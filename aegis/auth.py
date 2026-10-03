"""Credential and public identity helpers. Secrets never enter API identity payloads."""
import hashlib
import secrets
from .store_util import identifier, now

ROLES = {'admin', 'operator', 'viewer'}


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()


def public_user(user):
    if not user:
        return None
    return {key: user[key] for key in ('id', 'username', 'name', 'role', 'disabled', 'created_at', 'updated_at')}


def new_user(username, name, role, password):
    salt = secrets.token_hex(16)
    return dict(id=identifier(), username=username, name=name, role=role, salt=salt,
                password_hash=password_hash(password, salt), disabled=0, created_at=now(), updated_at=now())
