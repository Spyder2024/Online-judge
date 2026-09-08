import os
import sys
import subprocess
import urllib.request
import json
import re

TARGET_URL = os.environ.get("DEPLOY_URL", "https://online-judge-iota-ashen.vercel.app")

def run_step(desc, fn):
    print(f"[*] {desc}...", end=" ", flush=True)
    try:
        fn()
        print("PASS")
    except Exception as e:
        print("FAIL")
        print(f"    Error: {e}")
        sys.exit(1)

def test_js_syntax():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for i, s in enumerate(scripts):
        if not s.strip():
            continue
        temp_file = f"_smoke_script_{i}.js"
        with open(temp_file, "w", encoding="utf-8") as sf:
            sf.write(s)
        try:
            res = subprocess.run(["node", "-c", temp_file], capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Script #{i} syntax error:\n{res.stderr}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

def test_python_syntax():
    import py_compile
    for root, dirs, files in os.walk("app"):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                py_compile.compile(p, doraise=True)
    py_compile.compile("main.py", doraise=True)

def test_required_dom_elements():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    required_ids = [
        "problem-list-container",
        "screen-hub",
        "screen-arena",
        "screen-analytics",
        "screen-profile",
        "code-editor",
        "leaderboard-table-body",
        "auth-modal",
        "nav-hub",
        "nav-arena",
        "nav-analytics",
        "nav-profile"
    ]
    for req_id in required_ids:
        if f'id="{req_id}"' not in html and f"id='{req_id}'" not in html:
            raise AssertionError(f"Required DOM ID '{req_id}' missing in frontend/index.html")

def test_required_js_functions():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    required_fns = [
        "fetchProblems",
        "selectProblem",
        "switchTab",
        "toggleAuthModal",
        "fetchRedisLeaderboard",
        "submitCodeToArena"
    ]
    for fn in required_fns:
        if f"function {fn}" not in html and f"{fn} = " not in html:
            raise AssertionError(f"Required JS function '{fn}' missing in frontend/index.html")

def test_live_health():
    req = urllib.request.Request(f"{TARGET_URL}/health", headers={"User-Agent": "SmokeTest"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise AssertionError(f"/health returned status {resp.status}")

def test_live_problems():
    req = urllib.request.Request(f"{TARGET_URL}/api/v1/problems?page=1&limit=10", headers={"User-Agent": "SmokeTest"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise AssertionError(f"/api/v1/problems returned status {resp.status}")
        data = json.loads(resp.read().decode("utf-8"))
        problems = data.get("items") or data.get("problems") or (data if isinstance(data, list) else [])
        if len(problems) == 0:
            raise AssertionError("Problem list returned 0 records")

def test_live_problem_detail():
    req = urllib.request.Request(f"{TARGET_URL}/api/v1/problems/1", headers={"User-Agent": "SmokeTest"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise AssertionError(f"/api/v1/problems/1 returned status {resp.status}")
        data = json.loads(resp.read().decode("utf-8"))
        if "statement_text" not in data and "statement" not in data:
            raise AssertionError("Problem detail missing statement")

def test_live_leaderboard():
    req = urllib.request.Request(f"{TARGET_URL}/api/v1/contests/1/leaderboard", headers={"User-Agent": "SmokeTest"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise AssertionError(f"Leaderboard returned status {resp.status}")
        data = json.loads(resp.read().decode("utf-8"))
        if "rankings" not in data:
            raise AssertionError("Leaderboard response missing 'rankings' key")

if __name__ == "__main__":
    print(f"=== Code Captain Critical-Path Smoke Test (Target: {TARGET_URL}) ===")
    run_step("1. Validate JavaScript syntax in index.html", test_js_syntax)
    run_step("2. Validate Python compilation", test_python_syntax)
    run_step("3. Validate required DOM elements", test_required_dom_elements)
    run_step("4. Validate required JS function bindings", test_required_js_functions)
    run_step("5. Validate live health probe", test_live_health)
    run_step("6. Validate live Problem Hub API", test_live_problems)
    run_step("7. Validate live Problem Detail API", test_live_problem_detail)
    run_step("8. Validate live Leaderboard API", test_live_leaderboard)
    print("\n[SUCCESS] All 8 critical-path smoke tests PASSED. Baseline is GREEN.")
