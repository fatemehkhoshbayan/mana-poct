# MANA POCT — Back End

FastAPI service implementing the QC assistant: SSE streaming, LLM orchestration, deterministic rules engine, and async PostgreSQL persistence.

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI 0.138+ (async, Pydantic v2) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (auto-run at startup via lifespan) |
| LLM gateway | OpenRouter via `openai` SDK (model set by `LLM_MODEL` env var) |
| Streaming | `sse-starlette` — Server-Sent Events |
| Dependency mgmt | `uv` |
| Linting / formatting | `ruff` |
| Testing | `pytest` + `pytest-asyncio` |

## Project layout

```
back-end/
├── Dockerfile
├── pyproject.toml
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_tables.py
└── app/
    ├── main.py              FastAPI app factory, lifespan, CORS, router wiring
    ├── config.py            Pydantic Settings (env vars)
    │
    ├── api/
    │   ├── health.py        GET /api/health
    │   ├── hello.py         GET /api/hello  (slice 0 smoke test)
    │   └── sessions.py      POST /api/sessions · POST /api/sessions/{id}/messages · GET /api/sessions/{id}
    │
    ├── schemas/             Frozen cross-layer contracts (do not change without updating front-end types)
    │   ├── domain.py        ExtractionState, ConsumableInput, StorageInput, HistoricalInput, EqaInput, Decision
    │   ├── api.py           CreateSessionRequest/Response, MessageRequest, SessionDetail, SSE event payloads
    │   └── llm.py           LlmMessage, ToolSpec, StreamEvent (internal LLM adapter types)
    │
    ├── domain/              Pure, deterministic business logic — no I/O, no LLM
    │   ├── variables.py     derive_consumable · derive_storage · derive_historical · derive_eqa
    │   ├── rules_engine.py  resolve(extraction) → Decision  (precedence chain A→B→C→D→E)
    │   └── scenarios.py     SCENARIO_TABLE — maps Scenario enum to metadata
    │
    ├── orchestration/       LLM dialogue management
    │   ├── fsm.py           mark_known · next_objective · can_resolve_early  (pure FSM)
    │   ├── orchestrator.py  handle_turn() → AsyncGenerator[OrchestratorEvent]
    │   ├── tools.py         record_* + lookup_lot/device ToolSpecs + execute_tool()
    │   └── prompts.py       system prompt preamble + per-objective instructions
    │
    ├── llm/                 Vendor-agnostic LLM adapter
    │   ├── base.py          LLMProvider ABC
    │   ├── translate.py     normalised → OpenAI wire format
    │   ├── openrouter_provider.py  streaming tool-call accumulation + thinking-token filter
    │   ├── fake.py          FakeProvider for local testing without a key
    │   └── factory.py       get_provider() → OpenRouterProvider | FakeProvider
    │
    ├── db/
    │   ├── models.py        SQLAlchemy ORM models (7 tables)
    │   ├── session.py       async_sessionmaker, get_db dependency
    │   └── base.py          declarative Base
    │
    ├── observability/       LangFuse tracer (slice 4, currently noop)
    ├── events/              Outbox publisher (slice 5, currently stub)
    ├── mock_db/             Seeded lot/device fixtures + in-memory repository
    │   ├── fixtures.py      Static rows covering scenarios A–E
    │   ├── repository.py    Sync lookup index (used mid-turn by tool executors)
    │   └── seed.py          Idempotent upsert on app startup
    └── tests/
        ├── test_rules_engine.py   22 truth-table tests for the rules engine
        ├── test_fsm.py            mark_known boundaries + early-resolution chain
        └── test_mock_db.py        lookup_lot/device executors + scenario triggers
```

## Environment variables

Copy `../.env.example` to `../.env` and fill in values.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pass@host/db` |
| `OPENROUTER_API_KEY` | No | — | If blank, `FakeProvider` is used |
| `LLM_MODEL` | No | `google/gemini-3.1-flash-lite` | Any OpenRouter model with tool-calling |
| `LOG_LEVEL` | No | `INFO` | Python root logger level |
| `LANGFUSE_PUBLIC_KEY` | No | — | Slice 4 observability |
| `LANGFUSE_SECRET_KEY` | No | — | Slice 4 observability |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Slice 4 observability |

## Running locally

The simplest way is through Docker Compose from the repo root:

```bash
make up      # builds images, starts postgres + backend + frontend
make logs    # follow all container logs
```

To run the backend directly (requires a running Postgres):

```bash
cd back-end
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness check — `{"status": "ok"}` |
| `POST` | `/api/sessions` | Create a new QC session |
| `POST` | `/api/sessions/{id}/messages` | Stream one dialogue turn (SSE); **409** if session already resolved |
| `GET` | `/api/sessions/{id}` | Full session state snapshot |

Full interactive docs at **`http://localhost:8000/docs`**.

### SSE event types

| `event:` | `data:` payload | Purpose |
|----------|----------------|---------|
| `token` | raw text chunk | Append to streaming bubble |
| `state` | `ExtractionState` + `current_objective` + `variable_statuses` | Drive ProgressPanel |
| `decision` | `Decision` | Final resolved action — render DecisionCard |
| `error` | `{"message": "..."}` | Recoverable error |
| `done` | `[DONE]` | End of turn |

### Session lifecycle

- A session starts as `status=active` and progresses through the FSM until a `Decision` is emitted.
- On decision, `status` is set to `resolved` and `fsm_state` to `RESOLVED`.
- Further `POST /api/sessions/{id}/messages` calls return **HTTP 409** with detail *"Session is already resolved. Start a new session for the next device."*
- Each device / QC check should use a new session via `POST /api/sessions`.

## Running tests

```bash
cd back-end
uv run pytest
```

49 tests total: rules-engine truth table, FSM `mark_known` / `can_resolve_early`, and mock DB lookup executors.

## Mock DB & fallback tools

On startup, `seed_mock_db()` upserts fixture rows into `mock_lots` and `mock_devices`. Tool executors read from an in-memory index for zero-latency lookups mid-turn.

| Tool | When used | Example fixture |
| ---- | --------- | --------------- |
| `lookup_lot` | Operator provides lot number but not dates | `LOT-EXPIRED-1` → expired lot (Scenario A) |
| `lookup_device` | Operator provides device serial | `SN-FAIL-HIST-1` → 2 consecutive failures (Scenario C) |

Placeholder values (`"unknown"`, `"I don't know"`, etc.) are rejected — the assistant must ask a follow-up question instead of calling lookup with a placeholder.

### FSM collection rules

| Variable | Marked known when |
| -------- | ----------------- |
| Consumable | `lot_number` **and** `lot_expiry_date` are set |
| Storage | Freeze-indicator answered, **or** excursion data alone proves FAIL |
| Historical | `consecutive_qc_failures_30d` is set |
| EQA | `has_active_cycle` is set (False = STANDARD; True also needs deadline + status) |

`can_resolve_early()` mirrors the §2.2 precedence chain: consumable FAIL → A; storage FAIL → B; historical FAIL → C. The orchestrator resolves as soon as `all_known()` or `can_resolve_early()` is true.

The rules engine only includes **collected** variables in the decision payload (no default PASS/STANDARD for fields not yet gathered).

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Key design decisions

- **LLM gathers, rules decide.** The LLM's only job is to extract structured facts via tool calls. All QC decisions are made by `rules_engine.resolve()` — pure Python, fully testable, no LLM involved.
- **Variable statuses are computed server-side.** `sessions.py` calls `derive_*` functions before emitting each `state` event so the frontend never re-derives business logic.
- **`freeze_indicator_tripped` is mandatory** unless excursion data alone proves storage FAIL. The `record_storage` tool schema and `ASK_STORAGE` prompt enforce this to prevent silent skips (see `evals/results/slice1_model_comparison.md`).
- **`lot_number` is required for consumable.** Expiry date alone does not mark consumable known — this is the audit identifier and gates early resolution.
- **`FakeProvider`** allows the full UI to work in offline/CI environments with no API key.
