# Code Captain: Database & Storage Architecture (Layer 3)

**Product Name:** Code Captain Online Judge  
**Document Version:** 1.0.0  
**Phase:** 3 — Databases & Storage (Foundation Phase)  
**Status:** Approved Baseline  
**Related Documents:** [docs/system-design.md](system-design.md), [docs/architecture.md](architecture.md)

---

## 1. Relational Database Overview

Code Captain uses **PostgreSQL 16 (via Neon Serverless)** with the **`pgvector`** extension for vector similarity search. The schema is normalized (3NF) to guarantee ACID integrity for competitive programming contests, timed penalties, and code evaluation histories.

---

## 2. Comprehensive Entity Schema Specification

### 1. `users` Table
Primary user identity and role assignment.
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `user_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `username` | `VARCHAR(64)` | No | — | Unique, Indexed (`ix_users_username`) |
| `password_hash` | `VARCHAR(256)` | Yes | `NULL` | Bcrypt hash. Nullable for pure OAuth accounts |
| `rating` | `INTEGER` | No | `1200` | Elo/contest performance rating |
| `role` | `ENUM('ADMIN', 'CONTESTANT', 'STUDENT')` | No | `'CONTESTANT'` | System RBAC authorization role |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit update timestamp |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `NULL` | Soft delete timestamp for account recovery |

---

### 2. `user_profiles` Table
Extended candidate profile data and preferences (1:1 with `users`).
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `profile_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `user_id` | `INTEGER` | No | — | Unique Foreign Key (`users.user_id` ON DELETE CASCADE) |
| `full_name` | `VARCHAR(128)` | Yes | `NULL` | Display name |
| `bio` | `TEXT` | Yes | `NULL` | Candidate bio |
| `preferred_language` | `ENUM('PYTHON3', 'CPP', 'JAVA')`| No | `'PYTHON3'` | Default arena language choice |
| `avatar_url` | `VARCHAR(512)` | Yes | `NULL` | Cloud object storage URL (S3/R2) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Timestamp |

---

### 3. `problems` Table
Curated competitive programming problem catalog with semantic embeddings.
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `problem_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `title` | `VARCHAR(255)` | No | — | Problem title, Indexed (`ix_problems_title`) |
| `statement_text` | `TEXT` | No | — | Markdown problem description & examples |
| `difficulty` | `ENUM('Easy', 'Medium', 'Hard')` | No | — | Algorithmic difficulty |
| `time_limit` | `FLOAT` | No | `1.0` | CPU execution timeout ceiling (seconds) |
| `memory_limit` | `INTEGER` | No | `256` | RAM ceiling (Megabytes) |
| `problem_embedding` | `vector(384)` | Yes | `NULL` | 384-dim embedding for semantic similarity |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit update timestamp |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `NULL` | Soft delete timestamp |

---

### 4. `tags` & `problem_tags` Tables
Many-to-many relationship classifying problems by DSA domain (e.g., Dynamic Programming, Trees).
* **`tags` Table**:
  * `tag_id`: `INTEGER` PK, Auto-inc
  * `tag_name`: `VARCHAR(64)` Unique, Indexed
* **`problem_tags` Table (Composite PK)**:
  * `problem_id`: `INTEGER` FK (`problems.problem_id` ON DELETE CASCADE)
  * `tag_id`: `INTEGER` FK (`tags.tag_id` ON DELETE CASCADE)

---

### 5. `test_cases` Table
Input/output evaluation cases for automated judging.
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `test_case_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `problem_id` | `INTEGER` | No | — | FK (`problems.problem_id` ON DELETE CASCADE), Indexed |
| `input_data` | `TEXT` | No | — | stdin data fed into candidate sandbox |
| `expected_output`| `TEXT` | No | — | stdout comparison baseline |
| `is_sample` | `BOOLEAN` | No | `FALSE` | Sample test cases visible to candidates |
| `is_hidden` | `BOOLEAN` | No | `TRUE` | Secret evaluation cases (never exposed to client) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Timestamp |

---

### 6. `submissions` Table
Immutable candidate code execution submissions.
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `submission_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `user_id` | `INTEGER` | No | — | FK (`users.user_id` ON DELETE CASCADE), Indexed |
| `problem_id` | `INTEGER` | No | — | FK (`problems.problem_id` ON DELETE CASCADE), Indexed |
| `code` | `TEXT` | No | — | Full source code evaluated |
| `language_enum` | `ENUM('C++', 'Python3', 'Java')` | No | — | Execution language |
| `verdict` | `ENUM('Pending', 'Accepted', 'Wrong Answer', 'Time Limit Exceeded', 'Memory Limit Exceeded', 'Runtime Error', 'Compilation Error')` | No | `'Pending'` | Judge outcome |
| `execution_time` | `FLOAT` | No | `0.0` | Execution latency in milliseconds |
| `memory_consumed`| `INTEGER` | No | `0` | RAM consumed in kilobytes |
| `code_embedding` | `vector(384)` | Yes | `NULL` | Vector representation for plagiarism detection |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Audit update timestamp |

---

### 7. `ai_reviews` Table
Automated code quality and static complexity analysis (1:1 with `submissions`).
| Column | Type | Nullable | Default | Description & Constraints |
|---|---|:---:|:---:|---|
| `review_id` | `INTEGER` | No | Auto-inc | Primary Key |
| `submission_id` | `INTEGER` | No | — | Unique FK (`submissions.submission_id` ON DELETE CASCADE) |
| `ai_feedback` | `TEXT` | No | — | Markdown evaluation feedback |
| `suggested_refactoring` | `TEXT` | No | — | Suggested cleaner code snippet |
| `code_quality_score` | `FLOAT` | No | — | Normalized score (0.0 – 100.0) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | Timestamp |

---

### 8. `contests`, `contest_problems`, `contest_leaderboard` Tables
Competitive contest scheduling and live scoring.
* **`contests` Table**:
  * `contest_id`: `INTEGER` PK, Auto-inc
  * `title`: `VARCHAR(255)` Indexed
  * `start_time`: `TIMESTAMP WITH TIME ZONE` Indexed
  * `end_time`: `TIMESTAMP WITH TIME ZONE`
  * `is_active`: `BOOLEAN` Default `FALSE`
* **`contest_problems` Table**:
  * `contest_id`: FK (`contests.contest_id` ON DELETE CASCADE)
  * `problem_id`: FK (`problems.problem_id` ON DELETE CASCADE)
  * `points`: `INTEGER` Default `100`
* **`contest_leaderboard` Table**:
  * `id`: `INTEGER` PK, Auto-inc
  * `contest_id`: FK (`contests.contest_id` ON DELETE CASCADE), Indexed
  * `user_id`: FK (`users.user_id` ON DELETE CASCADE), Indexed
  * `score`: `INTEGER` Default `0`
  * `penalty_time`: `INTEGER` Default `0` (minutes)
  * `last_submission_time`: `TIMESTAMP WITH TIME ZONE`

---

## 3. High-Traffic Query Paths & Indexing Strategy

To guarantee sub-50ms latency at scale, the database employs deliberate composite and vector indexes:

```sql
-- 1. Candidate submission history & profile filtering
CREATE INDEX ix_submissions_user_problem_created 
ON submissions (user_id, problem_id, created_at DESC);

-- 2. Global verdict statistics & analytical rollups
CREATE INDEX ix_submissions_verdict_created 
ON submissions (verdict, created_at DESC);

-- 3. Catalog filtering by difficulty and recency
CREATE INDEX ix_problems_difficulty_created 
ON problems (difficulty, created_at DESC);

-- 4. Contest leaderboard sorting (Score DESC, Penalty ASC)
CREATE INDEX ix_contest_leaderboard_rank 
ON contest_leaderboard (contest_id, score DESC, penalty_time ASC);

-- 5. Semantic Vector Search (HNSW Cosine Distance)
CREATE INDEX ix_problems_embedding_hnsw 
ON problems USING hnsw (problem_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 4. Object Storage vs. Database Partitioning

| Data Asset | Storage Location | Access Policy | Format / Limits |
|---|---|---|---|
| **Source Code (< 64 KB)** | Neon PostgreSQL (`submissions.code`) | Row-level authorization | Plaintext UTF-8 |
| **Candidate Avatars** | Cloudflare R2 / S3 | Public CDN read, Presigned PUT | JPEG/PNG, max 2 MB |
| **Large Test Cases (> 256 KB)** | Cloudflare R2 / S3 | Private bucket, Judge worker access | Gzipped plaintext stdin |
| **Exported Problem PDFs** | Cloudflare R2 / S3 | Presigned GET (15-min expiry) | Generated binary PDF |

---

## 5. Soft Delete Strategy

Accidental deletion of a Problem or Contest causes cascading historical data loss for all submitted candidates. We enforce:
* `deleted_at: TIMESTAMP WITH TIME ZONE NULL` on `problems`, `users`, and `contests`.
* Read queries automatically include `WHERE deleted_at IS NULL`.
* Admin "Purge" operations require explicit two-factor confirmation.

---

## 6. Migration & Backup Policy

* **Migration Tool:** Alembic (SQLAlchemy). All schema mutations must be tracked in `alembic/versions/`.
* **Execution Standard:** Never execute `CREATE TABLE` or `ALTER TABLE` manually in production.
* **Point-in-Time Recovery (PITR):** Neon Serverless provides continuous WAL archiving with 7-day point-in-time recovery.
