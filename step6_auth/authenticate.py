"""
Authenticates a username/password pair against the shared hashed
password and the users config identity mapping. Returns the matched
User on success, None on any failure - the caller (UI) should show
one generic "invalid username or password" message either way,
never distinguishing unknown-username from wrong-password, to avoid
leaking which usernames are valid.
"""
from step1_scaffold.config import Settings
from step1_scaffold.logging_setup import get_logger
from step6_auth.hashing import verify_password
from step6_auth.models import User
from step6_auth.users_config import find_user

logger = get_logger("authenticate")


def authenticate(username: str, password: str, settings: Settings) -> User | None:
    if not settings.auth_shared_password_hash:
        raise ValueError(
            "AUTH_SHARED_PASSWORD_HASH is not set in .env - run "
            "step6_auth.hash_password_cli first"
        )

    user = find_user(username, settings.users_config_file)
    if user is None:
        logger.warning(f"Login attempt for unknown username: {username}")
        return None

    if not verify_password(password, settings.auth_shared_password_hash):
        logger.warning(f"Failed login attempt for username: {username}")
        return None

    logger.info(f"Successful login: {username}")
    return user
