# Code Captain: System Design Document (Layer 1)

**Product Name:** Code Captain Online Judge  
**Document Version:** 1.0.0  
**Phase:** 1 — System Design (Plan Phase)  
**Author:** Software Architect & Founder  
**Status:** Approved Baseline  

---

## 1. Executive Summary & Product Vision

Code Captain is a recruiter-grade, high-performance competitive programming and technical interview preparation SaaS platform. It combines a curated catalog of algorithmic challenges, an isolated multi-language code execution sandbox, real-time WebSocket test streaming, automated AI code review, and live contest leaderboards.

---

## 2. Target Users & Core Workflows

We define three primary user personas to drive architecture decisions:

### Persona 1: Alex — The Job-Seeking Candidate ("Cadet")
* **Profile:** Computer Science student or software engineer preparing for FAANG/tier-1 technical interviews.
* **Core Workflow:**
  1. Lands on **Problem Hub**, filters by topic (`Dynamic Programming`, `Graphs`) or difficulty (`Medium`).
  2. Opens **Coding Arena**, selects preferred language (`Python`, `C++`, `Java`).
  3. Uses **"Run Code"** to test algorithm against sample test cases without risking submission penalties.
  4. Submits solution via `Ctrl+Enter`; watches real-time test execution progress bar.
  5. Reviews side-by-side **Test Case Diff** on failures or benchmark percentiles on `ACCEPTED` (*"Beats 94.2% of submissions"*).
  6. Reads automated **AI Mentor** complexity analysis and refactoring tips.
  7. Clicks **"Next Problem →"** to maintain continuous practice flow.

### Persona 2: Priya — The Competitive Programmer ("Navigator")
* **Profile:** Active competitive programmer participating in weekly algorithmic contests and hackathons.
* **Core Workflow:**
  1. Enrolls in a scheduled timed **Contest**.
  2. Solves problems under strict algorithmic constraints (Time: 1.0s, Memory: 256 MB).
  3. Submits code; each failed submission incurs a 10-minute penalty on the contest clock.
  4. Monitors the live **Leaderboard** driven by Redis sorted sets with sub-second ranking updates.

### Persona 3: Marcus — The Platform Administrator & Contest Host ("Fleet Admiral")
* **Profile:** Lead recruiter or contest organizer curating problem sets and reviewing candidate submissions.
* **Core Workflow:**
  1. Authenticates via secure Admin credentials.
  2. Authors new problem statements with Markdown, constraints, input/output specifications, and reference test cases.
  3. Uploads bulk hidden evaluation test suites.
  4. Schedules and moderates live contests.
  5. Monitors system health, queue depth, and compiler sandbox throughput via `/health`.

---

## 3. Tenancy & Account Model

### Tenancy Model
* **Multi-tenant with Row-Level Isolation:** All users share a unified, horizontally scalable PostgreSQL database. Every user-owned entity (`drafts`, `submissions`, `contest_entries`) strictly references `user_id` and enforces row-level ownership at the database query layer.

### Account Tiers & Resource Limits
| Feature | Free Tier ("Cadet") | Pro Tier ("Captain") | Admin / Host ("Fleet Admiral") |
|---|:---:|:---:|:---:|
| **Catalog Access** | All 524 Public Problems | All Public + Pro Collections | Full Authoring & Management |
| **Submission Rate Limit** | 5 submissions / minute | 20 submissions / minute | Unlimited |
| **AI Mentor Reviews** | 10 reviews / day | Unlimited reviews | Unlimited |
| **Contest Access** | Public Contests | Public & Private Contests | Contest Host & Analytics |
| **Execution Timeout** | Standard 2.0s CPU cap | Priority queue, 2.0s CPU cap | Configurable per problem |
| **Price** | $0 / month | $15 / month | Enterprise Licensing |

---

## 4. Data Volume & Traffic Projections (Year One)

All estimates are grounded in explicit mathematical modeling:

### 1. User Base & Daily Traffic (DAU)
* **Registered Users (Year 1):** 10,000 candidates
* **Daily Active Users (DAU):** 1,000 active candidates (10% engagement ratio)
* **Average Daily Sessions:** 1,000 DAU × 1.5 sessions = 1,500 daily sessions
* **Problem Views:** 1,000 DAU × 15 views/day = **15,000 problem views / day**
* **Code Submissions:** 1,000 DAU × 8 submissions/day = **8,000 code submissions / day**

### 2. Request Rates & Concurrency
* **Average Submissions per Second:**  
  $$\text{Avg Rate} = \frac{8,000\text{ submissions}}{86,400\text{ seconds}} \approx 0.093\text{ req/sec}$$
* **Peak Submission Window:** 4 hours during evening contest and interview prep hours (50% of daily volume):  
  $$\text{Peak Window} = \frac{4,000\text{ submissions}}{14,400\text{ seconds}} \approx 0.28\text{ req/sec}$$
* **Burst Factor (Contest Starts):** $15\times$ peak traffic = **~4.2 to 5 submissions / second**.
* **Read Traffic Peak (Problem Hub & Leaderboard):** ~25 to 30 requests / second.

### 3. Storage Growth Projections (Year One)
* **Submissions Table:** 8,000 submissions/day × 365 days = $2.92 \times 10^6$ rows/year.
  * Average source code size: 2 KB.
  * Row metadata (verdict, runtime, memory, error log): 1.5 KB.
  * Annual Submission Storage: $2.92\text{M} \times 3.5\text{ KB} \approx \mathbf{10.2\text{ GB / year}}$.
* **Problem Catalog & Test Cases:** 524 problems × 50 test cases × 1 KB avg = **~26.2 MB** (static).
* **User Accounts & Profiles:** 10,000 users × 2 KB = **~20 MB**.
* **Total Year 1 Database Footprint:** **~12 to 15 GB** (comfortably within serverless Neon PostgreSQL tiers).

---

## 5. Non-Negotiables (Zero-Tolerance Boundaries)

1. **Absolute Sandbox Isolation (Zero Host Compromise):**
   * Arbitrary user-submitted code MUST execute in an isolated container under an unprivileged `sandbox` user (UID 10001).
   * Network access inside the execution sandbox MUST be disabled (`--net none`).
   * Hard OS-level resource limits: CPU quota ($1.0$ vCPU), Memory limit ($256\text{ MB}$), Process limit (`nproc 64`), Read-only root filesystem.
2. **Deterministic Timeouts (Zero Worker Starvation):**
   * Code execution exceeding CPU limit (e.g. 2.0s) MUST be forcefully terminated via `SIGKILL`. Infinite loops must never lock background execution workers.
3. **Zero IDOR & Data Leakage (Strict Authorization):**
   * No candidate can view another candidate's private code submissions or draft buffers unless explicitly flagged as public on a contest leaderboard.
   * Hidden judge evaluation test cases MUST NEVER be returned to the client browser in API response payloads.
4. **Submission Idempotency:**
   * Rapid double-clicks or client retries MUST pass an `Idempotency-Key` or submission debounce window to prevent duplicate penalty strikes on contest clocks.
5. **No Secret Leaks:**
   * API keys, database credentials, and JWT signing secrets MUST NEVER be present in client-side bundles or repository history.

---

## 6. Explicit Trade-Offs ("What We Are NOT Building Yet")

To ensure rapid execution and rock-solid stability, we deliberately exclude the following from early milestones:

| Feature / Pattern | Deliberate Decision | Rationale |
|---|---|---|
| **Microservices / Kubernetes** | **REJECTED** | A clean, modular monolith with asynchronous task workers handles 1,000 DAU with $10\times$ lower operational complexity. |
| **Obscure Language Support** | **REJECTED** | Limit sandbox to Python 3.12, C++20, and Java 17 (covers >95% of all technical interviews and CP). |
| **Complex Payment Gateways** | **DEFERRED** | Mock Pro subscription tier first; integrate Stripe / Razorpay in Phase 5 after core retention is verified. |
| **WebRTC Video Proctoring** | **REJECTED** | Code Captain is a developer training and contest judge platform, not an invasive remote proctoring utility. |
| **Custom Language Interpreters**| **REJECTED** | Use official GCC, CPython, and OpenJDK distributions rather than custom in-memory WASM runtimes to ensure 100% LeetCode/Codeforces parity. |

---

## 7. Layer 1 Verification Checklist

- [x] Personas have concrete user workflows, not generic demographic profiles.
- [x] Multi-tenancy model is clearly justified with row-level security.
- [x] Traffic and data growth calculations contain explicit mathematical modeling.
- [x] Non-negotiables are concrete, measurable, and testable (sandbox escape, timeouts, IDOR).
- [x] Explicit "What We Are NOT Building Yet" section prevents architectural scope creep.
