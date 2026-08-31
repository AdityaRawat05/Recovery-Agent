# Security & Access Document
## AI Revenue Recovery Agent

---

## 1. Purpose

This document defines what the agent is allowed to do, what it is never allowed to do, how credentials are handled, and how the "bounded and gated" requirement from the track brief is technically enforced — not just claimed.

## 2. Threat / Risk Model

This is a **defense-only, recovery-only** system. It never handles money offensively (no charging arbitrary amounts, no accessing accounts it wasn't scoped for, no exploiting payment flows). The realistic risks for this project are:

| Risk | Concern | Mitigation |
|---|---|---|
| Uncapped retries | Agent could retry a failing payment indefinitely, harming customer experience or looking like abuse | Hardcoded max-attempt caps per failure type + global cap |
| Acting on fraud cases | Agent could inadvertently "help" a fraudulent transaction succeed by retrying it | Fraud/blocked diagnosis → hard-coded to `no_action`, never reaches executor |
| Credential leakage | Razorpay API keys committed to repo / exposed in demo | `.env` file, gitignored, test-mode keys only, no prod keys ever used |
| Unbounded spend/action | Agent takes actions with no upper bound on customer contact or discount offered | Explicit stop conditions (see Section 4) |
| Silent/unlogged action | An action taken with no record, breaking auditability | Every executor call wrapped in a mandatory audit_log write; pipeline halts if logging fails |

## 3. Access Control

| Component | Access Level | Notes |
|---|---|---|
| Razorpay API | Test-mode key only, scoped to Orders/Payment Links | No production keys ever used or requested |
| `audit.db` | Local file, read/write by pipeline; read-only for dashboard | No external network exposure |
| Synthetic data | Fully synthetic, no real customer PII | `customer_id` values are generated, not real |
| `.env` file | Gitignored, never committed | Shared only via `.env.example` with placeholder values |

## 4. Bounded Action Rules (the "gates")

### 4.1 Definition of "attempt" (binding, applies everywhere in this document and the codebase)

> **Attempt = any single automated recovery action executed for an order — a payment retry counts as one attempt, and a customer nudge counts as one attempt. Both draw from the same counter.**

This removes the earlier ambiguity between "retry" and "nudge" being counted separately. Concretely: `retry #1` → attempt 1. `retry #2` → attempt 2. A subsequent `nudge #1` on the same order → attempt 3, and would hit the global cap (see below) before it could fire.

Per-category max-attempts figures below are a **ceiling within that category's own action type**, but the **global cap always applies first and wins** if it would be reached sooner.

### 4.2 Policy table

| Diagnosis | Allowed Action Type | Category Max Attempts | Min Delay Between Attempts | Hard Stop Condition |
|---|---|---|---|---|
| Bank/gateway issue | Retry payment | 2 | 15 minutes | 2nd retry fails → escalate to human review |
| Insufficient funds | Retry payment | 3 | 24 hours | 3rd retry fails → stop, mark unresolved |
| Expired/invalid card | Send nudge (never auto-retry) | 2 | 48 hours | No response after 2 nudges → stop |
| Fraud / blocked | **No automated action, ever** | 0 | N/A | Immediately flagged for human review |

### 4.3 Global limits (apply across all categories, take precedence)

| Rule | Value |
|---|---|
| Global cap | **Max 3 total attempts per order_id**, counting retries and nudges together (per definition in §4.1) |
| Low-value cutoff | Order value below configurable minimum (e.g., ₹50) → not pursued at all (cost of recovery exceeds value) |

**Worked example (resolves the ambiguity directly):** an order diagnosed as `bank_issue` gets retry #1 (attempt 1) and retry #2 (attempt 2), both fail. Category max for bank_issue (2) is reached, so the policy engine escalates to human review — it does **not** fall through to try a nudge, because bank_issue's allowed action type is retry-only. If a different order somehow qualified for both retry and nudge actions across its diagnosis history (e.g., re-diagnosed after a bank timeout resolves into a card issue), attempt count carries over from the same global counter — attempt 3 would be the last one permitted regardless of type, and the policy engine must check the global counter before allowing any action, not just the category counter.

**Design principle:** the policy engine is a fixed lookup table, not a model — so these limits are structurally impossible to exceed by inference drift or edge-case model behavior. This is a deliberate architectural choice (see Technical Architecture §2.4). The global cap check happens **before** the category check on every decision, so it is always the binding constraint when the two would otherwise disagree.

## 5. What the Agent Is Explicitly Forbidden From Doing

Per the track's "strictly defense-only, anything offense-capable is disqualified" requirement, and general good practice:

- Never initiates a charge/payment that wasn't already attempted and failed (no new unsolicited charges)
- Never retries or acts on any event diagnosed as fraud/blocked
- Never sends more than the capped number of customer contacts
- Never uses production Razorpay credentials
- Never stores or generates real PII
- Never exceeds its own documented policy table (enforced by code structure, not just convention)
- Contains no functionality that could be repurposed to probe, exploit, or attack a payment system (e.g., no card-testing loops, no brute-force logic)

## 6. Audit & Explainability Requirements

- Every action (or explicit non-action, e.g., "skipped — fraud") is logged with a reasoning string
- Logs are immutable within a run (append-only table, no updates/deletes)
- The batch report (see Technical Architecture §2.7) is generated purely from the audit log — ensuring the reported numbers can't drift from what actually happened

## 7. Demo-Time Safety Notes

- Only test-mode Razorpay test cards are used live (e.g., documented Razorpay test card numbers for success/failure simulation)
- No real payment instruments or real customer data touched at any point, including during the live demo
