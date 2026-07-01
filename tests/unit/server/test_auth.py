"""
PATCH-1-09: Hash admin password dengan hashlib.pbkdf2_hmac
Verifikasi bahwa password hashing dan verifikasi berfungsi dengan benar.
"""

import pytest
from core.security import hash_password, verify_password


class TestPasswordHashing:
    """Checklist PATCH-1-09:
    - [x] core/security.py ada dengan hash_password dan verify_password
    - [x] Hash password menggunakan pbkdf2 (bukan plaintext)
    - [x] Login berfungsi dengan password yang sama
    - [x] Password salah ditolak
    """

    def test_hash_password_exists(self):
        """hash_password harus ada dan callable."""
        assert callable(hash_password)

    def test_verify_password_exists(self):
        """verify_password harus ada dan callable."""
        assert callable(verify_password)

    def test_hash_password_returns_non_plaintext(self):
        """Hash password TIDAK BOLEH sama dengan input plaintext."""
        password = "my_secure_password"
        hashed = hash_password(password)
        assert hashed != password, "Hash password TIDAK BOLEH sama dengan plaintext"

    def test_hash_password_starts_with_pbkdf2(self):
        """Hash password harus dimulai dengan 'pbkdf2:sha256:'."""
        hashed = hash_password("test_password")
        assert hashed.startswith("pbkdf2:sha256:"), (
            f"Hash harus dimulai dengan 'pbkdf2:sha256:', ditemukan: {hashed[:30]}"
        )

    def test_verify_password_correct(self):
        """Password yang benar harus lolos verifikasi."""
        password = "correct_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_wrong(self):
        """Password yang salah harus ditolak."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_unique_per_call(self):
        """Dua hash dari password yang sama harus berbeda (karena salt acak)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2, "Salt harus acak — hash berbeda setiap kali"

    def test_verify_different_hashes_same_password(self):
        """Kedua hash berbeda dari password yang sama harus lolos verifikasi."""
        password = "my_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_plaintext_fallback_removed(self):
        """TASK-1.1: Plaintext fallback HARUS ditolak untuk keamanan.
        Sebelumnya ada fallback plaintext compare, tapi sudah dihapus.
        verify_password dengan non-pbkdf2 hash HARUS return False."""
        # Plaintext compare harus ditolak (TASK-1.1 security fix)
        assert verify_password("admin", "admin") is False
        assert verify_password("admin", "wrong") is False
        assert verify_password("admin", "pbkdf2:sha256:invalid") is False

    def test_hash_contains_salt(self):
        """Hash harus mengandung salt (encoded)."""
        hashed = hash_password("test")
        parts = hashed.split("$")
        assert len(parts) >= 3, (
            f"Hash format harus berisi salt dan key terpisah '$', ditemukan: {hashed}"
        )

    def test_empty_password_hash(self):
        """Password kosong harus tetap bisa di-hash (edge case)."""
        hashed = hash_password("")
        assert hashed.startswith("pbkdf2:sha256:")
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_unicode_password(self):
        """Password unicode harus didukung."""
        password = "пароль_密码_パスワード"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
