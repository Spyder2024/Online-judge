# ADR 0002: Dedicated Docker Container Execution Sandbox

**Date:** 2026-11-02  
**Status:** Accepted  
**Deciders:** Security & Infrastructure Lead  

---

## Context

An online judge platform must execute untrusted, potentially malicious user code (C++, Python, Java) thousands of times per day. Malicious or poorly-written submissions can attempt:
1. **Host Compromise (RCE)**: Reading environment variables, stealing database credentials, or tampering with the host operating system.
2. **Denial of Service (DoS)**: Spawning fork bombs, opening thousands of socket connections, or saturating disk and CPU.
3. **Sandbox Escapes**: Exploiting root vulnerabilities or unpatched kernel privileges.

Evaluating code directly via in-process `subprocess.run()` or `eval()` on the web server host is an unacceptable critical security vulnerability (classified as SEC-01 in our security audit).

## Decision

We chose to run all candidate code inside **dedicated, ephemeral Docker containers (`compiler-engine/Dockerfile`)** hardened with non-root privileges, Linux cgroups, and network isolation.

### Hardened Sandbox Specification
1. **Unprivileged Runner User**: All compilation and execution runs under user `sandbox` (`UID 10001`, `GID 10001`). The container drops all Linux root capabilities (`CAP_SYS_ADMIN`, `CAP_NET_RAW`).
2. **Network Egress Blocked**: The container execution flags enforce `--net none`, blocking all outbound socket connections, SSRF attacks, and external C2 botnet communication.
3. **Hardware Resource Quotas (cgroups)**:
   - CPU quota: `--cpus 1.0`
   - Memory limit: `--memory 256m --memory-swap 256m`
   - Process limit: `--pids-limit 64` (completely mitigates fork bombs)
4. **Read-Only Root Filesystem**: The container root filesystem is mounted read-only (`--read-only`), with only a restricted `/tmp` tmpfs volume for temporary source code compilation.
5. **Deterministic Signal Handling**: When user code exceeds the per-problem time limit (e.g. 1.0s or 2.0s), the runner issues a `SIGKILL` to ensure immediate process termination.

## Consequences

### Positive
* **Zero Host Vulnerability**: Even if candidate code executes `rm -rf /` or attempts to dump `/etc/shadow`, it runs as an unprivileged user inside a read-only container with zero host impact.
* **Deterministic Resource Throttling**: Memory leaks and infinite loops are bounded strictly by the kernel cgroup quotas.
* **Multi-Language Parity**: Official GCC 13, Python 3.12, and OpenJDK 17 run in a standard Alpine Linux environment matching production judge standards.

### Negative / Trade-Offs
* Running containerized workers requires Docker daemon access or an external container runtime (e.g. Fly.io, Railway, AWS ECS) rather than pure serverless functions.
* Startup overhead: Mitigated by maintaining a pre-warmed pool of execution containers.
