from passlib.context import CryptContext

from app_service.core.security import BCRYPT_ROUNDS, hash_password, password_needs_rehash, verify_password
from app_service.db.postgres.models import User, UserRole
from app_service.services.auth_service import AuthService


def _rounds(hashed: str) -> int:
    # bcrypt format: $2b$<cost>$...
    return int(hashed.split("$")[2])


def test_new_hashes_use_the_configured_cost():
    hashed = hash_password("StrongPass1")
    assert _rounds(hashed) == BCRYPT_ROUNDS == 10
    assert verify_password("StrongPass1", hashed)
    assert not password_needs_rehash(hashed)


def test_old_cost_12_hash_still_verifies_and_is_flagged_for_rehash():
    old = CryptContext(schemes=["bcrypt"], bcrypt__default_rounds=12).hash("StrongPass1")
    assert verify_password("StrongPass1", old)
    assert password_needs_rehash(old)


def test_login_upgrades_an_old_hash(db_session):
    old = CryptContext(schemes=["bcrypt"], bcrypt__default_rounds=12).hash("StrongPass1")
    user = User(email="old.hash@example.com", password_hash=old, role=UserRole.USER, is_active=True)
    db_session.add(user)
    db_session.commit()

    AuthService(db_session).authenticate("old.hash@example.com", "StrongPass1")

    db_session.refresh(user)
    assert _rounds(user.password_hash) == BCRYPT_ROUNDS
    assert verify_password("StrongPass1", user.password_hash)
