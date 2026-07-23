import sys
from app.services.sandbox import SandboxEngine
from app.models.submission import LanguageEnum, SubmissionVerdict

def test_sandbox():
    print("Testing SandboxEngine with a simple Python script...")
    code = "print(int(input()) + 1)\n"
    engine = SandboxEngine(
        submission_id=9999,
        code=code,
        language=LanguageEnum.PYTHON3,
        time_limit=1.0,
        memory_limit=256
    )

    engine.stage()
    print("Code staged.")

    success, err = engine.compile()
    print(f"Compile phase: success={success}, err={err}")
    
    if success:
        # Test Case 1
        print("Running Test Case 1...")
        res = engine.execute_test_case("12\n", "13\n")
        print(f"Result: {res.verdict}, Time: {res.execution_time_ms}ms, Mem: {res.memory_consumed_kb}kb")
        if res.verdict != SubmissionVerdict.ACCEPTED:
            print(f"Failed. Error: {res.error_message}")
            engine.teardown()
            sys.exit(1)
            
        # Test Case 2
        print("Running Test Case 2 (TLE test)...")
        tle_engine = SandboxEngine(
            submission_id=10000,
            code="while True: pass\n",
            language=LanguageEnum.PYTHON3,
            time_limit=1.0,
            memory_limit=256
        )
        tle_engine.stage()
        res_tle = tle_engine.execute_test_case("12\n", "13\n")
        print(f"Result (TLE): {res_tle.verdict}, Time: {res_tle.execution_time_ms}ms")
        tle_engine.teardown()
        if res_tle.verdict != SubmissionVerdict.TIME_LIMIT_EXCEEDED:
            print("Failed. Should be TLE.")
            engine.teardown()
            sys.exit(1)
    
    engine.teardown()
    print("All tests passed.")

if __name__ == "__main__":
    test_sandbox()
