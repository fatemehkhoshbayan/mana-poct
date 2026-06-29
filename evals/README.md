# evals/

End-to-end evaluation framework for the MANA POCT QC Assistant.

```
evals/
├── README.md              ← this file
├── scenarios.json         ← canonical 5-scenario fixture (happy paths)
├── run_eval.py            ← CLI runner (no extra deps, stdlib only)
└── results/
    ├── slice1_model_comparison.md   ← Slice 1 evaluation report
    └── slice2_edge_cases.md         ← Slice 2 edge-case live run report
```

---

## Quick start

```bash
# 1. Start the backend
cd /path/to/mana-poct && docker compose up -d

# 2. Run all scenarios (needs OPENROUTER_API_KEY set in .env)
python evals/run_eval.py

# 3. Run specific scenarios
python evals/run_eval.py --scenarios A E

# 4. Save to a custom path
python evals/run_eval.py --out evals/results/my_run.json
```

Exit code `0` = all scenarios passed. Exit code `1` = one or more failed. Exit code `2` = backend unreachable.

---

## Scenario fixture — `scenarios.json`

Each entry defines a complete conversation script for one of the five QC decision paths.

```jsonc
{
  "id": "E",                    // scenario letter A–E
  "label": "Standard Clearance",
  "description": "All variables pass — device cleared.",
  "expected_scenario": "E",    // matched against SSE decision event
  "expected_variables": { ... },
  "messages": [                 // 4 scripted user turns
    "Lot number LOT-FRESH-1, expiry 2026-12-31, opened 5 days ago",
    "Refrigerated at 4C ...",
    ...
  ]
}
```

> **Important:** Turn 1 must include a **lot number**. The FSM requires `lot_number` + `lot_expiry_date` before marking consumable known. Messages with expiry only will not resolve.

### Variable status values

| Key | PASS | FAIL | WARN |
|-----|------|------|------|
| `consumable_status` | lot valid + open vial ≤ 30 days | lot expired OR vial > 30 days | — |
| `storage_condition` | no excursion, freeze indicator not tripped | excursion > threshold OR freeze tripped | — |
| `historical_error_flag` | < 2 consecutive failures | ≥ 2 consecutive failures | — |
| `eqa_status` | no active cycle OR deadline > 7 days OR SUBMITTED | — | active + deadline ≤ 7 days + PENDING |

### Thresholds and boundaries

| Variable | Threshold | Boundary behaviour |
|----------|-----------|-------------------|
| Consumable expiry | `expiry_date >= today` | Expiry today → PASS |
| Open-vial age | `age <= 30 days` | Age = 30 → PASS; age = 31 → FAIL |
| Refrigerated excursion | `temp > 8°C AND duration > 2h` | 8.1°C for 1.9h → PASS; 8.1°C for 2.1h → FAIL |
| Room-temp excursion | `temp > 30°C` | Exactly 30.0°C → PASS; 30.1°C → FAIL |
| Historical failures | `failures >= 2` | 1 failure → PASS; 2 → FAIL |
| EQA deadline | `deadline_days <= 7 AND PENDING` | 7 days → WARN; 8 days → STANDARD |
| EQA submitted | SUBMITTED always → STANDARD | Even with imminent deadline |

---

## What `scenarios.json` covers

`scenarios.json` contains the five **happy-path** scenarios — one canonical trigger per scenario letter. It is designed for regression testing after code changes, not exhaustive coverage.

For edge cases, boundaries, precedence, lookup paths, and dialogue robustness, see:
- **Live edge-case run:** [slice2_edge_cases.md](results/slice2_edge_cases.md)
- **Unit tests:** `back-end/app/tests/` (pytest, no server required)

---

## Edge cases NOT in `scenarios.json`

The following are covered by the live edge-case run and/or unit tests but are **not** in the `scenarios.json` fixture:

| Category | Case |
|----------|------|
| Consumable A | Open-vial age 31 days (valid expiry) → A |
| Consumable A | `lookup_lot` on `LOT-EXPIRED-1` → A |
| Consumable A | `lookup_lot` on `LOT-OLD-VIAL-1` (vial >30d) → A |
| Consumable boundary | Expiry today → PASS |
| Consumable boundary | Open-vial age exactly 30 days → PASS |
| Storage B | Refrigerated excursion >8°C for >2h → B |
| Storage B | Room-temp peak 30.1°C → B |
| Storage boundary | 8.1°C for 1.9h → PASS (not B) |
| Storage boundary | Room-temp exactly 30.0°C → PASS |
| FSM edge | "4°C" current reading only → storage not complete, no decision |
| Historical boundary | Exactly 1 failure → PASS (not C) |
| Historical lookup | `lookup_device` `SN-FAIL-HIST-2` (3 failures in DB) → C |
| EQA boundary | Deadline exactly 7 days away → WARN → D |
| EQA boundary | Deadline 8 days away → STANDARD → E |
| EQA boundary | Imminent deadline but SUBMITTED → STANDARD → E |
| Precedence | Expired lot + freeze tripped → A (not B) |
| Precedence | Freeze tripped + 2 failures → B (not C) |
| Precedence | 2 failures + EQA WARN → C (not D) |
| Dialogue | All four variables volunteered in one message → E (1 turn) |
| Dialogue | Correction: valid expiry → expired → A |
| Dialogue | Correction: expired → valid → continues to E |

---

## Updating fixtures for future slices

- **Lot number on turn 1:** Every scenario's first message must include a lot number. See `back-end/app/mock_db/fixtures.py` for seeded IDs (`LOT-FRESH-1`, `LOT-EXPIRED-1`, `LOT-OLD-VIAL-1`, etc.).
- **Date-sensitive scenarios:** Scenario D uses an `eqa_deadline_date` that must be within 7 days of today. Update the date in `scenarios.json` before each run, or parameterise it in the runner.
- **Early resolution:** Scenarios A–C resolve in fewer than 4 turns (as soon as the failing variable is confirmed). The runner treats a session as passed once the correct `decision` event arrives, regardless of turn count.
- **New scenarios:** Add entries to `scenarios.json`. The runner will pick them up automatically.
- **New variables:** Extend `expected_variables` in each entry to match new fields added to the backend `DecisionEvent`.

---

## Historical results

| Date | Scope | Model | Pass | Report |
|------|-------|-------|------|--------|
| 2026-06-28 | 5 happy paths | `cohere/north-mini-code:free` | 3/5 (5/5 extra turns) | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-1) |
| 2026-06-28 | 5 happy paths | `google/gemini-2.5-flash-lite` | 2/5 | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-2) |
| 2026-06-29 | 5 happy paths | `google/gemini-3.1-flash-lite` pre-fix | 3/5 | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-3) |
| 2026-06-29 | 5 happy paths | `google/gemini-3.1-flash-lite` post-fix | **5/5** | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-4) |
| 2026-06-29 | 21 edge cases | `google/gemini-3.1-flash-lite` | **21/21** | [slice2_edge_cases.md](results/slice2_edge_cases.md) |
