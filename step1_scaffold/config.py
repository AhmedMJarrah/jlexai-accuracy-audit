"""
Centralized, typed configuration. Nothing downstream should read
os.environ directly or hardcode a path/value — everything flows
through this Settings object so later steps (Sheets, auth, sampling)
just extend this class instead of scattering constants around.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bridge_streamlit_secrets() -> None:
    """On Streamlit Cloud, secrets configured via the dashboard are
    exposed through st.secrets, NOT automatically as OS environment
    variables - pydantic-settings only reads .env/os.environ, so
    bridge the two here. Safe no-op anywhere else (local CLI use,
    no .streamlit/secrets.toml present) - any failure is swallowed
    since this must never block a plain CLI script from running."""
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            os.environ.setdefault(key, str(value))
    except Exception:
        pass


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

    # Sampling (Step 3) - local CLI only
    sample_size: int = 100
    num_users: int = 5
    random_seed: int = 42

    # Google Sheets (Step 4). Two spreadsheets: the main one (meta,
    # chain, future bylaw pools) and a dedicated one for reflect,
    # requested to keep the main sheet lighter.
    google_service_account_file: Path = Path("./secrets/service_account.json")
    google_service_account_json: str = ""  # cloud deployment: raw JSON string via secrets, takes priority over the file
    google_spreadsheet_id: str = ""
    google_reflect_spreadsheet_id: str = ""

    # Auth (Step 6)
    auth_shared_password_hash: str = ""
    users_config_file: Path = Path("./config/users.json")

    # Active data file - local CLI convenience only; deployed portals
    # never read this (volunteer portals only touch the sheet, and
    # the admin portal's release feature takes an upload instead).
    active_law_filename: str = ""

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "batches").mkdir(parents=True, exist_ok=True)
        self.google_service_account_file.parent.mkdir(parents=True, exist_ok=True)
        self.users_config_file.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    _bridge_streamlit_secrets()
    settings = Settings()
    settings.ensure_dirs()
    return settings
