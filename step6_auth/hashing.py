"""
Password hashing. The project password is shared across all
volunteers (a login gate, not per-user security, per project
decision) - but it is still never stored or compared as plaintext.
"""
import bcrypt


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
