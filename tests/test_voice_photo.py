"""Photo validation, paid-call boundaries, structured vision and speech. Every provider is replaced."""

import asyncio
import base64
import io
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image
from starlette.testclient import TestClient

from voice_agent.photo import MAX_IMAGE_BYTES, PhotoAnswer, PhotoProviders, PhotoResult, PhotoService
from voice_agent.server import create_app


def photo() -> bytes:
    image = Image.new("RGB", (60, 30), "green")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "private camera metadata"
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


FOUND = PhotoResult(status="found", answer="The red cup is to the left of the book.", audio_base64="SUQz")
URL = "/api/voice/photo?question=Where%20is%20the%20red%20cup%3F"
HEADERS = {"Content-Type": "image/jpeg", "Origin": "https://ui.example.com"}


class PhotoRouteTest(unittest.TestCase):
    def setUp(self):
        self.provider = AsyncMock(return_value=FOUND)
        self.service = PhotoService(self.provider, daily_limit=2)
        self.client = TestClient(create_app(lambda: "token", cors_origins=["https://ui.example.com"], photos=self.service))

    def test_sends_upright_metadata_free_image_and_returns_speech_without_caching(self):
        response = self.client.post(URL, content=photo(), headers=HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), FOUND.model_dump())
        self.assertEqual(response.headers["cache-control"], "no-store")
        normalized, question = self.provider.call_args.args
        with Image.open(io.BytesIO(normalized)) as image:
            self.assertEqual(image.size, (30, 60))
            self.assertFalse(image.getexif())
        self.assertEqual(question, "Where is the red cup?")
        self.assertEqual(self.service.used, 1)

    def test_rejects_invalid_input_before_any_provider_call(self):
        for url, content, headers, expected in [
            (URL, photo(), HEADERS | {"Origin": "https://other.example"}, 403),
            (URL, photo(), HEADERS | {"Content-Type": "image/svg+xml"}, 415),
            (URL, b"not an image", HEADERS, 422),
            ("/api/voice/photo", photo(), HEADERS, 422),
            (URL, b"x" * (MAX_IMAGE_BYTES + 1), HEADERS, 413),
        ]:
            with self.subTest(status=expected):
                self.assertEqual(self.client.post(url, content=content, headers=headers).status_code, expected)
        self.provider.assert_not_called()
        self.assertEqual(self.service.used, 0)
        self.assertFalse(self.service.busy)

    def test_daily_limit_includes_failed_attempts_and_does_not_leak_provider_details(self):
        self.provider.side_effect = RuntimeError("upstream key sk_secret private payload")
        for _ in range(2):
            response = self.client.post(URL, content=photo(), headers=HEADERS)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("sk_secret", response.text)
        self.assertEqual(self.client.post(URL, content=photo(), headers=HEADERS).status_code, 429)
        self.assertEqual(self.provider.await_count, 2)
        self.assertFalse(self.service.busy)

    def test_unconfigured_capability_and_cors_preflight_make_no_paid_calls(self):
        client = TestClient(create_app(lambda: "token"))
        self.assertEqual(client.get("/api/voice/photo").json(), {"available": False})
        self.assertEqual(client.post(URL, content=photo(), headers={"Content-Type": "image/jpeg"}).status_code, 503)
        self.assertEqual(self.client.get("/api/voice/photo").json(), {"available": True})
        response = self.client.options(URL, headers={"Origin": "https://ui.example.com",
            "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://ui.example.com")
        self.provider.assert_not_called()


class PhotoConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_second_upload_does_not_queue_a_second_paid_call(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def provider(image, question):
            started.set()
            await finish.wait()
            return FOUND

        service = PhotoService(provider)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(lambda: "token", photos=service)),
                                     base_url="http://testserver") as client:
            first = asyncio.create_task(client.post(URL, content=photo(), headers={"Content-Type": "image/jpeg"}))
            await started.wait()
            second = await client.post(URL, content=photo(), headers={"Content-Type": "image/jpeg"})
            self.assertEqual(second.status_code, 429)
            finish.set()
            self.assertEqual((await first).status_code, 200)
        self.assertEqual(service.used, 1)


class ProviderContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_structured_answer_is_spoken_verbatim_using_the_agent_voice(self):
        claude = AsyncMock()
        claude.messages.parse.return_value = SimpleNamespace(parsed_output=PhotoAnswer(
            status="uncertain", answer="Which of the two red cups do you mean?"))
        speech = SimpleNamespace(conversational_ai=SimpleNamespace(agents=SimpleNamespace(get=AsyncMock(
            return_value=SimpleNamespace(conversation_config=SimpleNamespace(tts=SimpleNamespace(voice_id="agent-voice")))))))
        calls = []

        async def convert(**kwargs):
            calls.append(kwargs)
            yield b"ID3audio"

        speech.text_to_speech = SimpleNamespace(convert=convert)
        with patch("voice_agent.photo.AsyncAnthropic") as anthropic, patch("voice_agent.photo.AsyncElevenLabs", return_value=speech):
            anthropic.return_value.__aenter__ = AsyncMock(return_value=claude)
            anthropic.return_value.__aexit__ = AsyncMock()
            result = await PhotoProviders("secret", "secret", "agent")(photo(), "Find a red cup")
        self.assertEqual(result.status, "uncertain")
        self.assertEqual(base64.b64decode(result.audio_base64), b"ID3audio")
        self.assertEqual(calls[0]["text"], result.answer)
        self.assertEqual(calls[0]["voice_id"], "agent-voice")
        self.assertFalse(calls[0]["enable_logging"])
        self.assertEqual(calls[0]["request_options"]["max_retries"], 0)
        vision = claude.messages.parse.call_args.kwargs
        self.assertEqual(vision["output_format"], PhotoAnswer)
        self.assertNotIn("tool_choice", vision)
        self.assertEqual(vision["messages"][0]["content"][0]["source"]["media_type"], "image/jpeg")

    async def test_speech_failure_preserves_the_grounded_text(self):
        claude = AsyncMock()
        claude.messages.parse.return_value = SimpleNamespace(parsed_output=PhotoAnswer(
            status="not_visible", answer="I cannot see the red cup in this photo."))
        with patch("voice_agent.photo.AsyncAnthropic") as anthropic:
            anthropic.return_value.__aenter__ = AsyncMock(return_value=claude)
            anthropic.return_value.__aexit__ = AsyncMock()
            result = await PhotoProviders("secret", "secret", None)(photo(), "Find a red cup")
        self.assertEqual(result.status, "not_visible")
        self.assertIsNone(result.audio_base64)
        self.assertIn("read the answer", result.speech_error)


if __name__ == "__main__":
    unittest.main()
