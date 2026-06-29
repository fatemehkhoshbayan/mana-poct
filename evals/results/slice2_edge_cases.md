# Slice 2 — Edge Case Live Run Report

**Date:** 2026-06-29  
**Model:** `google/gemini-3.1-flash-lite`  
**Infrastructure:** `docker compose up` on localhost, `OPENROUTER_API_KEY` set  
**Method:** Custom operator messages sent directly to `POST /api/sessions/{id}/messages` SSE endpoint — not from `evals/scenarios.json`  
**Result: 21/21 passed**

---

## Test method

Each case was a fresh session with custom messages designed to target a specific edge condition.
Pass criterion: the `decision` SSE event carries the expected `scenario` value (or no decision fires, for FSM-incomplete cases).

No code was changed. All messages were hand-crafted for this run.

---

## Scenario A — Consumable FAIL variants

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `A-open-vial-31d` | Valid expiry, vial opened **31 days** ago | 1 | **PASS** — A RED `LOCKDOWN_DEVICE` |
| `A-lookup-expired-lot` | `LOT-EXPIRED-1` looked up from DB (expiry 2026-01-15) | 1 | **PASS** — A RED `LOCKDOWN_DEVICE` |
| `A-lookup-old-vial` | `LOT-OLD-VIAL-1` looked up from DB (opened ~40 days ago) | 1 | **PASS** — A RED `LOCKDOWN_DEVICE` |

All resolved in **1 turn** via early exit. Variables recorded: `consumable_status: FAIL` only (storage/historical/EQA not collected).

---

## Consumable boundaries

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `boundary-consumable-expiry-today` | Expiry = **2026-06-29** (today), opened 0 days ago | 4 | **PASS** — E GREEN `PASS_QC` |
| `boundary-consumable-age-30` | Expiry valid, vial opened **exactly 30 days** ago | 4 | **PASS** — E GREEN `PASS_QC` |

Confirmed: boundary is inclusive — expiry today and age = 30 both count as PASS.

---

## Scenario B — Storage FAIL variants

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `B-refrigerated-excursion` | Peak **9°C for 3 hours** (refrigerated) | 2 | **PASS** — B YELLOW `FAIL_QC_SESSION` |
| `B-room-temp-breach` | Room-temp peak **30.1°C** | 2 | **PASS** — B YELLOW `FAIL_QC_SESSION` |

Both resolved in **2 turns** (consumable + storage). Variables: `consumable: PASS`, `storage: FAIL`.

---

## Storage boundaries

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `boundary-storage-excursion-1.9h` | 8.1°C for **1.9 hours** (below 2h threshold) | 4 | **PASS** — E GREEN `PASS_QC` — `storage: PASS` |
| `boundary-room-temp-30` | Room-temp peak exactly **30.0°C** (at threshold, not over) | 4 | **PASS** — E GREEN `PASS_QC` — `storage: PASS` |
| `fsm-temp-only-incomplete` | Operator says **"4°C right now"** only — no freeze indicator answer | 2 | **PASS** — no decision fired; FSM correctly waited |

The `fsm-temp-only-incomplete` case confirms the LLM does not infer freeze indicator status from a current temperature reading — it asks again rather than assuming.

---

## Historical boundary and lookup

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `boundary-historical-1-failure` | Exactly **1 consecutive failure** in 30 days | 4 | **PASS** — E GREEN `PASS_QC` — `historical: PASS` |
| `C-lookup-device` | `SN-FAIL-HIST-2` looked up from DB (**3 failures**) | 3 | **PASS** — C BLUE `TRIGGER_SECONDARY_BIO_REF_RUN` |

Confirmed: threshold is `≥ 2` — 1 failure is PASS. Device lookup auto-merges the failure count and triggers early exit.

---

## EQA boundaries

| Case | Trigger | Turns | Result |
|------|---------|-------|--------|
| `D-eqa-deadline-7d` | Active cycle, deadline **2026-07-06** (exactly 7 days), PENDING | 4 | **PASS** — D GREEN `PASS_QC_HIGH_PRIORITY` — `eqa: WARN` |
| `boundary-eqa-8d-standard` | Active cycle, deadline **2026-07-07** (8 days), PENDING | 4 | **PASS** — E GREEN `PASS_QC` — `eqa: STANDARD` |
| `boundary-eqa-submitted` | Active cycle, deadline **2026-07-02** (3 days), **SUBMITTED** | 4 | **PASS** — E GREEN `PASS_QC` — `eqa: STANDARD` |

Confirmed: the 7-day window is inclusive (≤ 7 → WARN). SUBMITTED status neutralises even an imminent deadline.

---

## Precedence — multiple simultaneous failures

| Case | Simultaneous failures | Winner | Turns | Result |
|------|----------------------|--------|-------|--------|
| `precedence-A-beats-B` | Consumable FAIL + storage FAIL | **A** | 1 | **PASS** — A RED, variables show both FAIL |
| `precedence-B-beats-C` | Storage FAIL + 2 historical failures | **B** | 2 | **PASS** — B YELLOW, variables show storage FAIL + historical FAIL |
| `precedence-C-beats-D` | 2 historical failures + EQA WARN | **C** | 3 | **PASS** — C BLUE, variables show historical FAIL + eqa WARN |

Confirmed first-match-wins chain: A > B > C > D > E.

---

## Dialogue / orchestration behaviour

| Case | Description | Turns | Result |
|------|-------------|-------|--------|
| `out-of-order-all-four` | All four variables volunteered in **one message** | 1 | **PASS** — E GREEN in a single turn |
| `correction-pass-to-fail` | Valid expiry given first, then **corrected to expired** | 2 | **PASS** — A RED; decision fired after correction |
| `correction-fail-to-pass` | Expired lot given first, then **corrected to valid**; full collection continues | 5 | **PASS** — E GREEN; no premature resolution after initial expired input |

Out-of-order confirmed: the LLM calls all four `record_*` tools in one iteration when given enough information, resolving in a single turn.

Correction confirmed: `mark_known` re-derives flags from scratch — correcting an expired date to valid un-blocks the session, and correcting valid to expired triggers immediate Scenario A.

---

## Summary

| Category | Cases | Passed | Failed |
|----------|-------|--------|--------|
| Scenario A variants | 3 | 3 | 0 |
| Consumable boundaries | 2 | 2 | 0 |
| Scenario B variants | 2 | 2 | 0 |
| Storage boundaries (incl. FSM edge) | 3 | 3 | 0 |
| Historical boundary + lookup | 2 | 2 | 0 |
| EQA boundaries | 3 | 3 | 0 |
| Precedence | 3 | 3 | 0 |
| Dialogue / orchestration | 3 | 3 | 0 |
| **Total** | **21** | **21** | **0** |

---

## What this run did NOT cover

These are exercised only by unit tests (`pytest`, no server required) and were not re-run live:

| Category | Cases |
|----------|-------|
| Unknown lot/device lookups | `LOT-NOPE`, `UNKNOWN-999` → `found: false`, `consumable_known` / `historical_known` stay False |
| Placeholder serial rejection | `lookup_device("unknown")` → rejected with error message, no DB call |
| Partial excursion data | `max_excursion_temp_c` set but `excursion_duration_hours` absent → `storage_known: False` |
| Stale flag reset | `consumable_known=True` with `lot_number=None` → resets to False on next `mark_known` |
| `record_storage` sanitisation | `freeze_indicator_tripped=False` inferred from temp-only reading is stripped |

These are deterministic FSM/tool behaviours that don't require the LLM call path to test.
