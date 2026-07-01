# Contributing

Thanks for contributing to MANA POCT. This is a small full-stack POC — the goal is to keep changes simple, tested, and consistent with the existing architecture.

## Getting set up

See [SETUP.md](./SETUP.md) for full installation instructions. The short version:

```bash
cp .env.example .env   # add OPENROUTER_API_KEY + LLM_MODEL (leave blank for FakeProvider)
make up                 # docker compose up --build
```

## Project structure

Read the root [README.md](./README.md) for the high-level architecture, and [back-end/README.md](./back-end/README.md) / [front-end/README.md](./front-end/README.md) for layer-by-layer detail before making changes.

## Making changes

- **The rules engine is the source of truth for QC decisions.** The LLM only extracts structured facts via tool calls; never encode decision logic in a prompt. See `back-end/app/domain/rules_engine.py`.
- **`back-end/app/schemas/` are frozen cross-layer contracts.** If you change a field there, update `front-end/src/services/types.ts` to match in the same change.
- **Prefer additive, backward-compatible changes.** Avoid renaming existing API fields, SSE event types, or env var names without a clear migration path — other slices/consumers may depend on them.
- Keep the vendor-agnostic adapter pattern (`LLMProvider`, `Tracer`, `EventPublisher`) when adding new integrations — implement the ABC and wire it into the relevant `factory.py`, rather than branching on vendor inside call sites.

## Running tests

```bash
make test                       # backend pytest, inside the container
# or, running locally:
cd back-end && uv run pytest
```

All new backend logic (rules engine, FSM, orchestration, events) should have accompanying tests under `back-end/app/tests/`.

## Linting and formatting

```bash
make fmt                        # ruff (backend) + prettier (frontend)
```

Or individually:

```bash
cd back-end && uv run ruff check . && uv run ruff format .
cd front-end && npm run lint && npm run prettier
```

## Database migrations

If you change `back-end/app/db/models.py`, generate a migration:

```bash
make revision msg="add foo column to bar table"
make migrate
```

Keep a single linear migration history (no branching heads) unless there's a good reason otherwise.

## Pull requests

- Keep PRs focused on one slice/change at a time.
- Update the relevant `README.md` if you change project structure, endpoints, or environment variables.
- Make sure `make test` and `make fmt` pass before requesting review.
