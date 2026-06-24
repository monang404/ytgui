import hashlib
import secrets
import base64

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2:sha256:100000${base64.b64encode(salt).decode('utf-8')}${base64.b64encode(key).decode('utf-8')}"

def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password.startswith("pbkdf2:sha256:"):
        # TASK-1.1: Tolak semua format non-pbkdf2 — hapus plaintext fallback
        # Plaintext comparison adalah security hole: password mentah tersimpan
        # di env var, log, dan /proc/self/environ.
        return False
    try:
        _, _, iterations, salt_b64, key_b64 = hashed_password.split("$")[0].split(":") + hashed_password.split("$")[1:]
        salt = base64.b64decode(salt_b64)
        expected_key = base64.b64decode(key_b64)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iterations))
        return secrets.compare_digest(key, expected_key)
    except Exception:
        return False
