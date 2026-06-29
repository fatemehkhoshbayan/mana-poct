# Slice 1 — QC Scenario Eval Report

**Date:** 2026-06-29  
**Evaluator:** manual curl + `run_eval.py`  
**Scope:** All five QC decision scenarios (A–E) against the live `POST /api/sessions/{id}/messages` SSE endpoint.

---

## Test method

Each scenario was run as a fresh session with a fixed script of **4 turns**, one per FSM variable:

| Turn | Variable | Example input |
|------|----------|---------------|
| 1 | Consumable | `"Lot expiry 2026-12-31, opened 5 days ago"` |
| 2 | Storage | `"Refrigerated at 4C, no excursions, freeze indicator not tripped"` |
| 3 | Historical | `"Zero consecutive QC failures"` |
| 4 | EQA | `"No active EQA cycle"` |

**Pass criterion:** session resolves in ≤ 4 turns with the correct `scenario` value and all four `variables` matching expected.

**Infrastructure:** `docker compose up` on localhost, OPENROUTER_API_KEY set, no DB fixtures required.

---

## Scenario definitions

| ID | Label | Trigger | Expected decision |
|----|-------|---------|-------------------|
| **A** | Hard Block | Lot expired (`2026-01-15`) | `LOCKDOWN_DEVICE`, `is_qc_locked: true` |
| **B** | Environmental Breach | 9°C excursion for 3h (refrigerated) | `FAIL_QC_SESSION` |
| **C** | Hardware Drift | 2 consecutive QC failures | `TRIGGER_SECONDARY_BIO_REF_RUN` |
| **D** | High-Priority Sprint | Active EQA cycle, deadline ≤ 7 days, PENDING | `PASS_QC_HIGH_PRIORITY` |
| **E** | Standard Clearance | All variables pass | `PASS_QC` |

---

## Run 1 — `cohere/north-mini-code:free`

**Date:** 2026-06-28  
**Score: 3/5 in 4 turns | 5/5 with extra turns**

| Scenario | In 4 turns | Notes |
|----------|-----------|-------|
| A | PASS | — |
| B | STUCK | historical never recorded; empty assistant replies on turns 3–4 |
| C | STUCK | EQA turn skipped by model |
| D | PASS | — |
| E | PASS | — |

**Root cause:** Free-tier rate limits caused `429` errors on some turns. On those turns the backend returned an error SSE event, the assistant replied with an empty string, and the session stalled. All five scenarios resolved with 5–6 turns total (no extra human turns needed, just additional messages).

---

## Run 2 — `google/gemini-2.5-flash-lite`

**Date:** 2026-06-28  
**Score: 2/5 in 4 turns | 2/5 resolved**

| Scenario | In 4 turns | Notes |
|----------|-----------|-------|
| A | FAIL | Resolved only after extra turns |
| B | FAIL | Storage recorded correctly but historical skipped |
| C | PASS | — |
| D | PASS | — |
| E | FAIL | Nothing recorded in first 4 turns (session had zero known flags) |

**Root cause:**
1. `freeze_indicator_tripped` omitted — the model called `record_storage(storage_type="refrigerated")` without setting `freeze_indicator_tripped`, leaving storage `not known`, which cascaded to skip historical and EQA turns.
2. Scenario E entirely stuck with `known_flags=[False, False, False, False]` — model did not call any tool on the first two turns.

This model was **worse** than the free Cohere model in practice for this task.

---

## Run 3 — `google/gemini-3.1-flash-lite` (pre prompt fix)

**Date:** 2026-06-29  
**Score: 3/5 in 4 turns | 3/5 resolved**

| Scenario | In 4 turns | Notes |
|----------|-----------|-------|
| A | STUCK | `storage_known=False` — `freeze_indicator_tripped` omitted |
| B | PASS | — |
| C | PASS | — |
| D | STUCK | `storage_known=False` same root cause |
| E | PASS | — |

**Root cause:** Identical to gemini-2.5. Model omitted `freeze_indicator_tripped` on storage turns.  
**No rate-limit errors** (notable improvement over Cohere free tier).

---

## Prompt fix applied

**Files changed:** `app/orchestration/tools.py`, `app/orchestration/prompts.py`

Three targeted changes:

1. **`RECORD_STORAGE` tool description** — explicitly states `freeze_indicator_tripped` must always be set to `true` or `false`, and that storage is not considered known until it is.
2. **`freeze_indicator_tripped` parameter description** — marked `REQUIRED — always set to true or false, never omit`.
3. **`ASK_STORAGE` objective prompt** — reframed freeze-indicator from an *optional fallback* to a *mandatory question*, with explicit instruction to call the tool as soon as `storage_type` and `freeze_indicator_tripped` are both known.

No model change, no architecture change, no code change to the rules engine or FSM.

---

## Run 4 — `google/gemini-3.1-flash-lite` (post prompt fix)

**Date:** 2026-06-29  
**Score: 5/5 in 4 turns | 5/5 resolved**

| Scenario | In 4 turns | turns | time | Variables |
|----------|-----------|-------|------|-----------|
| A | **PASS** | 4 | 13.8s | `consumable_status: FAIL` |
| B | **PASS** | 4 | 8.0s | `storage_condition: FAIL` |
| C | **PASS** | 4 | 8.7s | `historical_error_flag: FAIL` |
| D | **PASS** | 4 | 9.2s | `eqa_status: WARN` |
| E | **PASS** | 4 | 7.6s | all PASS/STANDARD |

**Zero errors. All decisions correct. Total runtime: ~48 seconds.**

---

## Summary

| Model | Pass (4 turns) | Resolved | Rate limit errors | Avg time/scenario |
|-------|---------------|----------|-------------------|-------------------|
| `cohere/north-mini-code:free` | 3/5 | 5/5 (extra turns) | Yes (429s) | ~45s |
| `google/gemini-2.5-flash-lite` | 2/5 | 2/5 | No | ~30s |
| `google/gemini-3.1-flash-lite` pre-fix | 3/5 | 3/5 | No | ~10s |
| **`google/gemini-3.1-flash-lite` post-fix** | **5/5** | **5/5** | **No** | **~10s** |

---

## Conclusion

**Root cause was prompting, not model capability.** Making `freeze_indicator_tripped` mandatory in both the tool schema and the objective prompt was sufficient to achieve 5/5 on a lightweight free-tier model. No larger model is required for Slice 1.

**Recommendation for Slice 2+:** Keep `google/gemini-3.1-flash-lite` for development speed and cost. Upgrade to a stronger model (e.g. `anthropic/claude-3.7-sonnet`) only if Slice 2 tool-calling complexity (lookup tools + fallback handling) causes regression. Re-run `evals/run_eval.py` after each slice to detect regressions.
