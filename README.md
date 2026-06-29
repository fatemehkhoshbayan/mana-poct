# MANA POCT — Intelligent QC Assistant

> A full-stack Proof of Concept: autonomous, text-based Conversational QC Assistant for Point-of-Care Testing management.

## Architecture

**The single most important design decision:** the LLM gathers facts; deterministic Python code makes the decision.

- **Backend:** FastAPI (Python 3.10) + async SQLAlchemy 2.0 + PostgreSQL 16 + Alembic
- **LLM gateway:** OpenRouter via the OpenAI-compatible SDK (vendor chosen by `LLM_MODEL` string)
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS
- **Observability:** LangFuse (Cloud free tier by default; self-host optional)
- **Containers:** Docker + Docker Compose (single-command spin-up)

## Project structure

```
mana-poct/
├── docker-compose.yml
├── .env.example
├── Makefile
├── evals/                    end-to-end eval framework
│   ├── scenarios.json        canonical 5-scenario fixture
│   ├── run_eval.py           CLI runner (stdlib only)
│   └── results/              timestamped run reports
├── back-end/                 FastAPI app (uv-managed) — see back-end/README.md
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/              async migrations
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/              routers: health · sessions · hello
│       ├── db/               models · session · base
│       ├── schemas/          domain.py · api.py · llm.py  ← frozen contracts
│       ├── domain/           variables · rules_engine · scenarios  (slice 1)
│       ├── orchestration/    fsm · orchestrator · tools · prompts  (slice 1)
│       ├── llm/              openrouter_provider · fake · factory  (slice 1)
│       ├── observability/    tracer · langfuse_tracer · noop_tracer  (slice 4)
│       ├── events/           publisher · log_publisher · outbox  (slice 5)
│       ├── mock_db/          fixtures · seed · repository  (slice 2)
│       └── tests/            pytest suite — rules engine · FSM · mock DB (49 tests)
└── front-end/                React 19 + TypeScript — see front-end/README.md
    └── src/
        ├── services/         types.ts · client.ts  (mirrors backend contracts)
        ├── hooks/            useChatStream.ts · helper.ts
        ├── state/            chatReducer.ts  (slice 1)
        ├── features/         ChatPanel · ProgressPanel · DecisionCard · Layout
        └── ui/               MessageBubble · Composer · Button
```

## Quick start

```bash
# 1. Copy and fill credentials
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY + LLM_MODEL (or leave blank for FakeProvider)

# 2. Start everything
make up
# or: docker compose up --build

# 3. Open
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
# Health:    http://localhost:8000/api/health
```

> **No credentials needed for Slice 0** — the app boots on `FakeProvider` + `NoopTracer` with no keys.

## API

Interactive Swagger UI at **`http://localhost:8000/docs`** — all endpoints documented with request/response schemas and examples.

### SSE event types (`POST /api/sessions/{id}/messages`)

| `event:`   | `data:`                                                  | Meaning                                     |
| ---------- | -------------------------------------------------------- | ------------------------------------------- |
| `token`    | raw text chunk                                           | Append to the streaming bubble              |
| `state`    | `ExtractionState` + `{current_state, current_objective}` | Drives ProgressPanel                        |
| `decision` | `Decision`                                               | Final resolved action — render DecisionCard |
| `error`    | `{message}`                                              | Recoverable error                           |
| `done`     | `[DONE]`                                                 | End of turn                                 |

## The QC Decision Matrix

| Scenario                     | Condition       | Color     | System Action                 |
| ---------------------------- | --------------- | --------- | ----------------------------- |
| A — Hard Block               | Consumable FAIL | 🔴 RED    | Lockdown Device               |
| B — Environmental Breach     | Storage FAIL    | 🟡 YELLOW | Fail QC Session               |
| C — Suspected Hardware Drift | Historical FAIL | 🔵 BLUE   | Trigger Secondary Bio-Ref Run |
| D — High-Priority Sprint     | EQA = WARN      | 🟢 GREEN  | Pass QC (High Priority)       |
| E — Standard Clearance       | All PASS        | 🟢 GREEN  | Pass QC                       |

Early resolution: once a FAIL makes the outcome certain (e.g. expired lot → A, storage breach → B), the session resolves without collecting remaining variables.

## Manual testing (all five paths)

Start a **new session** for each path. Turn 1 must include a **lot number** — consumable is not marked known without it.

| Path | Turn 1 (consumable) | Key trigger | Resolves |
| ---- | --------------------- | ----------- | -------- |
| **A** | `Lot number LOT-EXPIRED-1, expiry date 2026-01-15, vial opened 4 days ago` | Expired lot | Turn 1 |
| **B** | `Lot number LOT-FRESH-1, expiry 2026-12-31, vial opened 5 days ago` | Turn 2: `9°C for 3 hours` excursion | Turn 2 |
| **C** | `Lot number LOT-FRESH-1, expiry 2026-12-31, vial opened 5 days ago` | Turn 3: `2 consecutive QC failures` | Turn 3 |
| **D** | `Lot number LOT-EQA-D, expiry 2026-12-31, vial opened 5 days ago` | Turn 4: EQA deadline ≤ 7 days, PENDING | Turn 4 |
| **E** | `Lot number LOT-STANDARD, expiry 2026-12-31, vial opened 5 days ago` | All variables pass | Turn 4 |

**"I don't know" fallbacks** (Slice 2): the assistant can call `lookup_lot` / `lookup_device` against seeded mock data. Fixture IDs live in `back-end/app/mock_db/fixtures.py` (e.g. `LOT-EXPIRED-1`, `SN-FAIL-HIST-1`).

## Evals

The `evals/` directory contains a reproducible test harness for all five QC decision scenarios.

```bash
# Run all 5 scenarios against the local stack
python evals/run_eval.py

# Run a subset
python evals/run_eval.py --scenarios A C E
```

See [`evals/README.md`](./evals/README.md) for full usage and historical results.

## Delivery slices

| Slice                       | Status   | Goal                                                          |
| --------------------------- | -------- | ------------------------------------------------------------- |
| 0 — Skeleton & contracts    | ✅ Done  | Docker up, health green, hello-stream works, contracts frozen |
| 1 — end-to-end POC          | ✅ Done  | Real FSM + LLM extraction + rules engine + DecisionCard       |
| 2 — Fallbacks + mock DB     | ✅ Done  | Mock DB seed, lookup_lot/device, early resolution, FSM tests |
| 3 — Robust dialogue         | 🔲       | Out-of-order, corrections, vendor-swap parity                 |
| 4 — Observability           | 🔲       | LangFuse tracing                                              |
| 5 — Polish + tests + events | 🔲       | Outbox, full test suite, README complete                      |

## Development commands

```bash
make up          # docker compose up --build
make down        # docker compose down
make logs        # follow all logs
make test        # pytest (backend)
make fmt         # ruff + prettier
make migrate     # alembic upgrade head
make revision    # alembic autogenerate (msg=<message>)
```

## Credentials

See [§11 of the implementation plan](./virtual-po-mossy-spring.md) for full credential setup instructions.

- **Slice 0**: no keys needed
- **Slice 1+**: `OPENROUTER_API_KEY` + `LLM_MODEL` (tool-calling capable model)
- **Slice 4**: `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` + `LANGFUSE_HOST`
