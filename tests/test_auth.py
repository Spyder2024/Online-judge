import unittest
from datetime import timedelta
import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.schemas.user import UserCreate, UserLogin
from app.api.v1.oauth import _generate_oauth_state, _verify_oauth_state


class TestAuthSecurity(unittest.TestCase):
    """Unit tests for authentication, hashing, JWT issuance, and OAuth state verification."""

    def test_password_hashing_and_verification(self):
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        self.assertNotEqual(password, hashed)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))

    def test_access_token_creation_and_decoding(self):
        user_id = 101
        role = "CONTESTANT"
        token = create_access_token(subject=user_id, role=role, expires_delta=timedelta(minutes=15))
        self.assertIsInstance(token, str)

        payload = decode_access_token(token)
        self.assertEqual(int(payload.get("sub")), user_id)
        self.assertEqual(payload.get("role"), role)
        self.assertEqual(payload.get("type"), "access")

    def test_refresh_token_creation_and_decoding(self):
        user_id = 202
        refresh_token = create_refresh_token(subject=user_id, expires_delta=timedelta(days=7))
        self.assertIsInstance(refresh_token, str)

        payload = decode_refresh_token(refresh_token)
        self.assertEqual(int(payload.get("sub")), user_id)
        self.assertEqual(payload.get("type"), "refresh")

    def test_invalid_token_decoding(self):
        with self.assertRaises(Exception):
            decode_access_token("invalid.jwt.token.string")

    def test_user_create_validation(self):
        # Valid input
        valid_user = UserCreate(username="cadet_alex", password="ValidPassword123")
        self.assertEqual(valid_user.username, "cadet_alex")

        # Too short password (< 8 chars)
        with self.assertRaises(ValidationError):
            UserCreate(username="cadet_alex", password="short")

        # Too short username (< 3 chars)
        with self.assertRaises(ValidationError):
            UserCreate(username="al", password="ValidPassword123")

    def test_oauth_state_generation_and_validation(self):
        google_state = _generate_oauth_state("google")
        github_state = _generate_oauth_state("github")

        # Valid states verify correctly
        self.assertTrue(_verify_oauth_state(google_state, "google"))
        self.assertTrue(_verify_oauth_state(github_state, "github"))

        # Mismatched provider must fail
        self.assertFalse(_verify_oauth_state(google_state, "github"))
        self.assertFalse(_verify_oauth_state(github_state, "google"))

        # Null or garbage state must fail
        self.assertFalse(_verify_oauth_state(None, "google"))
        self.assertFalse(_verify_oauth_state("corrupted_state_token", "google"))


if __name__ == "__main__":
    unittest.main()
