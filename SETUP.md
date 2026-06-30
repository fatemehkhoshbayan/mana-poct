# Setup Guide

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- Node.js ≥ 20 (frontend standalone only)
- Python ≥ 3.10 + [uv](https://github.com/astral-sh/uv) (backend standalone only)

---

## Quick start (Docker — recommended)

```bash
# 1. Copy and fill credentials
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY + LLM_MODEL
# Leave blank to boot on FakeProvider (no keys needed for Slice 0)

# 2. Start everything
make up
# or: docker compose up --build

# 3. Open
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
# Health:    http://localhost:8000/api/health
```

> **No credentials needed for Slice 0** — the app boots on `FakeProvider` + `NoopTracer` with no keys.

---

## Standalone development

### Frontend

```bash
cd front-end
npm install
npm run dev
# http://localhost:5173
# Proxies /api → http://localhost:8000 (see vite.config.ts)
```

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Type-check + production build → `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
| `npm run prettier` | Format all source files |
| `npm run check-format` | Check formatting without writing |

### Backend

```bash
cd back-end
uv sync
uv run uvicorn app.main:app --reload
# http://localhost:8000
```

---

## Make targets

```bash
make up          # docker compose up --build
make down        # docker compose down
make logs        # follow all service logs
make test        # pytest (backend, inside container)
make fmt         # ruff + prettier
make migrate     # alembic upgrade head
make revision    # alembic autogenerate  msg=<message>
```

---

## Credentials

| Slice | Keys required |
|-------|--------------|
| 0 | None — `FakeProvider` + `NoopTracer` |
| 1+ | `OPENROUTER_API_KEY` · `LLM_MODEL` (tool-calling capable model) |
| 4 | `LANGFUSE_PUBLIC_KEY` · `LANGFUSE_SECRET_KEY` · `LANGFUSE_HOST` |

Copy `.env.example` and fill in the values for the slices you are running:

```dotenv
# LLM
OPENROUTER_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-3-5-sonnet          # any tool-calling model on OpenRouter

# Observability (Slice 4+)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com       # or your self-hosted URL

# Database (defaults work with Docker Compose)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mana_poct
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/mana_poct
```

---

## Database migrations

```bash
# Apply all pending migrations
make migrate

# Generate a new migration after changing a model
make revision msg="add foo column to bar table"

# Inside the container directly
docker compose exec backend alembic upgrade head
```

---

## Running evals

```bash
# Run all 5 happy-path scenarios against the local stack
python evals/run_eval.py

# Run a subset
python evals/run_eval.py --scenarios A C E
```

See [`evals/README.md`](./evals/README.md) for full usage, boundary thresholds, edge-case inventory, and historical results.
