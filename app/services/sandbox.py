import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from app.models.submission import LanguageEnum, SubmissionVerdict

@dataclass
class ExecutionResult:
    verdict: SubmissionVerdict
    execution_time_ms: float
    memory_consumed_kb: int
    error_message: str = ""


class SandboxEngine:
    def __init__(self, submission_id: int, code: str, language: LanguageEnum, time_limit: float, memory_limit: int):
        self.submission_id = submission_id
        self.code = code
        self.language = language
        # Convert time limit to ms, add slight overhead tolerance for docker startup
        self.time_limit_ms = time_limit * 1000
        self.memory_limit_mb = memory_limit
        
        # Temp staging area
        base_tmp = Path(tempfile.gettempdir()) / "online_judge_sandbox"
        self.sandbox_dir = base_tmp / str(submission_id)
        
        # Determine language config
        if language == LanguageEnum.CPP:
            self.image = "gcc:latest"
            self.file_name = "main.cpp"
            self.compile_cmd = ["g++", "-O2", "main.cpp", "-o", "main"]
            self.run_cmd = ["./main"]
        elif language == LanguageEnum.PYTHON3:
            self.image = "python:3.12-slim"
            self.file_name = "main.py"
            self.compile_cmd = None
            self.run_cmd = ["python", "main.py"]
        elif language == LanguageEnum.JAVA:
            self.image = "openjdk:17-slim"
            self.file_name = "Main.java"
            self.compile_cmd = ["javac", "Main.java"]
            self.run_cmd = ["java", "Main"]
        else:
            raise ValueError("Unsupported language")

    def stage(self):
        """Create sandbox directory and write code."""
        os.makedirs(self.sandbox_dir, exist_ok=True)
        with open(self.sandbox_dir / self.file_name, "w", encoding="utf-8") as f:
            f.write(self.code)

    def teardown(self):
        """Clean up the sandbox directory."""
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)

    def _get_docker_base_cmd(self) -> List[str]:
        """Base Docker run command with strict security constraints."""
        # Normalize paths for Docker mount, especially on Windows
        # We need absolute path. Path.absolute() works.
        host_path = str(self.sandbox_dir.absolute())
        return [
            "docker", "run", "--rm",
            "--net=none",
            f"--memory={self.memory_limit_mb}m",
            f"--memory-swap={self.memory_limit_mb}m",
            "--cpus=1.0",
            "--pids-limit=64",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "-v", f"{host_path}:/workspace",
            "-w", "/workspace",
            "-i" # Keep STDIN open even if not attached
        ]

    def compile(self) -> Tuple[bool, str]:
        """Compile the code if necessary. Returns (Success, Error Message)."""
        if not self.compile_cmd:
            return True, ""
            
        cmd = self._get_docker_base_cmd() + [self.image] + self.compile_cmd
        try:
            # Add 10 seconds tolerance for compilation
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                return False, result.stderr
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Compilation Time Limit Exceeded"
        except Exception as e:
            return False, f"Compilation Sandbox Error: {str(e)}"

    def execute_test_case(self, input_text: str, expected_output: str) -> ExecutionResult:
        """Execute the code against a single test case."""
        cmd = self._get_docker_base_cmd() + [self.image] + self.run_cmd
        start_time = time.perf_counter()
        
        try:
            # We enforce a timeout slightly higher than the problem's limit
            # to allow Docker overhead. We'll measure actual time in Python.
            # A more precise way in prod is wrapping execution inside container with `time`.
            timeout_seconds = (self.time_limit_ms / 1000.0) + 2.0 
            
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            
            # Note: measuring exact memory requires cgroups inspection from inside.
            # We will default to a placeholder (0) or try parsing it if a wrapper was used.
            # Docker enforces the limit anyway.
            memory_kb = 0
            
            if elapsed_ms > self.time_limit_ms:
                return ExecutionResult(SubmissionVerdict.TIME_LIMIT_EXCEEDED, elapsed_ms, memory_kb)
                
            if result.returncode != 0:
                # 137 is OOM kill in Docker
                if result.returncode == 137:
                    return ExecutionResult(SubmissionVerdict.MEMORY_LIMIT_EXCEEDED, elapsed_ms, memory_kb)
                return ExecutionResult(SubmissionVerdict.RUNTIME_ERROR, elapsed_ms, memory_kb, result.stderr)

            # Compare outputs
            actual_output = result.stdout.strip()
            expected_clean = expected_output.strip()
            
            # Simple whitespace-agnostic comparison for lines
            actual_lines = [l.strip() for l in actual_output.splitlines() if l.strip()]
            expected_lines = [l.strip() for l in expected_clean.splitlines() if l.strip()]
            
            if actual_lines == expected_lines:
                return ExecutionResult(SubmissionVerdict.ACCEPTED, elapsed_ms, memory_kb)
            else:
                return ExecutionResult(SubmissionVerdict.WRONG_ANSWER, elapsed_ms, memory_kb)

        except subprocess.TimeoutExpired:
            return ExecutionResult(SubmissionVerdict.TIME_LIMIT_EXCEEDED, self.time_limit_ms, 0)
        except Exception as e:
            return ExecutionResult(SubmissionVerdict.RUNTIME_ERROR, 0, 0, str(e))
