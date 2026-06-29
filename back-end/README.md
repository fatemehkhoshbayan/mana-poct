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
    │   ├── fsm.py           mark_known · next_objective  (pure FSM transitions)
    │   ├── orchestrator.py  run_turn() → AsyncGenerator[OrchestratorEvent]
    │   ├── tools.py         record_* ToolSpec definitions + execute_tool()
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
    ├── mock_db/             Mock lot/device data (slice 2, currently stub)
    └── tests/
        └── test_rules_engine.py   22 truth-table tests for the rules engine
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
| `POST` | `/api/sessions/{id}/messages` | Stream one dialogue turn (SSE) |
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

## Running tests

```bash
cd back-end
uv run pytest
```

All 22 rules-engine tests cover the full truth table (scenarios A–E), boundary conditions, and precedence.

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Key design decisions

- **LLM gathers, rules decide.** The LLM's only job is to extract structured facts via tool calls. All QC decisions are made by `rules_engine.resolve()` — pure Python, fully testable, no LLM involved.
- **Variable statuses are computed server-side.** `sessions.py` calls `derive_*` functions before emitting each `state` event so the frontend never re-derives business logic.
- **`freeze_indicator_tripped` is mandatory.** The `record_storage` tool schema and the `ASK_STORAGE` prompt both enforce this field to prevent the LLM from silently skipping it, which was the root cause of several eval failures (see `evals/results/slice1_model_comparison.md`).
- **`FakeProvider`** allows the full UI to work in offline/CI environments with no API key.
