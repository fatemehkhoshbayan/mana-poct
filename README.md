# MANA POCT — Intelligent QC Assistant

> A full-stack Proof of Concept: autonomous, text-based Conversational QC Assistant for Point-of-Care Testing management.

## Architecture

**The single most important design decision:** the LLM gathers facts; deterministic Python code makes the decision.

- **Backend:** FastAPI (Python 3.10) + async SQLAlchemy 2.0 + PostgreSQL 16 + Alembic
- **LLM gateway:** OpenRouter via the OpenAI-compatible SDK (vendor chosen by `LLM_MODEL` string)
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS v4 — Material Design 3-inspired token system, light/dark mode, SSE streaming
- **Observability:** LangFuse (Cloud free tier by default; self-host optional)
- **Containers:** Docker + Docker Compose (single-command spin-up)

## Project structure

```
mana-poct/
├── docker-compose.yml
├── .env.example
├── Makefile
├── SETUP.md                  installation, credentials, make targets
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
│       ├── observability/    Tracer (abstract) · LangfuseTracer · NoopTracer  (slice 4)
│       ├── events/           EventPublisher · LogPublisher · NtfyPublisher · KafkaPublisher · outbox  (slice 5/6)
│       ├── mock_db/          fixtures · seed · repository  (slice 2)
│       └── tests/            pytest suite — rules engine · FSM · mock DB (49 tests)
└── front-end/                React 19 + TypeScript — see front-end/README.md
    └── src/
        ├── context/          ThemeContext · ThemeProvider · helper (light/dark mode)
        ├── layout/           Layout · Header · Footer (h-screen flex chain)
        ├── pages/            ChatPanelPage (owns chatReducer state)
        ├── features/
        │   └── chat-panel-page/
        │       ├── ChatPanel.tsx      message list + Composer + streaming
        │       ├── ProgressPanel.tsx  horizontal 4-pill QC variable strip
        │       ├── DecisionCard.tsx   colour-coded final decision card
        │       └── constants.ts       COLOR_STYLES · VAR_STATUS_STYLES maps
        ├── services/         types.ts · client.ts  (mirrors backend contracts)
        ├── hooks/            useChatStream.ts · useTheme.ts · helper.ts
        ├── state/            chatReducer.ts  (SESSION_CREATED → STREAM_DONE)
        ├── lib/              cn.ts (clsx + extended tailwind-merge)
        └── ui/               Button · IconButton · Chip · Composer
                              MessageBubble · TypingIndicator
```

## Quick start

```bash
cp .env.example .env   # add OPENROUTER_API_KEY + LLM_MODEL (leave blank for FakeProvider)
make up                # docker compose up --build
# Frontend: http://localhost:5173  |  API docs: http://localhost:8000/docs
```

> Full installation steps, standalone dev servers, Make targets, credentials, and migration commands are in **[SETUP.md](./SETUP.md)**.

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

Sending a message to a **resolved** session returns **HTTP 409** — start a new session via `POST /api/sessions` for the next device.

## Chat UI

The frontend is a full-viewport, frosted-glass chat interface styled with a linear gradient background (light/dark mode switchable via the header toggle).

**Page layout (top → bottom):**

1. **Header** — app name + theme toggle
2. **QC Variables strip** — four horizontal pills (Consumable · Storage · Historical · EQA), each showing a `PENDING / PASS / WARN / FAIL` chip; the active FSM state is highlighted
3. **Chat panel** — frosted-glass scrollable message list pinned above the Composer input
4. **Footer** — copyright strip

| State                   | What the user sees                                                                                                     |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Waiting for first token | Animated three-dot typing indicator                                                                                    |
| Streaming               | Assistant bubble with a blinking cursor; QC variable pills update live                                                 |
| Turn complete           | Composer auto-refocuses so the user can type the next answer immediately                                               |
| Decision reached        | Colour-coded `DecisionCard` (RED / YELLOW / BLUE / GREEN) with variables grid, directives, and collapsible raw payload |
| Session locked          | Composer disabled; **New QC Check** button appears                                                                     |
| Next device             | Click **New QC Check** → fresh session, cleared chat and progress strip (no page reload)                               |

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

| Path  | Turn 1 (consumable)                                                        | Key trigger                            | Resolves |
| ----- | -------------------------------------------------------------------------- | -------------------------------------- | -------- |
| **A** | `Lot number LOT-EXPIRED-1, expiry date 2026-01-15, vial opened 4 days ago` | Expired lot                            | Turn 1   |
| **B** | `Lot number LOT-FRESH-1, expiry 2026-12-31, vial opened 5 days ago`        | Turn 2: `9°C for 3 hours` excursion    | Turn 2   |
| **C** | `Lot number LOT-FRESH-1, expiry 2026-12-31, vial opened 5 days ago`        | Turn 3: `2 consecutive QC failures`    | Turn 3   |
| **D** | `Lot number LOT-EQA-D, expiry 2026-12-31, vial opened 5 days ago`          | Turn 4: EQA deadline ≤ 7 days, PENDING | Turn 4   |
| **E** | `Lot number LOT-STANDARD, expiry 2026-12-31, vial opened 5 days ago`       | All variables pass                     | Turn 4   |

**"I don't know" fallbacks** (Slice 2): the assistant can call `lookup_lot` / `lookup_device` against seeded mock data. Fixture IDs live in `back-end/app/mock_db/fixtures.py` (e.g. `LOT-EXPIRED-1`, `SN-FAIL-HIST-1`).

After a decision, use **New QC Check** in the UI (or `POST /api/sessions`) to start a fresh session for another device. Messages to a resolved session are rejected with HTTP 409.

## Evals

The `evals/` directory contains a reproducible test harness for all five QC decision scenarios (happy paths) plus documented edge-case coverage.

```bash
# Run all 5 happy-path scenarios against the local stack
python evals/run_eval.py

# Run a subset
python evals/run_eval.py --scenarios A C E
```

See [`evals/README.md`](./evals/README.md) for full usage, boundary thresholds, edge-case inventory, and historical results (including the 21/21 edge-case live run).

## Observability

Every dialogue turn is traced through a vendor-agnostic `Tracer` interface (`back-end/app/observability/`), mirroring the LLM provider pattern: `NoopTracer` by default, `LangfuseTracer` automatically selected once `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` are set in `.env`.

Per turn, the trace tree is:

```
qc_turn (span)                     ← one per handle_turn() call, tagged with session_id/tenant_id
├── llm_stream:<objective> (generation)   ← one per LLM stream call, captures model/tokens/output
└── tool:<name> (span)                    ← one per tool execution (record_*/lookup_*)
```

No credentials → the app boots on `NoopTracer` with zero overhead; nothing is sent anywhere. With credentials set, open the LangFuse dashboard (`LANGFUSE_HOST`, default `https://cloud.langfuse.com`) to inspect full traces, token usage, and latency per turn.

## Event-driven Hard Block dispatch

When a device resolves to **Scenario A (Hard Block)**, the backend stages a row in the `events` table **in the same DB transaction** as the `qc_decisions` row — a transactional **outbox**, so the event can never be lost or double-fired relative to the decision. A background relay (`app/events/outbox.py`, started in the FastAPI lifespan) polls every `EVENT_RELAY_INTERVAL_SECONDS` (default 3s), hands unpublished rows to whichever `EventPublisher` sinks are configured, and only marks a row published once every sink succeeds — a failed sink is retried on the next pass.

| Sink             | Always on?                           | What it does                                                                                                                                                                                                                                                                         |
| ---------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `LogPublisher`   | ✅ always                            | Structured log line — the durable fallback/audit trail                                                                                                                                                                                                                               |
| `NtfyPublisher`  | opt-in via `NTFY_TOPIC`              | Posts a real push notification to [ntfy.sh](https://ntfy.sh) — **free, no signup, no app required.** Open `https://ntfy.sh/<your topic>` in any browser and watch the Hard Block alert arrive live.                                                                                  |
| `KafkaPublisher` | opt-in via `KAFKA_BOOTSTRAP_SERVERS` | Publishes to a real Kafka-compatible event bus (topic `poct.device.hardblock`, keyed by device serial) — the Slice 6 stretch goal. `docker compose --profile kafka up` (or `make kafka-up`) runs a free, single-node, KRaft-mode `apache/kafka` container — no ZooKeeper, no signup. |

Set any subset of `NTFY_TOPIC` / `KAFKA_BOOTSTRAP_SERVERS` in `.env` — sinks fan out via `CompositePublisher`; with neither set, only the log line fires.

**Live demo (zero extra setup beyond a browser tab):**

1. Pick a unique topic, e.g. `mana-poct-hardblock-<yourname>`, and set `NTFY_TOPIC` in `.env`.
2. Open `https://ntfy.sh/<that topic>` in a browser tab — no login, no install.
3. Run the **Scenario A** path from the manual testing table below.
4. The push notification appears in that tab within ~`EVENT_RELAY_INTERVAL_SECONDS`.

## Delivery slices

| Slice                       | Status  | Goal                                                                                                         |
| --------------------------- | ------- | ------------------------------------------------------------------------------------------------------------ |
| 0 — Skeleton & contracts    | ✅ Done | Docker up, health green, hello-stream works, contracts frozen                                                |
| 1 — end-to-end POC          | ✅ Done | Real FSM + LLM extraction + rules engine + DecisionCard                                                      |
| 2 — Fallbacks + mock DB     | ✅ Done | Mock DB seed, lookup_lot/device, early resolution, FSM tests                                                 |
| 3 — Robust dialogue         | ✅ Done | Out-of-order, corrections, mark_known re-derive, 16 new tests                                                |
| 3b — UI polish              | ✅ Done | Typing indicator, auto-focus, new session after resolution                                                   |
| 3c — UI redesign            | ✅ Done | Design system (Tailwind v4 tokens), frosted-glass layout, DecisionCard colour-coding, layout stability fixes |
| 4 — Observability           | ✅ Done | LangFuse tracing (turn/generation/tool spans), token usage capture                                           |
| 5 — Polish + tests + events | ✅ Done | Transactional outbox + background relay; LogPublisher + ntfy.sh push notification                            |
| 6 — (Stretch) Real Kafka    | ✅ Done | `KafkaPublisher` (aiokafka) + free single-node KRaft Kafka under `--profile kafka`                           |
