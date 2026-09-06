import hashlib
from app.core.config import settings


def hash_token(plain: str) -> str:
    data = (plain + settings.TOKEN_HASH_SALT).encode("utf-8")
    return hashlib.sha256(data).hexdigest()