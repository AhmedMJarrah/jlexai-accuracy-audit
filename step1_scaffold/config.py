"""
Centralized, typed configuration. Nothing downstream should read
os.environ directly or hardcode a path/value — everything flows
through this Settings object so later steps (Sheets, auth, sampling)
just extend this class instead of scattering constants around.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    project_name: str = "jlexai-accuracy-audit"

    data_dir: Path = Path("./data")
    log_dir: Path = Path("./logs")

    def ensure_dirs(self) -> None:
        """Create data/log dirs if missing. Called once at startup."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Single entry point — import this everywhere, don't instantiate
    Settings() directly in other modules."""
    settings = Settings()
    settings.ensure_dirs()
    return settings