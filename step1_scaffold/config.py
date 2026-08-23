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

    # Sampling (Step 3)
    sample_size: int = 100
    num_users: int = 5
    random_seed: int = 42

    # Google Sheets (Step 4)
    google_service_account_file: Path = Path("./secrets/service_account.json")
    google_spreadsheet_id: str = ""

    # Auth (Step 6)
    auth_shared_password_hash: str = ""
    users_config_file: Path = Path("./config/users.json")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "batches").mkdir(parents=True, exist_ok=True)
        self.google_service_account_file.parent.mkdir(parents=True, exist_ok=True)
        self.users_config_file.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
