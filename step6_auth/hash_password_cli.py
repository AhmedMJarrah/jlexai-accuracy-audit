"""
One-off CLI: generates a bcrypt hash for the shared project
password. Run once, paste the output into .env as
AUTH_SHARED_PASSWORD_HASH. The plaintext password is never written
anywhere, including here - prompted securely via getpass by default.
"""
import argparse
import getpass

from step6_auth.hashing import hash_password

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=None, help="Omit to be prompted securely instead")
    args = parser.parse_args()

    plaintext = args.password or getpass.getpass("Enter the shared password: ")
    print("\nAdd this to your .env as AUTH_SHARED_PASSWORD_HASH:")
    print(hash_password(plaintext))
