import time
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

from app.models.submission import LanguageEnum, SubmissionVerdict
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    verdict: SubmissionVerdict
    execution_time_ms: float
    memory_consumed_kb: int
    output: str = ""
    error_message: str = ""


def inject_driver_code(user_code: str, language: LanguageEnum, input_text: str) -> str:
    """
    Directive 2 / 3: Appends dynamic LeetCode-style driver code wrapper to the bottom of user submission.
    Executes user function / Solution class method with testcase inputs and prints result to stdout.
    """
    if language != LanguageEnum.PYTHON3:
        return user_code

    escaped_input = input_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    driver_code = """

# === DYNAMIC LEETCODE DRIVER CODE INJECTION ===
if __name__ == '__main__':
    import sys, json, ast, inspect

    raw_input_str = "{ESCAPED_INPUT_PLACEHOLDER}"
    
    local_env = {}
    global_env = dict(globals())
    parsed_args = []
    if raw_input_str.strip():
        try:
            if "=" in raw_input_str and not raw_input_str.strip().startswith("def ") and not raw_input_str.strip().startswith("class "):
                import re
                clean_assign_str = re.sub(r',\\s*([a-zA-Z_][a-zA-Z0-9_]*\\s*=)', r'\\n\\1', raw_input_str)
                exec(clean_assign_str, global_env, local_env)
                parsed_args = list(local_env.values())
        except Exception:
            local_env = {}

        if not parsed_args:
            for line in raw_input_str.splitlines():
                line_s = line.strip()
                if not line_s:
                    continue
                try:
                    parsed_args.append(json.loads(line_s))
                except Exception:
                    try:
                        parsed_args.append(ast.literal_eval(line_s))
                    except Exception:
                        parsed_args.append(line_s)

    target_fn = None
    if 'Solution' in globals() and inspect.isclass(globals()['Solution']):
        try:
            sol_obj = globals()['Solution']()
            methods = [m for m in dir(sol_obj) if not m.startswith('_')]
            if methods:
                target_fn = getattr(sol_obj, methods[0])
        except Exception:
            pass

    if not target_fn:
        user_fns = [
            obj for name, obj in globals().items()
            if inspect.isfunction(obj) and not name.startswith('_') and obj.__module__ == '__main__'
        ]
        if user_fns:
            target_fn = user_fns[-1]

    if target_fn:
        try:
            res = target_fn(*parsed_args) if parsed_args else target_fn()
            if res is not None:
                if isinstance(res, (dict, list, bool, int, float, str)):
                    print(json.dumps(res, separators=(',', ':')))
                else:
                    print(res)
        except Exception as err:
            sys.stderr.write(f"RuntimeError: {err}\\n")
            sys.exit(1)
""".replace("{ESCAPED_INPUT_PLACEHOLDER}", escaped_input)
    return user_code + driver_code


class SandboxEngine:
    """
    Compiler Engine Client integrating external Node.js Compiler API Microservice (AlgoU-Online-Compiler-2).
    Sends HTTP POST requests to the microservice endpoint.
    """
    def __init__(self, submission_id: int, code: str, language: LanguageEnum, time_limit: float, memory_limit: int):
        self.submission_id = submission_id
        self.code = code
        self.language = language
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        
        # Normalize language string for Node.js compiler API
        if language == LanguageEnum.CPP:
            self.lang_str = "cpp"
        elif language == LanguageEnum.PYTHON3:
            self.lang_str = "py"
        elif language == LanguageEnum.JAVA:
            self.lang_str = "java"
        else:
            self.lang_str = "cpp"

    def stage(self):
        """No-op staging for HTTP microservice."""
        pass

    def teardown(self):
        """No-op teardown for HTTP microservice."""
        pass

    def compile(self) -> Tuple[bool, str]:
        """Microservice handles compilation dynamically on POST /run."""
        return True, ""

    async def execute_test_case_remote_async(self, input_text: str, expected_output: str) -> ExecutionResult:
        """
        Execute code against a single test case via HTTP POST to Node.js Compiler API.
        Payload: {"language": "<lang>", "code": "<code>", "input": "<input_text>"}
        """
        # Directive 2: Dynamic Driver Code Injection & Mandatory Server-Side Logging
        final_code = inject_driver_code(self.code, self.language, input_text)
        logger.info(f"Submitting code: {final_code}")

        payload = json.dumps({
            "language": self.lang_str,
            "code": final_code,
            "input": input_text
        }).encode("utf-8")

        urls = [settings.COMPILER_ENGINE_FALLBACK_URL, settings.COMPILER_ENGINE_URL]
        start_time = time.perf_counter()
        
        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=float(self.time_limit or 10.0)) as resp:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    
                    if resp.status != 200:
                        logger.error(f"Non-200 HTTP status from compiler: {resp.status}")
                        return ExecutionResult(
                            verdict=SubmissionVerdict.RUNTIME_ERROR,
                            execution_time_ms=elapsed_ms,
                            memory_consumed_kb=0,
                            error_message=f"Compiler Microservice Error: HTTP {resp.status}"
                        )

                    body = resp.read().decode("utf-8")
                    data = json.loads(body)

                    # Directive 2: Log raw compiler response JSON
                    logger.info(f"Compiler Response: {data}")

                    raw_output = data.get("output") or data.get("stdout") or ""
                    raw_error  = data.get("error")  or data.get("stderr") or data.get("message") or ""

                    # Directive 1: Strict Check for Stderr / Errors / Crashes FIRST
                    if raw_error and str(raw_error).strip():
                        err_str = str(raw_error).strip()
                        is_compilation_err = any(
                            sig in err_str for sig in [
                                "SyntaxError", "IndentationError", "compilation failed",
                                "g++", "javac", "error:", "invalid syntax", "compile error"
                            ]
                        )
                        verdict = SubmissionVerdict.COMPILATION_ERROR if is_compilation_err else SubmissionVerdict.RUNTIME_ERROR
                        logger.warning(f"Execution halted: {verdict.value} | Error details: {err_str}")
                        return ExecutionResult(
                            verdict=verdict,
                            execution_time_ms=elapsed_ms,
                            memory_consumed_kb=0,
                            error_message=err_str
                        )

                    # Directive 3: Ironclad Output Comparison
                    actual_output = str(raw_output).strip()
                    expected_output_str = str(expected_output).strip()

                    # Directive 2: Log Output Comparison
                    logger.info(f"Expected: {expected_output_str}, Received: {actual_output}")

                    # Empty stdout when expected output is non-empty -> WRONG ANSWER
                    if not actual_output and expected_output_str:
                        return ExecutionResult(
                            verdict=SubmissionVerdict.WRONG_ANSWER,
                            execution_time_ms=elapsed_ms,
                            memory_consumed_kb=12400,
                            output=actual_output,
                            error_message="Wrong Answer: Code produced no stdout output."
                        )

                    if actual_output != expected_output_str:
                        return ExecutionResult(
                            verdict=SubmissionVerdict.WRONG_ANSWER,
                            execution_time_ms=elapsed_ms,
                            memory_consumed_kb=12400,
                            output=actual_output,
                            error_message=f"Wrong Answer: Output mismatch. Expected: {repr(expected_output_str)}, Received: {repr(actual_output)}"
                        )

                    return ExecutionResult(
                        verdict=SubmissionVerdict.ACCEPTED,
                        execution_time_ms=elapsed_ms,
                        memory_consumed_kb=12400,
                        output=actual_output
                    )
            except (urllib.error.URLError, TimeoutError) as err:
                err_str = str(err).lower()
                is_timeout = isinstance(err, TimeoutError) or "timed out" in err_str or (hasattr(err, "reason") and ("timed out" in str(err.reason).lower() or isinstance(err.reason, TimeoutError)))
                if is_timeout:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.warning(f"Execution timed out after {elapsed_ms:.2f}ms")
                    return ExecutionResult(
                        verdict=SubmissionVerdict.TIME_LIMIT_EXCEEDED,
                        execution_time_ms=elapsed_ms,
                        memory_consumed_kb=0,
                        error_message="Time Limit Exceeded: Execution timed out."
                    )
                continue
            except Exception as exc:
                logger.warning(
                    "Compiler microservice request failed for url=%s submission_id=%s: %s",
                    url, self.submission_id, exc
                )
                continue

        # Microservice fault tolerance
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            verdict=SubmissionVerdict.RUNTIME_ERROR,
            execution_time_ms=elapsed_ms,
            memory_consumed_kb=0,
            error_message="Compiler Microservice Error: Unable to reach execution engine at COMPILER_ENGINE_URL."
        )
