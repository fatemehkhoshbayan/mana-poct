# evals/

End-to-end evaluation framework for the MANA POCT QC Assistant.

```
evals/
├── README.md              ← this file
├── scenarios.json         ← canonical 5-scenario fixture
├── run_eval.py            ← CLI runner (no extra deps, stdlib only)
└── results/
    └── slice1_model_comparison.md   ← Slice 1 evaluation report
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
    "Lot expiry ...",
    "Refrigerated at 4C ...",
    ...
  ]
}
```

### Variable status values

| Key | PASS | FAIL | WARN |
|-----|------|------|------|
| `consumable_status` | lot valid + open vial within window | lot expired OR vial > max_days | — |
| `storage_condition` | no excursion, freeze-ok | excursion > threshold OR freeze tripped | — |
| `historical_error_flag` | < 2 consecutive failures | ≥ 2 consecutive failures | — |
| `eqa_status` | no active cycle | — | active + deadline ≤ 7 days + PENDING |

---

## Updating fixtures for future slices

- **Date-sensitive scenarios:** Scenario D uses an `eqa_deadline_date` that must be within 7 days of today. Update the date in `scenarios.json` before each run, or parameterise it in the runner.
- **New scenarios:** Add entries to `scenarios.json`. The runner will pick them up automatically.
- **New variables:** Extend `expected_variables` in each entry to match new fields added to the backend `DecisionEvent`.

---

## Historical results

| Date | Model | Pass | Report |
|------|-------|------|--------|
| 2026-06-28 | `cohere/north-mini-code:free` | 3/5 (5/5 extra turns) | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-1) |
| 2026-06-28 | `google/gemini-2.5-flash-lite` | 2/5 | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-2) |
| 2026-06-29 | `google/gemini-3.1-flash-lite` pre-fix | 3/5 | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-3) |
| 2026-06-29 | `google/gemini-3.1-flash-lite` post-fix | **5/5** | [slice1_model_comparison.md](results/slice1_model_comparison.md#run-4) |
