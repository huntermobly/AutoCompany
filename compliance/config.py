import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = ".local/compliance.sqlite3"
    mode: str = "development"
    external_enabled: bool = False
    sandbox_env: str = "test"
    sandbox_key: str = ""
    sandbox_secret: str = ""
    ai_key: str = ""
    ai_model: str = ""
    max_body_bytes: int = 7_000_000

    def __post_init__(self):
        if self.mode not in {"development", "test", "production"}:
            raise ValueError("COMPLIANCE_MODE must be development, test or production")

    @classmethod
    def from_env(cls):
        return cls(
            db_path=os.getenv("COMPLIANCE_DB", ".local/compliance.sqlite3"),
            mode=os.getenv("COMPLIANCE_MODE", "development"),
            external_enabled=os.getenv("ENABLE_EXTERNAL_PROVIDERS") == "true",
            sandbox_env=os.getenv("SANDBOX_ENV", "test"),
            sandbox_key=os.getenv("SANDBOX_API_KEY", ""),
            sandbox_secret=os.getenv("SANDBOX_API_SECRET", ""),
            ai_key=os.getenv("OPENROUTER_API_KEY", ""),
            ai_model=os.getenv("OPENROUTER_MODEL", ""),
        )

