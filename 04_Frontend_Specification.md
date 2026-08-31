# Frontend Specification Document
## AI Revenue Recovery Agent — Dashboard (Optional/Stretch Component)

**Note:** Per the build plan, this is a stretch-goal module — only build if core pipeline (data_gen → detector → diagnoser → policy → executor → audit → reporting) is complete and tested first. A clean CLI/printed report alone satisfies the track's requirements. This spec exists so that *if* time permits, you're not designing on the fly.

**STATUS UPDATE (Aug 30):** Given ~3.5 build days remain before the Sep 3 deadline, this entire module is now **cut from scope** (see PRD §3/§10 and Feature Ticket List Epic 10) rather than merely deprioritized. This document is kept for reference only, in case time genuinely remains after every P0 ticket is done and verified — treat that as unlikely.

---

## 1. Purpose

A read-only viewer over the audit log, so judges can see the pipeline's decisions visually instead of reading raw JSON/DB rows during the demo.

## 2. Tech Choice

**Streamlit** — chosen over React/HTML for build speed; a solo builder with ~1-2 hours of frontend time budgeted should not hand-roll a JS frontend. Streamlit reads directly from `audit.db` (SQLite), no separate API layer needed.

## 3. Screens

### 3.1 Summary Screen (default view)
**Purpose:** The scorecard — this is what judges see first.

Contents:
- Header: "Revenue Recovery Agent — Batch Report"
- Big-number row (4 metric cards):
  - Total At-Risk Revenue (₹)
  - Recovered Revenue (₹) + recovery rate (%)
  - Events Detected (count)
  - Stopped-by-Cap / Unresolved (count)
- A simple bar chart: recovered vs unrecovered ₹, broken down by diagnosis category (bank_issue / card_issue / funds_issue / fraud_blocked)

### 3.2 Event Table Screen
**Purpose:** Drill-down, browsable list of individual events.

Columns:
```
order_id | amount | diagnosis | action_taken | attempts | outcome | amount_recovered
```
- Sortable/filterable by `diagnosis` and `outcome` (Streamlit's built-in dataframe filtering is sufficient — no custom filter UI needed)
- Row click (or a "view detail" button) expands to show the full reasoning trail for that order (all audit log rows for that order_id, in timestamp order)

### 3.3 Graceful Failure Highlight (demo aid)
**Purpose:** A pinned/highlighted section showing one specific pre-selected order that hit its retry cap and was correctly stopped — this directly supports the "show one failure handled gracefully" requirement.

Contents:
- Order ID, timeline of attempts (retry 1 → failed → retry 2 → failed → capped → escalated to human review), each step timestamped with its reasoning string
- Rendered as a simple vertical timeline/list, not a complex visualization

## 4. Layout

```
┌────────────────────────────────────────────┐
│  Revenue Recovery Agent — Batch Report      │
├─────────┬─────────┬─────────┬───────────────┤
│ At-Risk │Recovered│Detected │ Stopped/Unres. │
│  ₹X     │ ₹Y (Z%) │   N1    │      N2        │
├────────────────────────────────────────────┤
│  [Bar chart: recovered vs unrecovered]       │
├────────────────────────────────────────────┤
│  Tabs: [ Event Table ] [ Graceful Failure ]  │
│  ...................................         │
└────────────────────────────────────────────┘
```

## 5. Data Contract (what the frontend reads)

The dashboard is strictly read-only against `audit.db`. No write path. Query pattern:

```sql
-- Summary metrics (execute-stage rows only — that's where outcomes/₹ land)
SELECT diagnosis, outcome, SUM(amount_recovered), COUNT(*)
FROM actions WHERE stage = 'execute' GROUP BY diagnosis, outcome;

-- Event table (execute-stage rows, most recent first)
SELECT order_id, amount, diagnosis, action_taken, outcome, amount_recovered
FROM actions WHERE stage = 'execute' ORDER BY timestamp DESC;

-- Single order full timeline, across all stages (detect → diagnose → policy → execute)
SELECT * FROM actions WHERE order_id = ? ORDER BY timestamp ASC;
```

## 6. Visual Style

- Minimal, no custom theming needed beyond Streamlit defaults — judges are evaluating substance, not design polish, per the track's grading bar
- Use color only functionally: green for recovered, amber for stopped/unresolved, red for fraud-flagged — not decoratively

## 7. Explicitly Out of Scope

- No authentication/login screens (single-user, local demo tool)
- No editing/manual override UI (would contradict the "agent decides, logs, and is auditable" design — a manual override path adds complexity with no grading benefit)
- No mobile responsiveness — demo is on a laptop
- No real-time/live streaming updates — batch is run once, then viewed statically
