# Product Requirements Document (PRD)
## AI Revenue Recovery Agent — Payment Degradation & Recovery

**Track:** Razorpay Hackathon — Track 03: AI Revenue Recovery
**Owner:** Aditya (solo builder)
**Deadline:** September 3
**Today:** August 30 — **4 calendar days / ~3.5 usable build days remain**
**Status:** Draft v2.0 — replanned for compressed timeline (see §10)

---

## 1. Problem Statement

Merchants lose revenue silently through failed payments, abandoned checkouts, failed subscription renewals, and unpaid invoices. Today this is either ignored (money is simply lost) or handled manually — someone notices a failure, investigates why, and decides whether to retry or follow up. This process is slow, inconsistent, doesn't scale, and has no audit trail.

## 2. Goal

Build an agent that automatically **detects** at-risk revenue, **diagnoses** the root cause of each failure, **decides** on a bounded recovery action, **executes** it via Razorpay test-mode APIs, and **reports** honest, measured results — including cases it correctly chose not to act on.

## 3. Scope

**Explicit scope statement (state this during demo):** This system detects **payment degradation** — abnormal segment-level failure spikes — as the signal for at-risk revenue. It is not a general individual-failure detector. A single isolated failure (e.g., one customer's expired card) that occurs while its segment is otherwise healthy will not be flagged by the detector. This is a deliberate scope boundary, not a gap: "an unusual increase in failures indicates recoverable revenue risk" is the specific problem this build solves, and it should be stated as such rather than implied.

**In scope (MVP — revised for compressed timeline, see §10):**
- Payment degradation detection (failure-rate spikes by segment/bank/method)
- Root-cause diagnosis (bank issue / card issue / funds issue / fraud)
- Rule-based recovery policy engine with explicit caps and stop conditions
- Execution via Razorpay test-mode (retries) + simulated notification (nudges)
- Full audit trail of every decision
- Batch-level report with recovery rate and ₹ recovered (CLI/printed output — see §10, dashboard is cut)

**Out of scope (not this build):**
- Checkout drop-off recovery, subscription dunning, B2B receivables chasing, voice recovery (may reference as future work, not built)
- Real SMS/email delivery (simulated/logged only)
- Any offense-capable or exploit-adjacent logic
- Production-grade auth, multi-tenant support, real customer PII
- **Streamlit dashboard — cut given remaining time; see §10** (was previously stretch, now explicitly dropped, not just deprioritized)
- **ML-based diagnoser comparison — cut given remaining time; see §10**

## 4. Users

- **Primary:** Hackathon judges evaluating technical rigor and the stated "bar"
- **Simulated end user:** A merchant operations dashboard user (not built as a real login-based product, but designed as if it were)

## 5. Success Metrics (what "done" looks like)

| Metric | Target |
|---|---|
| Synthetic batch size | ≥ 200 events |
| Diagnoser accuracy vs ground truth | Reported honestly, no target — must just be measured |
| Recovery rate | Reported honestly (expect realistic 20-40% range, not 90%+) |
| Every action logged | 100% — no unlogged action |
| Retry/attempt caps respected | 100% — zero rule violations in audit log |
| Demo includes 1 graceful failure | Yes, scripted and shown live |

## 6. User Stories

1. As a merchant, I want failed payments automatically flagged so I don't have to manually monitor a dashboard.
2. As a merchant, I want to know *why* a payment failed, not just that it failed.
3. As a merchant, I want the system to retry intelligently (right timing, right cap) instead of spamming customers or retrying pointlessly.
4. As a merchant, I want fraud-flagged cases to never be auto-retried — only surfaced for human review.
5. As a merchant, I want a report showing exactly how much revenue was recovered and how.
6. As a judge, I want to see the reasoning behind every automated action (explainability).
7. As a judge, I want to see the system stop itself correctly when limits are hit (boundedness).

## 7. Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | System generates a synthetic batch of failed-payment events with realistic noise |
| FR2 | System detects at-risk events using explainable threshold rules |
| FR3 | System classifies root cause into 4 fixed buckets |
| FR4 | System applies a fixed, documented policy table to decide action |
| FR5 | System never exceeds per-order or global attempt caps |
| FR6 | System never auto-retries fraud/blocked cases |
| FR7 | System executes retries via Razorpay test-mode API |
| FR8 | System logs every decision with timestamp + reasoning string |
| FR9 | System produces a batch summary report (recovered ₹, rate, stopped count, unresolved count) |

## 8. Non-Functional Requirements

- **Explainability:** every automated decision must have a human-readable reason string
- **Determinism:** given the same input batch and policy table, results must be reproducible
- **Honesty:** no cherry-picked demo data; full-batch metrics only
- **Safety:** strictly defense/recovery only — no offense-capable logic (disqualifying if violated)

## 9. Risks

| Risk | Mitigation |
|---|---|
| Synthetic data too easy/unrealistic → inflated metrics | Probabilistic `recoverable` assignment per failure_reason (not deterministic) — see Technical Architecture §2.1 |
| Solo build time overrun (now the dominant risk with 3.5 days left) | Dashboard and ML-diagnoser stretch goals are already cut from scope, not just deprioritized — see §10 |
| **Razorpay test-mode API behavior unclear — HIGHEST PRIORITY RISK given compressed timeline** | **Validate the exact retry mechanism (new Order + Payment Link per attempt, per Technical Architecture §2.5) FIRST, before writing any other module — do this today, Aug 30, as a standalone throwaway script, not on the day the executor is built** |
| Demo failure live | Rehearse with a pre-scripted, known-good graceful-failure case |

## 10. Current Status & Revised Plan

**Reality check:** the original plan assumed an Aug 23 start and 11 build days. Today is Aug 30 — that window did not happen as planned, and only ~3.5 usable build days remain before the Sep 3 deadline. Continuing to reference "Day 1 / Day 2..." against the original calendar is misleading. The plan below uses status buckets instead of calendar days, per the current feature ticket list.

**Status legend:** `DONE` / `IN PROGRESS` / `NEXT` / `STRETCH (cut if any slippage)`

As of Aug 30 (confirm/correct if any of this has actually been started):
- `DONE`: Planning documents (this PRD, architecture, security, ticket list) — no code yet
- `NEXT` (today, Aug 30, before anything else): Razorpay test-mode POC — confirm Orders + Payment Links + test-card simulation actually behave as documented in Technical Architecture §2.5, in a disposable script, before building any pipeline module on top of that assumption
- `NEXT`: synthetic data generator → detector → diagnoser → policy engine → executor → audit log (compressed, target: complete by end of Sep 1)
- `NEXT`: reporting + full pipeline integration, README, demo script (target: Sep 2)
- `STRETCH — CUT`: Streamlit dashboard, ML-diagnoser comparison — do not attempt unless the above is fully done with a full day still free

See the Feature Ticket List document for the authoritative, up-to-date status of every individual ticket.
