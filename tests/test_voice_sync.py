"""Voice agent sync against a fake ElevenLabs client: which remote resources it creates, updates and deletes."""

import unittest
from types import SimpleNamespace

from voice_agent.agent import sync

AGENT, URL, OLD_URL = "agent-1", "https://voice.example/mcp", "https://old.example/mcp"


class FakeElevenLabs:
    """Records the calls `sync` makes. Integrations are (id, url) pairs; `attached` are the agent's integrations."""

    def __init__(self, integrations: dict[str, str], attached: list[str], secrets: dict[str, str] | None = None):
        self.integrations = dict(integrations)
        self.attached = list(attached)
        self.secrets = dict(secrets or {})
        self.created: list[str] = []
        self.updated: list[str] = []
        self.deleted: list[str] = []
        self.conversational_ai = SimpleNamespace(
            agents=self.Agents(self), mcp_servers=self.Servers(self), secrets=self.Secrets(self)
        )

    class Agents:
        def __init__(self, fake: "FakeElevenLabs") -> None:
            self.fake = fake

        def get(self, agent_id: str) -> SimpleNamespace:
            prompt = SimpleNamespace(mcp_server_ids=self.fake.attached)
            return SimpleNamespace(conversation_config=SimpleNamespace(agent=SimpleNamespace(prompt=prompt)))

        def update(self, agent_id: str, **settings) -> None:
            self.fake.attached = settings["conversation_config"]["agent"]["prompt"]["mcp_server_ids"]

    class Servers:
        def __init__(self, fake: "FakeElevenLabs") -> None:
            self.fake = fake

        def list(self) -> SimpleNamespace:
            servers = [
                SimpleNamespace(id=i, config=SimpleNamespace(url=url)) for i, url in self.fake.integrations.items()
            ]
            return SimpleNamespace(mcp_servers=servers)

        def create(self, config: dict) -> SimpleNamespace:
            new_id = f"new-{len(self.fake.created)}"
            self.fake.integrations[new_id] = config["url"]
            self.fake.created.append(new_id)
            return SimpleNamespace(id=new_id)

        def update(self, server_id: str, **behavior) -> None:
            self.fake.updated.append(server_id)

        def delete(self, server_id: str) -> None:
            del self.fake.integrations[server_id]
            self.fake.deleted.append(server_id)

    class Secrets:
        def __init__(self, fake: "FakeElevenLabs") -> None:
            self.fake = fake

        def list(self, search: str) -> SimpleNamespace:
            found = [SimpleNamespace(name=name, secret_id=i) for name, i in self.fake.secrets.items() if search in name]
            return SimpleNamespace(secrets=found)

        def create(self, name: str, value: str) -> SimpleNamespace:
            self.fake.secrets[name] = f"secret-{len(self.fake.secrets)}"
            return SimpleNamespace(secret_id=self.fake.secrets[name])

        def update(self, secret_id: str, name: str, value: str) -> None:
            pass


class SyncTest(unittest.TestCase):
    def test_same_url_updates_this_agents_integration_only(self) -> None:
        # "other" belongs to another agent in the workspace and points elsewhere; sync must leave it alone.
        fake = FakeElevenLabs({"mine": URL, "other": OLD_URL}, attached=["mine"])
        sync(fake, AGENT, URL, "token")
        self.assertEqual((fake.created, fake.updated, fake.deleted), ([], ["mine"], []))
        self.assertEqual(fake.attached, ["mine"])

    def test_new_url_replaces_this_agents_integration_only(self) -> None:
        fake = FakeElevenLabs({"mine": OLD_URL, "other": OLD_URL}, attached=["mine"])
        sync(fake, AGENT, URL, "token")
        self.assertEqual(fake.created, ["new-0"])
        self.assertEqual(fake.attached, ["new-0"])
        self.assertEqual(fake.deleted, ["mine"])
        self.assertIn("other", fake.integrations)

    def test_secret_belongs_to_the_agent_and_is_reused(self) -> None:
        fake = FakeElevenLabs({}, attached=[], secrets={"building-mcp-authorization": "shared"})
        sync(fake, AGENT, URL, "token")
        sync(fake, AGENT, URL, "token")
        self.assertEqual(set(fake.secrets), {"building-mcp-authorization", f"building-mcp-authorization-{AGENT}"})


if __name__ == "__main__":
    unittest.main()
