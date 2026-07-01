"""
Password hashing utilities using bcrypt directly.
We use bcrypt directly instead of passlib because passlib 1.7.4 is incompatible
with bcrypt >= 4.0 (the newer bcrypt rejects passlib's internal 72-byte test strings).
"""
import bcrypt


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    pwd_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False
