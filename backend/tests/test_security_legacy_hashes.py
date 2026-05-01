import bcrypt
from passlib.hash import django_pbkdf2_sha256

from app.core.security import get_password_hash, needs_password_rehash, verify_password


def test_verify_password_accepts_legacy_bcrypt_hashes() -> None:
    password = "AdminPass_123"
    legacy_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    assert verify_password(password, legacy_hash) is True
    assert verify_password("wrong-password", legacy_hash) is False
    assert needs_password_rehash(legacy_hash) is True


def test_verify_password_accepts_legacy_django_pbkdf2_hashes() -> None:
    password = "AdminPass_123"
    legacy_hash = django_pbkdf2_sha256.hash(password)

    assert verify_password(password, legacy_hash) is True
    assert verify_password("wrong-password", legacy_hash) is False
    assert needs_password_rehash(legacy_hash) is True


def test_verify_password_accepts_current_pbkdf2_hashes() -> None:
    password = "AdminPass_123"
    current_hash = get_password_hash(password)

    assert verify_password(password, current_hash) is True
    assert needs_password_rehash(current_hash) is False
