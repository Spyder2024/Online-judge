import os
import re
from app.core.config import Settings
from main import create_application
from fastapi.middleware.cors import CORSMiddleware


def test_sec_08_secret_key():
    print("[*] Testing SEC-08 SECRET_KEY production validation...", end=" ", flush=True)
    # Dev with default secret -> allowed
    s_dev = Settings(ENVIRONMENT="development")
    assert s_dev.ENVIRONMENT == "development"

    # Prod with default secret -> blocked
    default_secret = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    try:
        Settings(ENVIRONMENT="production", SECRET_KEY=default_secret)
        assert False, "Should have rejected default SECRET_KEY in production"
    except ValueError as e:
        assert "Default hardcoded SECRET_KEY is not permitted in production" in str(e)

    # Prod with short secret -> blocked
    try:
        Settings(ENVIRONMENT="production", SECRET_KEY="too_short_key")
        assert False, "Should have rejected short SECRET_KEY in production"
    except ValueError as e:
        assert "at least 32 characters" in str(e)

    # Prod with strong secret -> allowed
    s_prod = Settings(ENVIRONMENT="production", SECRET_KEY="a" * 64)
    assert s_prod.SECRET_KEY == "a" * 64
    print("PASS")


def test_sec_10_cors():
    print("[*] Testing SEC-10 CORS policy configuration...", end=" ", flush=True)
    app = create_application()
    cors_mw = None
    for mw in app.user_middleware:
        if mw.cls == CORSMiddleware:
            cors_mw = mw
            break

    assert cors_mw is not None, "CORSMiddleware must be present"
    options = cors_mw.kwargs
    assert options.get("allow_origins") != ["*"], "CORS allow_origins must not be wildcard ['*'] with credentials"
    assert "https://online-judge-iota-ashen.vercel.app" in options.get("allow_origins")
    assert options.get("allow_origin_regex") == r"^https://.*\.vercel\.app$"
    print("PASS")


def test_sec_02_compiler_sandbox():
    print("[*] Testing SEC-02 compiler engine Dockerfile and index.js...", end=" ", flush=True)
    with open("compiler-engine/Dockerfile", "r", encoding="utf-8") as f:
        dockerfile = f.read()

    assert "USER sandbox" in dockerfile, "Dockerfile must run as unprivileged sandbox user"
    assert "adduser -S sandbox" in dockerfile, "Dockerfile must create sandbox user"

    with open("compiler-engine/index.js", "r", encoding="utf-8") as f:
        index_js = f.read()

    assert "ALLOWED_LANGUAGES" in index_js, "index.js must enforce ALLOWED_LANGUAGES"
    assert "killSignal: 'SIGKILL'" in index_js, "index.js must enforce SIGKILL termination"
    assert "timeout: 10000" in index_js, "index.js must enforce execution timeout"
    print("PASS")


def test_sec_09_stored_xss():
    print("[*] Testing SEC-09 HTML escaping in frontend/index.html...", end=" ", flush=True)
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "function escapeHtml(str)" in html, "escapeHtml function must be defined"
    assert "${escapeHtml(user)}" in html, "Leaderboard user must be escaped"
    assert "${escapeHtml(p.title)}" in html, "Problem title must be escaped"
    assert "${escapeHtml(t)}" in html, "Problem tags must be escaped"
    assert "${escapeHtml(sub.problem_title || 'Problem')}" in html, "Submission title must be escaped"
    assert "${escapeHtml(JSON.stringify(data))}" in html, "WebSocket data log must be escaped"
    print("PASS")


if __name__ == "__main__":
    test_sec_08_secret_key()
    test_sec_10_cors()
    test_sec_02_compiler_sandbox()
    test_sec_09_stored_xss()
    print("\n[SUCCESS] All P2 + SEC-08 remediations verified.")
