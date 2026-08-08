"""
test_compiler_engine.py — Module 1: Standalone Compiler Microservice Diagnostic

Purpose:
    Standalone, zero-dependency test script (Python 3.12 compatible).
    No FastAPI app context required. Run directly from VS Code or terminal:
        python test_compiler_engine.py
        python test_compiler_engine.py --url http://localhost:8000/run

Usage:
    Each test case is defined explicitly so it can be commented out
    and run cell-by-cell in a Jupyter-style debugger or VS Code Interactive.

Exit codes:
    0  — All tests passed
    1  — One or more tests failed
    2  — Compiler engine is unreachable
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
# Configuration — matches settings in config.py
# ─────────────────────────────────────────────
DEFAULT_URL = "http://127.0.0.1:8000/run"
HEALTH_URL  = "http://127.0.0.1:8000/health"
TIMEOUT_SEC = 12.0

# ─────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────
@dataclass
class TestCase:
    name: str
    language: str          # "cpp" | "py" | "java"
    code: str
    stdin: str
    expected_stdout: str
    expect_error: bool = False   # Set True for CE/RE tests


@dataclass
class TestResult:
    name: str
    passed: bool
    verdict: str
    actual_output: str
    expected_output: str
    raw_error: str
    elapsed_ms: float
    exception: Optional[str] = None


# ─────────────────────────────────────────────
# HTTP Client (zero external deps)
# ─────────────────────────────────────────────
def post_to_compiler(url: str, language: str, code: str, stdin: str) -> tuple[dict, float]:
    """
    POST {"language": ..., "code": ..., "input": ...} to the compiler microservice.
    Returns (response_dict, elapsed_ms).
    Raises on network error.
    """
    payload = json.dumps({
        "language": language,
        "code": code,
        "input": stdin,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        elapsed_ms = (time.perf_counter() - start) * 1000
        body = resp.read().decode("utf-8")
        return json.loads(body), elapsed_ms


def check_health(health_url: str) -> bool:
    """Ping /health to verify the microservice is reachable."""
    try:
        with urllib.request.urlopen(health_url, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


# ─────────────────────────────────────────────
# Output Sanitizer (mirrors sandbox.py logic)
# ─────────────────────────────────────────────
def sanitize(raw: str) -> list[str]:
    """
    Normalize stdout/expected output for comparison:
    1. Normalize Windows CRLF → LF
    2. Strip leading/trailing whitespace from full output
    3. Strip each line individually
    4. Discard empty lines
    """
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    return [line.strip() for line in normalized.splitlines() if line.strip()]


# ─────────────────────────────────────────────
# Is-error classifier (mirrors sandbox.py logic)
# ─────────────────────────────────────────────
COMPILE_ERROR_SIGNALS = [
    "error:", "SyntaxError", "NameError", "g++", "javac",
    "compilation failed", "undefined reference",
]

def classify_error(raw_error: str, raw_output: str) -> str:
    """
    Return a verdict string from error/output fields.
    The Node.js engine puts stderr in 'error' even when there are only
    compiler warnings on a successful run. We distinguish real errors
    by checking whether 'output' is empty AND 'error' is non-empty.
    """
    if not raw_error:
        return "ACCEPTED"
    # If the program produced output AND there is stderr, it's likely
    # just a warning — don't penalize as error
    if raw_output.strip() and not any(sig in raw_error for sig in COMPILE_ERROR_SIGNALS):
        return "WARNING_ONLY"
    if any(sig in raw_error for sig in COMPILE_ERROR_SIGNALS):
        return "COMPILATION_ERROR"
    return "RUNTIME_ERROR"


# ─────────────────────────────────────────────
# Core runner
# ─────────────────────────────────────────────
def run_test(url: str, tc: TestCase) -> TestResult:
    try:
        data, elapsed_ms = post_to_compiler(url, tc.language, tc.code, tc.stdin)
    except urllib.error.URLError as e:
        return TestResult(
            name=tc.name, passed=False,
            verdict="NETWORK_ERROR",
            actual_output="", expected_output=tc.expected_stdout,
            raw_error=str(e), elapsed_ms=0.0,
            exception=str(e),
        )
    except Exception as e:
        return TestResult(
            name=tc.name, passed=False,
            verdict="EXCEPTION",
            actual_output="", expected_output=tc.expected_stdout,
            raw_error="", elapsed_ms=0.0,
            exception=str(e),
        )

    raw_output: str = data.get("output", "") or ""
    raw_error:  str = data.get("error",  "") or ""

    verdict = classify_error(raw_error, raw_output)

    if tc.expect_error:
        # For CE/RE tests, we just need a non-ACCEPTED verdict
        passed = verdict in ("COMPILATION_ERROR", "RUNTIME_ERROR")
    else:
        actual_lines   = sanitize(raw_output)
        expected_lines = sanitize(tc.expected_stdout)
        passed = (actual_lines == expected_lines) and verdict not in ("COMPILATION_ERROR", "RUNTIME_ERROR")
        if passed:
            verdict = "ACCEPTED"
        elif verdict == "ACCEPTED":
            verdict = "WRONG_ANSWER"

    return TestResult(
        name=tc.name, passed=passed,
        verdict=verdict,
        actual_output=raw_output,
        expected_output=tc.expected_stdout,
        raw_error=raw_error,
        elapsed_ms=elapsed_ms,
    )


# ─────────────────────────────────────────────
# Test Suite Definition
# ─────────────────────────────────────────────
TEST_CASES: list[TestCase] = [

    # ── Python ────────────────────────────────
    TestCase(
        name="[PY] Hello World",
        language="py",
        code='print("Hello, World!")\n',
        stdin="",
        expected_stdout="Hello, World!",
    ),
    TestCase(
        name="[PY] stdin → stdout (Add 1)",
        language="py",
        code="n = int(input())\nprint(n + 1)\n",
        stdin="41",
        expected_stdout="42",
    ),
    TestCase(
        name="[PY] Multi-line output",
        language="py",
        code="for i in range(1, 4):\n    print(i)\n",
        stdin="",
        expected_stdout="1\n2\n3",
    ),
    TestCase(
        name="[PY] Trailing whitespace robustness",
        language="py",
        code='print("ok   ")\n',
        stdin="",
        expected_stdout="ok",        # sanitizer strips trailing spaces on each line
    ),
    TestCase(
        name="[PY] Syntax Error (expect CE)",
        language="py",
        code="def foo(:\n    pass\n",
        stdin="",
        expected_stdout="",
        expect_error=True,
    ),

    # ── C++ ───────────────────────────────────
    TestCase(
        name="[CPP] Hello World",
        language="cpp",
        code='#include<iostream>\nint main(){std::cout<<"Hello, World!"<<std::endl;return 0;}\n',
        stdin="",
        expected_stdout="Hello, World!",
    ),
    TestCase(
        name="[CPP] stdin → stdout (Two Sum check)",
        language="cpp",
        code="#include<iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<std::endl;return 0;}\n",
        stdin="3 7",
        expected_stdout="10",
    ),
    TestCase(
        name="[CPP] Compilation Error (expect CE)",
        language="cpp",
        code="int main(){ return undeclared_var; }\n",
        stdin="",
        expected_stdout="",
        expect_error=True,
    ),

    # ── Java ──────────────────────────────────
    TestCase(
        name="[JAVA] Hello World",
        language="java",
        code=(
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("Hello, World!");\n'
            "    }\n"
            "}\n"
        ),
        stdin="",
        expected_stdout="Hello, World!",
    ),
]


# ─────────────────────────────────────────────
# Reporter
# ─────────────────────────────────────────────
PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"

def report(result: TestResult) -> None:
    status = PASS if result.passed else FAIL
    ms = f"{result.elapsed_ms:.1f}ms"
    print(f"  {status}  {result.name:<50} [{result.verdict}]  {ms}")
    if not result.passed:
        if result.exception:
            print(f"         Exception : {result.exception}")
        if result.raw_error:
            print(f"         Stderr    : {result.raw_error[:300].strip()}")
        if not result.expect_error:
            print(f"         Expected  : {repr(result.expected_output[:120])}")
            print(f"         Actual    : {repr(result.actual_output[:120])}")


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Compiler Microservice Diagnostic")
    parser.add_argument("--url",    default=DEFAULT_URL, help="POST endpoint (default: %(default)s)")
    parser.add_argument("--health", default=HEALTH_URL,  help="Health endpoint (default: %(default)s)")
    args = parser.parse_args()

    run_url    = args.url
    health_url = args.health

    print("=" * 65)
    print("  Compiler Microservice Diagnostic — Module 1")
    print(f"  Target : {run_url}")
    print("=" * 65)

    # ── Health Check ──────────────────────────
    print("\n[0/3] Health check ...")
    if check_health(health_url):
        print(f"  {PASS}  /health → ok")
    else:
        print(f"  {FAIL}  /health unreachable at {health_url}")
        print("\n  ► Start the compiler microservice first:")
        print("    cd compiler-engine && npm install && node index.js")
        return 2

    # ── Run Tests ─────────────────────────────
    results: list[TestResult] = []
    print(f"\n[1/3] Running {len(TEST_CASES)} test cases ...\n")
    for tc in TEST_CASES:
        r = run_test(run_url, tc)
        report(r)
        results.append(r)

    # ── Summary ───────────────────────────────
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    print(f"\n[2/3] Summary: {passed}/{len(results)} passed", end="")
    print(f"  {'✓' if failed == 0 else '✗'}\n")

    # ── Sanitizer Self-Test ───────────────────
    print("[3/3] Sanitizer self-test ...")
    assert sanitize("hello\r\n")   == ["hello"],         "CRLF strip failed"
    assert sanitize("  ok   \n")   == ["ok"],            "Whitespace strip failed"
    assert sanitize("1\n2\n3\n")   == ["1", "2", "3"],   "Multi-line split failed"
    assert sanitize("")            == [],                 "Empty string failed"
    assert sanitize("a\n\nb\n")    == ["a", "b"],         "Blank-line discard failed"
    print(f"  {PASS}  All sanitizer assertions passed\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
