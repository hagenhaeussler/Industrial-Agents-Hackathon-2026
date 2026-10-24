"""Environment configuration; provider secrets never enter API responses."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = REPO_ROOT / "data"
    state_dir: Path = REPO_ROOT / ".state"
    hero_dir: Path = REPO_ROOT / "demo" / "hero"
    static_dir: Path = REPO_ROOT / "web" / "app" / "dist"
    demo_mode: bool = False
    profile: str = "kit_1_1_0"
    public_base_url: str = "http://localhost:8000"
    # CR-C-2: every construction path fails closed. Only an explicit local
    # development opt-in may allow admin creation without a code.
    admin_token: str | None = None
    admin_requires_code: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(REPO_ROOT / ".env", override=False)
        return cls(
            data_dir=Path(os.environ.get("DATA_DIR", str(REPO_ROOT / "data"))).resolve(),
            state_dir=Path(os.environ.get("STATE_DIR", str(REPO_ROOT / ".state"))).resolve(),
            demo_mode=os.environ.get("TYB_DEMO_MODE", "").lower() in {"1", "true", "yes"},
            profile=os.environ.get("TYB_PROFILE", "kit_1_1_0"),
            public_base_url=os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
            admin_token=os.environ.get("TYB_ADMIN_TOKEN", "").strip() or None,
            admin_requires_code=os.environ.get("TYB_ADMIN_OPEN_INSECURE", "").lower() not in {"1", "true", "yes"},
        )
