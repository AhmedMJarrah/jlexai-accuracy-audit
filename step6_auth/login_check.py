"""
Manual CLI test for the auth layer - run this before wiring up the
Streamlit login screen, to confirm hashing and the users config are
set up correctly.
"""
import getpass

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging
from step6_auth.authenticate import authenticate

if __name__ == "__main__":
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    user = authenticate(username, password, settings)
    if user is None:
        print("\nInvalid username or password.")
    else:
        role = "admin" if user.is_admin else f"volunteer ({user.user_slot})"
        print(f"\nLogin OK - {user.display_name or user.username} [{role}]")
