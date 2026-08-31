# Technical Architecture Document
## AI Revenue Recovery Agent

---

## 1. System Overview

A single-process, modular Python pipeline. No microservices, no distributed system — appropriate for a solo hackathon build with an 11-day timeline. Each module is independently testable and communicates via plain Python objects / JSON, not network calls (except the Razorpay executor).

```text
    250 PAYMENT ATTEMPTS
            │
            ▼
        DETECTOR
            │
            ▼
    Failure-rate spike?
            │
            ▼
        DIAGNOSER
            │
            ▼
     POLICY ENGINE
            │
       ┌────┴────┐
       │         │
    allowed    fraud/
       │        blocked
       ▼         │
    EXECUTOR     ▼
       │       HUMAN
       │       REVIEW
       │
    SUCCESS?
     ┌─┴──┐
    YES   NO
     │     │
     ▼     ▼
    STOP  CAP?
           │
        ┌──┴──┐
       NO     YES
        │      │
        ▼      ▼
     POLICY  ESCALATE
        │
        └───────┐
                ▼
             AUDIT LOG
                │
                ▼
             REPORT
                │
                ▼
       ₹ AT-RISK / ₹ RECOVERED
```

Orchestrated by a single `pipeline.py` entrypoint.

## 2. Module Specifications

### 2.1 `data_gen`
- **Input:** config (n_events, noise_rate, seed)
- **Output:** `data/events.json` — list of event objects
- **Schema:**
```json
{
  "order_id": "ord_0001",
  "amount": 1499.0,
  "customer_id": "cust_042",
  "payment_method": "card",
  "bank": "HDFC",
  "status": "failed",
  "failure_reason": "bank_timeout",
  "timestamp": "2026-08-30T10:15:00Z",
  "customer_segment": "repeat",
  "recoverable": true
}
```
- **Successful Event Example:**
```json
{
  "order_id": "ord_0002",
  "amount": 999.0,
  "customer_id": "cust_051",
  "payment_method": "card",
  "bank": "HDFC",
  "status": "success",
  "failure_reason": null,
  "timestamp": "2026-08-30T10:15:00Z",
  "customer_segment": "new",
  "recoverable": null
}
```
- `recoverable` is ground truth, used only for evaluation — never fed to detector/diagnoser.
- **Critical constraint on how `recoverable` is generated:** `recoverable` must NOT be a deterministic function of `failure_reason` (e.g., `bank_timeout` always → `true`). If it were, the diagnoser's "root cause → action" mapping would trivially predict recoverability with 100% accuracy regardless of whether its logic is any good, making the reported precision/recall meaningless. Instead, assign `recoverable` **probabilistically per failure_reason bucket** — e.g.:

  | failure_reason | P(recoverable = true) |
  |---|---|
  | bank_timeout | ~85% (mostly transient, but some bank timeouts mask a genuinely dead card/account) |
  | gateway_outage | ~90% |
  | insufficient_funds | ~70% (some customers never get funds in time) |
  | expired_card | ~40% (some customers update, most don't within the window) |
  | wrong_otp | ~60% |
  | invalid_card / fraud_flagged | ~5% (occasionally a false-positive fraud flag is genuinely recoverable) |

  This guarantees every `failure_reason` bucket contains **both** recoverable and unrecoverable examples, so the diagnoser is actually being tested on signal beyond the raw failure label, not just memorizing a 1:1 lookup that happens to already exist in the data.
- Deterministic via random seed for reproducibility (the *probabilities* are fixed and documented; the individual draws are seeded-random, so results are reproducible but not hardcoded).

### 2.2 `detector`
- **Input:** event list (containing both `success` and `failed` status events)
- **Logic:** rolling window failure-rate calculation per (bank, payment_method) computed as `failed / total_attempts`; flags failed events in windows where `current_failure_rate >= 3 * baseline_failure_rate`.
- **Output:** flagged event list with `{detection_reason, confidence}`

### 2.3 `diagnoser`
- **Input:** flagged event
- **Logic:** deterministic rule table mapping `failure_reason` (+ context) → one of `{bank_issue, card_issue, funds_issue, fraud_blocked}`
- **Output:** `{diagnosis, diagnosis_confidence}`
- Stretch goal: swap in a trained classifier (logistic regression / random forest) and report both rule-based and ML precision/recall for comparison — not required for MVP.

### 2.4 `policy_engine`
- **Input:** diagnosed event + current attempt count for that `order_id` (read from `audit_log`, `stage='execute'` rows, count of prior attempts — see Security & Access §4.1 for the binding definition: retries and nudges share one counter)
- **Logic:**
  1. Check global cap first (max 3 total attempts per order_id) — if already at cap, return `no_action` / stop, regardless of diagnosis
  2. If under global cap, look up category-specific rule from the hardcoded policy table
  3. Return decision
- **Output:** `{action: retry|nudge|escalate|no_action, delay, attempt_number, reason}`
- This module is intentionally **not ML** — deterministic rule table only, for auditability. The global-cap-before-category-cap ordering is the key implementation detail that prevents the retry/nudge ambiguity described in Security & Access §4.1.

### 2.5 `executor`

**What "retry" actually means (binding definition):**

Razorpay does not expose an API to force-retry a specific failed payment for one-off (non-subscription) payments — a failed `payment_id` is terminal. What real recovery systems do, and what this executor does, is **create a new payment attempt against the same logical order**, not resurrect the old one. Concretely:

```
Original payment attempt (payment_id_1) → FAILED
        ↓
Policy engine decides: retry
        ↓
Executor calls Orders API: create a NEW Order
   (same amount, receipt = original order_id + attempt suffix,
    e.g. receipt="ord_0042-attempt-2")
        ↓
Executor calls Payment Links API: create a Payment Link against that new Order
        ↓
[TEST MODE ONLY] Executor simulates customer completing payment using
Razorpay's documented test-mode card numbers:
    - success: 4111 1111 1111 1111
    - failure: a documented Razorpay test failure card / forced failure flag
        ↓
Razorpay test-mode returns: SUCCESS or FAILURE for the new payment_id
        ↓
Result logged against the ORIGINAL order_id, with the new payment_id
recorded as an attempt reference
```

**What "nudge" actually means:** a nudge is a *notification* action, not a payment action — the executor does not call any payment-creation API. It calls `notifier.py`, which writes a log entry ("would notify customer via [channel] with payment link [url]") and does not perform a real send in this build. In a production system this would map to Razorpay's Payment Link notification/reminder capability (SMS/email resend on an existing link); for this project it is mocked entirely.

**Why this matters for the demo:** if asked "what exactly are you retrying," the answer is precise: *"we create a fresh Order + Payment Link scoped to the same original order, and simulate its outcome using Razorpay's test-mode test cards — we're not force-resurrecting the failed payment, because Razorpay doesn't support that for one-off payments."* Given the current compressed timeline (see PRD §10, Feature Ticket List T00), this must be validated FIRST, before any other module, not left until the executor is built — flagged as the top project risk in the PRD.

**Sub-modules:**
- `razorpay_client.py` — wraps Razorpay Python SDK, test-mode keys only:
  - `create_order(amount, receipt)` → Orders API
  - `create_payment_link(order_id)` → Payment Links API
  - `simulate_payment(payment_link_id, outcome: success|fail)` → uses Razorpay test-mode card numbers to drive the simulated result
- `notifier.py` — mock; writes "would send nudge to customer X via channel Y with link Z" to the log; no real send
- **Output:** `{execution_status: success|fail|skipped, new_payment_id, executed_at}`

### 2.6 `audit_log`
- **Storage:** SQLite (`audit.db`) — chosen over JSON files for query-ability in reporting
- **Schema (table `actions`):**
```
log_id INTEGER PRIMARY KEY AUTOINCREMENT,
event_id TEXT, order_id TEXT, stage TEXT, amount REAL,
diagnosis TEXT, action_taken TEXT, reasoning TEXT,
timestamp TEXT, outcome TEXT, amount_recovered REAL,
attempt_number INTEGER
```
- `stage` is required on every row and must be one of: `detect`, `diagnose`, `policy`, `execute`. This is what makes the audit trail unambiguous — one order produces multiple rows (one per stage per event it passes through), not one row summarizing everything. A judge reading `order_001, policy, bank_issue, retry, "bank/gateway issue → retry per policy"` knows exactly which pipeline stage produced that row, versus `order_001, execute, bank_issue, retry, "retry attempt #1 succeeded"` for the actual execution outcome.
- Each module calls `audit_log.record(stage=..., ...)` immediately after making its decision — no module bypasses logging, and no module writes on behalf of another stage.
- `timestamp` replaces the earlier separate `detected_at`/`executed_at` fields — since every row is already scoped to one `stage`, a single timestamp field per row is sufficient and removes redundancy.

### 2.7 `reporting`
- **Input:** reads `audit.db`
- **Output:** printed summary table + optional CSV export
- **Binding metric definitions (all figures computed ONLY from `stage = 'execute'` rows with a real `outcome`, never from `policy`-stage rows or the agent's decisions/intentions):**

  ```
  Total At-Risk Revenue  = SUM(amount) for all events that reached 'detect' stage
  Total Recovered Amount = SUM(amount_recovered) for 'execute' stage rows where outcome = 'success'
  Recovery Rate (%)      = (Total Recovered Amount ÷ Total At-Risk Revenue) × 100
  ```

  Worked example: ₹5,00,000 at risk (from detect-stage rows), ₹1,20,000 actually recovered (from execute-stage rows with `outcome = success`) → recovery rate = 24%.

- **Critical constraint:** recovery figures must never be derived from `policy`-stage decisions (i.e., "the agent decided to retry" is not "the agent recovered money"). Only a confirmed `execute`-stage row with `outcome = 'success'` counts toward recovered revenue. An event where the policy engine chose `retry` but the executor's simulated attempt returned `outcome = 'fail'` contributes ₹0 to recovered revenue — it counts only in the "attempted" bucket. This is what keeps the reported recovery rate honest and matches the PRD's full-batch, non-cherry-picked metrics requirement.
- Computes: total at-risk ₹, detected count, attempted count (policy-stage rows with action ≠ `no_action`), recovered count/₹ (execute-stage, outcome=success only), recovery rate, stopped-due-to-cap count, unresolved/flagged-for-human count

### 2.8 `pipeline.py`
- Single entrypoint: `python pipeline.py --n 250 --seed 42`
- Orchestrates the **agentic recovery loop**. For each flagged event, it loops through `diagnoser -> policy -> executor -> policy...` until an execution succeeds or the policy caps are hit and it escalates. Prints final report at end.

### 2.9 `dashboard` (optional/stretch)
- Streamlit app reading directly from `audit.db`
- Read-only — no write path from the dashboard

## 3. Data Flow Summary

1. `data_gen` writes `events.json` (source of truth for the run)
2. `detector` reads events, produces flagged subset (in-memory)
3. `diagnoser` annotates each flagged event once
4. For each diagnosed event, the orchestrator starts the recovery loop:
   a. `policy_engine` decides action per event (checks global and category caps)
   b. If `action` is `no_action` or `escalate`, the loop breaks.
   c. Otherwise, `executor` performs action (e.g. retry). In Batch mode, it uses a Simulation Executor writing to local `audit.db`. In Demo mode, it uses Razorpay Test Mode for the actual test transaction.
   d. If `executor` returns `success`, loop breaks.
   e. If `executor` returns `fail`, loop repeats from (a) (policy engine evaluates incremented attempt count).
5. Every stage writes its decision to `audit_log` immediately (not batched at the end) — ensures partial runs still have a valid audit trail
6. `reporting` aggregates `audit.db` into the final scorecard

## 4. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Fastest to build rules/pipeline logic solo |
| Payment API | Razorpay Python SDK, test mode | Required by hackathon track |
| Storage | SQLite | Zero-setup, queryable, sufficient for single-run batch |
| Data gen | `faker` + custom noise logic | Fast synthetic data with realistic variety |
| Dashboard (optional) | Streamlit | Fastest path to a clickable UI without frontend build time |
| Config | `.env` + `python-dotenv` | Keep Razorpay test keys out of source |

## 5. Environment & Config

```
RAZORPAY_KEY_ID=test_xxx
RAZORPAY_KEY_SECRET=test_xxx
BATCH_SIZE=250
RANDOM_SEED=42
DETECTION_THRESHOLD=2.0
```

## 6. Failure Handling

- Razorpay API errors (timeout, invalid request) are caught, logged as `execution_status: fail`, and do **not** crash the pipeline — the event is marked and the pipeline continues to the next.
- If `audit_log` write fails, the pipeline halts (audit trail is treated as non-optional — a silent gap would violate the core requirement).

## 7. What This Architecture Deliberately Avoids

- No microservices / message queues — unnecessary complexity for a single-run batch pipeline
- No ML in the policy engine — determinism and auditability are more valuable than adaptiveness for this track's bar
- No real notification delivery — out of scope, adds infra risk with no grading benefit
