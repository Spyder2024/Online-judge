import asyncio
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.models.user import User, UserRole
from app.schemas.storage import PresignedURLMethod, PresignedURLRequest
from app.api.v1.storage import generate_presigned_url
from app.api.v1.oauth import _generate_oauth_state, _verify_oauth_state
from app.api.v1.problems import SemanticSearchRequest, search_problems_semantic, create_problem


def test_oauth_state_protection():
    print("[*] Testing OAuth state CSRF token generation and validation...", end=" ", flush=True)
    google_state = _generate_oauth_state("google")
    github_state = _generate_oauth_state("github")

    assert _verify_oauth_state(google_state, "google") is True, "Valid Google state should verify"
    assert _verify_oauth_state(github_state, "github") is True, "Valid GitHub state should verify"
    assert _verify_oauth_state(google_state, "github") is False, "Google state must not verify for GitHub"
    assert _verify_oauth_state(github_state, "google") is False, "GitHub state must not verify for Google"
    assert _verify_oauth_state(None, "google") is False, "None state must fail"
    assert _verify_oauth_state("invalid.jwt.token", "google") is False, "Garbage state must fail"
    print("PASS")


def test_storage_authorization():
    print("[*] Testing Storage presigned URL authorization and validation...", end=" ", flush=True)
    contestant = User(user_id=42, username="contestant_1", role=UserRole.CONTESTANT)
    admin = User(user_id=1, username="admin_1", role=UserRole.ADMIN)

    # 1. Path traversal check
    try:
        asyncio.run(generate_presigned_url(
            PresignedURLRequest(object_key="../secret.txt", method=PresignedURLMethod.GET),
            current_user=contestant
        ))
        assert False, "Should have rejected path traversal"
    except HTTPException as e:
        assert e.status_code == 400

    # 2. Non-admin attempting to upload to problem directory
    try:
        asyncio.run(generate_presigned_url(
            PresignedURLRequest(object_key="problems/10/statement.pdf", method=PresignedURLMethod.PUT),
            current_user=contestant
        ))
        assert False, "Contestant should not be able to PUT to problems/"
    except HTTPException as e:
        assert e.status_code == 403

    # 3. Non-admin attempting to download private testcase files
    try:
        asyncio.run(generate_presigned_url(
            PresignedURLRequest(object_key="testcases/problem_10_in.txt", method=PresignedURLMethod.GET),
            current_user=contestant
        ))
        assert False, "Contestant should not be able to GET private testcases"
    except HTTPException as e:
        assert e.status_code == 403

    # 4. Non-admin uploading avatar to wrong user directory
    try:
        asyncio.run(generate_presigned_url(
            PresignedURLRequest(object_key="avatars/999/avatar.png", method=PresignedURLMethod.PUT),
            current_user=contestant
        ))
        assert False, "Contestant should not be able to PUT to another user's avatar path"
    except HTTPException as e:
        assert e.status_code == 403

    # 5. Non-admin uploading invalid file type
    try:
        asyncio.run(generate_presigned_url(
            PresignedURLRequest(
                object_key="avatars/42/shell.sh",
                method=PresignedURLMethod.PUT,
                content_type="application/x-sh"
            ),
            current_user=contestant
        ))
        assert False, "Contestant should not be able to upload executable content type"
    except HTTPException as e:
        assert e.status_code == 400

    # 6. Admin upload to problems/ is allowed (mock storage client)
    with patch("app.api.v1.storage.storage_client.generate_presigned_put_url", return_value="https://s3.mock/upload"):
        res = asyncio.run(generate_presigned_url(
            PresignedURLRequest(object_key="problems/10/statement.pdf", method=PresignedURLMethod.PUT),
            current_user=admin
        ))
        assert res.url == "https://s3.mock/upload"

    # 7. Contestant uploading valid avatar to own directory
    with patch("app.api.v1.storage.storage_client.generate_presigned_put_url", return_value="https://s3.mock/avatar"):
        res = asyncio.run(generate_presigned_url(
            PresignedURLRequest(
                object_key="avatars/42/photo.png",
                method=PresignedURLMethod.PUT,
                content_type="image/png"
            ),
            current_user=contestant
        ))
        assert res.url == "https://s3.mock/avatar"

    print("PASS")


def test_problems_fixes():
    print("[*] Testing Problem search query handling and admin creation guard...", end=" ", flush=True)
    import inspect
    from app.api.deps import get_current_admin_user

    sig = inspect.signature(create_problem)
    assert "current_admin" in sig.parameters, "create_problem must require current_admin"
    assert sig.parameters["current_admin"].default.dependency == get_current_admin_user, "Must use get_current_admin_user"

    # Test search_problems_semantic empty query fallback
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar.return_value = 0
    mock_execute.scalars.return_value.all.return_value = []
    
    async def mock_exec_coro(*args, **kwargs):
        return mock_execute
    mock_db.execute = mock_exec_coro

    # Should not raise NameError: name 'query_text' is not defined
    res = asyncio.run(search_problems_semantic(
        SemanticSearchRequest(query="binary search", limit=5),
        db=mock_db
    ))
    assert isinstance(res, list)

    res_empty = asyncio.run(search_problems_semantic(
        SemanticSearchRequest(query="", limit=5),
        db=mock_db
    ))
    assert isinstance(res_empty, list)

    print("PASS")


if __name__ == "__main__":
    test_oauth_state_protection()
    test_storage_authorization()
    test_problems_fixes()
    print("\n[SUCCESS] All P1 security remediations verified.")
