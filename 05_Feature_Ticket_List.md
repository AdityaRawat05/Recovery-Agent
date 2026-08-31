# Feature Ticket List
## AI Revenue Recovery Agent — Solo Build

**Today: August 30. Deadline: September 3. ~3.5 usable build days remain.**
Status buckets replace calendar days — the earlier "Day 1...Day 11" plan assumed an Aug 23 start that didn't happen. This list reflects where things actually stand as of Aug 30 and what's realistically achievable. Update status inline as you complete each ticket.

**Status legend:** `DONE` | `IN PROGRESS` | `NEXT` | `STRETCH (cut first under any time pressure)`
Format: `[ID] Title — STATUS — Priority — Acceptance Criteria`

---

### Epic 0: Risk-First Validation (do this before anything else)

- **[T00] Razorpay test-mode POC** — **NEXT — P0 — DO THIS FIRST, TODAY** — 30-45 min timeboxed
  Acceptance: a disposable script (not part of the real pipeline) confirms — using real test-mode keys — that you can (1) create an Order, (2) create a Payment Link against it, (3) simulate both a success and a failure outcome using Razorpay's documented test-mode card numbers. This validates the exact mechanism documented in Technical Architecture §2.5 before any other module is built on top of that assumption. **This was originally scheduled for "Day 7" in the old plan — that was too late even under the original 11-day timeline, and is now the single highest-priority item given 3.5 days remain.**

---

### Epic 1: Setup

- **[T01] Repo scaffold + env setup** — NEXT — P0
  Acceptance: repo structure matches architecture doc; `.env.example` present; Razorpay test-mode keys working (confirmed by T00)

- **[T02] Write policy rule table** — NEXT — P0
  Acceptance: policy table (retry caps, delays, stop conditions, global cap, attempt definition per Security & Access §4.1-4.3) hardcoded in `policy/policy_rules.py`, matching the Security & Access doc exactly

---

### Epic 2: Synthetic Data

- **[T03] Build event schema + generator** — NEXT — P0
  Acceptance: `data_gen/generator.py` produces N events matching schema; supports seed for reproducibility

- **[T04] Inject realistic noise via probabilistic recoverable assignment** — NEXT — P0
  Acceptance: `recoverable` is assigned per-event via a probability draw keyed on `failure_reason` (see Architecture §2.1 probability table), NOT a fixed deterministic mapping; every `failure_reason` bucket contains both recoverable and unrecoverable examples in the generated batch (spot-checked via printed cross-tab of `failure_reason` × `recoverable`)

- **[T05] Generate 250-event batch for testing** — NEXT — P0
  Acceptance: `data/events.json` exists with 250 rows, passes schema validation

---

### Epic 3: Detector

- **[T06] Implement threshold/spike detection logic** — NEXT — P0
  Acceptance: detector flags events where failure rate in a `(bank, payment_method)` segment exceeds threshold within a time window; each flagged event carries a `detection_reason` string naming the segment stats that triggered it (per the detect→flag chain agreed earlier); unit test with synthetic spike confirms detection fires

- **[T07] Tune detection threshold against test batch** — NEXT — P1
  Acceptance: flagging rate on 250-event batch is neither ~0% nor ~100% (sanity range e.g. 20-60%)

---

### Epic 4: Diagnoser

- **[T08] Implement rule-based root cause classifier** — NEXT — P0
  Acceptance: every flagged event receives one of 4 diagnosis labels; no unhandled `failure_reason` values (explicit default case)

- **[T09] Validate diagnoser against ground truth** — NEXT — P1
  Acceptance: precision/recall computed against `recoverable` field from generator; numbers printed/logged honestly (no cherry-picking); since T04 now guarantees non-trivial recoverable distribution, these numbers are meaningful rather than artificially perfect

- ~~[T10] Train ML classifier as alternative diagnoser~~ — **CUT (was STRETCH, now explicitly out of scope per PRD §3/§10, do not attempt with 3.5 days left)**

---

### Epic 5: Policy Engine

- **[T11] Implement policy lookup engine** — NEXT — P0
  Acceptance: given a diagnosis + current attempt count, returns correct action per policy table; global cap check runs BEFORE category check (per Security & Access §4.1-4.3); unit tests cover all 4 diagnosis types + edge cases (low-value order, repeat offender, mixed retry+nudge attempt count)

- **[T12] Enforce per-order and global attempt caps** — NEXT — P0
  Acceptance: automated test confirms no order in a full batch run ever exceeds its category's max attempts or the global cap of 3 total attempts (retries + nudges combined, per binding definition in Security & Access §4.1)

- **[T13] Enforce fraud/blocked hard stop** — NEXT — P0
  Acceptance: automated test confirms fraud-diagnosed events never reach the executor

---

### Epic 6: Executor

*(Only start this after T00 POC is confirmed working — do not discover Razorpay API surprises here.)*

- **[T14] Razorpay test-mode client wrapper** — NEXT — P0
  Acceptance: implements the exact mechanism validated in T00 and documented in Technical Architecture §2.5 — `create_order`, `create_payment_link`, `simulate_payment` (new Order + Payment Link per retry attempt, NOT resurrecting the original failed payment)

- **[T15] Mock notifier for nudge actions** — NEXT — P0
  Acceptance: nudge actions produce a logged "would send" entry referencing a payment link; no real send occurs; no payment-creation API called for nudges

- **[T16] Handle executor failures gracefully** — NEXT — P0
  Acceptance: simulated API failure does not crash pipeline; event marked failed and pipeline continues

---

### Epic 7: Audit Trail

- **[T17] SQLite audit log schema + writer** — NEXT — P0
  Acceptance: `audit_log.record(stage=..., ...)` callable from every module; schema includes required `stage` column (`detect`/`diagnose`/`policy`/`execute`) per Technical Architecture §2.6 — this is what makes rows unambiguous

- **[T18] Wire audit logging into every module** — NEXT — P0
  Acceptance: end-to-end run produces one audit row per decision point per stage — no silent/unlogged actions; a single order_id can be traced through all 4 stages via its rows

---

### Epic 8: Reporting

- **[T19] Batch summary report generator** — NEXT — P0
  Acceptance: running `report.py` against a completed `audit.db` prints total at-risk ₹, recovered ₹/rate, stopped count, unresolved count; recovery rate = recovered ÷ at-risk × 100 (per Architecture §2.7 formula); a unit test confirms recovered ₹ is computed ONLY from `stage='execute', outcome='success'` rows — a synthetic case where policy decides `retry` but execution `fails` must contribute ₹0 to recovered revenue

- ~~[T20] CSV export of report~~ — **STRETCH, only if time remains after T19 + full pipeline integration**

---

### Epic 9: Pipeline Integration

- **[T21] End-to-end pipeline orchestrator** — NEXT — P0
  Acceptance: single command (`python pipeline.py --n 250 --seed 42`) runs all stages and prints final report with no manual steps

- **[T22] Fresh-clone smoke test** — NEXT — P0
  Acceptance: cloning repo fresh, following README setup steps, and running pipeline works with zero undocumented steps

---

### Epic 10: Dashboard — **CUT FROM SCOPE**

- ~~[T23] Streamlit summary screen~~ — **CUT**
- ~~[T24] Streamlit event table + drill-down~~ — **CUT**
- ~~[T25] Graceful-failure highlight view~~ — **CUT — replicate this as a CLI-printed highlighted section instead (cheap, see T28)**

Given 3.5 build days, a dashboard is not achievable without risking the P0 pipeline. A clean printed/CLI report satisfies the track's requirements — judges are grading substance (audit trail, honest metrics, bounded actions), not UI polish.

---

### Epic 11: Documentation & Demo

- **[T26] Write README** — NEXT — P0
  Acceptance: includes problem statement, architecture summary, policy table, honest metrics, run instructions

- **[T27] Script the demo walkthrough** — NEXT — P0
  Acceptance: 3-5 min script written, includes the one graceful-failure moment called out explicitly, AND includes the explicit scope statement from PRD §3 ("we're specifically solving payment degradation, where an unusual increase in failures indicates recoverable revenue risk") stated up front

- **[T28] Select and verify the graceful-failure demo case** — NEXT — P0
  Acceptance: a specific order_id is confirmed in the audit log to show the full "retry → retry → capped → escalated" sequence across all 4 stages, ready to reference live (print this order's full timeline as a standalone CLI output for the demo, replacing the cut Streamlit highlight view from T25)

- **[T29] Full rehearsal** — NEXT — P0
  Acceptance: complete run-through of demo, timed, no reliance on unsaved state

---

### Revised Priority Summary (3.5 days left)

**Everything not marked CUT or STRETCH above is now effectively P0** — there is no more slack for "should complete" vs "must complete" the way there was under the original 11-day plan. The only things explicitly removed from scope are the Streamlit dashboard (Epic 10) and the ML-diagnoser comparison (T10), plus CSV export (T20) as the one remaining true stretch item.

**Suggested compressed sequencing:**
1. **Right now:** T00 (Razorpay POC) — do not skip or defer this
2. **Rest of today (Aug 30):** T01, T02, T03, T04, T05
3. **Aug 31:** T06, T07, T08, T09, T11, T12, T13
4. **Sep 1:** T14, T15, T16, T17, T18
5. **Sep 2:** T19, T21, T22, T26, T27, T28, T29
6. **Sep 3:** submit early, do not use the deadline day for new building

If slippage happens (likely), cut in this order: T20 (CSV) → T09's depth (keep the metric, cut extra analysis) → T07 (ship with default threshold, skip tuning) — but T00, T11-T13 (policy caps), T17-T18 (audit), and T19 (honest reporting) are the ones a judge will actually probe, so protect those above all else.
