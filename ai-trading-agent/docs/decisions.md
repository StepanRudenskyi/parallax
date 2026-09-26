# Architectural Decisions Log

> Living document, append-only in spirit — new entries go at the bottom. Each entry
> should capture: what was decided, why, and what alternative was rejected. This
> exists so that, months from now, we don't re-litigate a decision without
> remembering why it was made.

---

### 2026-09-26 — Monorepo over multiple repositories

**Decision:** Single repository (`ai-trading-agent`) containing `agents/`
(Python), `execution/` (Java, later), `web/` (Next.js, later), `data/` (migrations),
and `infra/` (Docker Compose).

**Why:** At evenings-and-weekends pace, cross-repo version syncing (a Python change
breaking a Java contract) creates friction disproportionate to the benefit of
separate repos. A monorepo keeps everything reviewable and buildable together.

---

### 2026-09-26 — Plain PostgreSQL over TimescaleDB

**Decision:** Use vanilla PostgreSQL 16 for all phases unless intraday
(minute/tick-level) data across many instruments becomes a real requirement.

**Why:** At hobby scale (a handful of tickers, daily/hourly bars), TimescaleDB's
hypertables and compression add operational complexity without a measurable
benefit. Adopting it now would be premature optimization for a scale we don't have.

---

### 2026-09-26 — REST first between Python and Java, gRPC deferred

**Decision:** Python↔Java communication starts as plain REST/JSON. gRPC is a
possible later upgrade, not a Phase 3 requirement.

**Why:** REST is simpler to debug and sufficient for the request volume of a
hobby project. Introducing gRPC now adds tooling overhead (proto definitions,
codegen in two languages) before there's a performance problem to justify it.

---

### 2026-09-26 — Supervisor pattern for multi-agent orchestration, implemented as a custom graph

**Decision:** Use LangGraph's supervisor pattern (specialists report to a single
routing/synthesis step) rather than hierarchical or swarm patterns. Implemented
as a hand-written `StateGraph` (fan-out to three specialist nodes, fan-in to a
synthesis node) rather than adopting the `langgraph-supervisor` prebuilt package.

**Why:** Supervisor is the simplest multi-agent topology — routing/synthesis is
a single responsibility, cheaper in tokens than hierarchical structures. The
prebuilt `langgraph-supervisor` package is built around ReAct tool-calling
agents sharing a `messages` state, which doesn't match our specialists (each is
a fixed two-step pipeline: fetch data, call LLM once). A hand-written graph
using our own `ResearchState` TypedDict was more transparent for someone new to
LangGraph, and avoided learning a second abstraction on top of the first.

---

### 2026-09-26 — Docker Compose from day one, even for local-only use

**Decision:** Every service gets a Dockerfile and is orchestrated via Docker
Compose from its first commit, even though nothing is deployed anywhere yet.

**Why:** This keeps the project "deployment-ready" without requiring an actual
deployment decision now. Retrofitting containerization later, after
environment-specific assumptions have crept into the code, is more expensive
than starting with it.

---

### 2026-09-26 — Alembic (Python) owns all schema migrations

**Decision:** All DDL changes go through Alembic migrations in `data/`. The Java
service connects to the same tables but runs with `hibernate.ddl-auto` disabled
— it never creates or alters schema, only reads/writes rows.

**Why:** Two languages independently managing schema changes on a shared database
is a predictable source of migration conflicts. Designating a single owner
removes that entire class of bug before it can happen.

---

### 2026-09-26 — Phased LLM strategy: local-first, cloud when it earns it

**Decision:** Default target is Ollama running locally, at zero marginal cost,
during early development. Paid cloud APIs (Anthropic, etc.) are adopted later,
once the system is stable enough that response quality — not cost — becomes the
binding constraint.

**Why:** Early phases are about validating the graph topology and prompts, not
about response quality. Spending money on cloud APIs before the pipeline itself
is trustworthy is wasted spend.

**Update (same day):** See the next entry — this default was immediately
stress-tested by a hardware limitation.

---

### 2026-09-26 — Pluggable LLM provider factory; temporary move off local Ollama

**Decision:** `agents/llm_provider.py` exposes `get_llm()`, selecting a provider
via the `LLM_PROVIDER` environment variable (`ollama` | `groq` | `google`),
rather than hardcoding `ChatOllama`. Currently defaulting to **Google Gemini**
(`gemini-2.5-flash`, free tier via Google AI Studio) as the active provider,
used by all specialist agents and the supervisor synthesis step.
`get_active_model_label()` returns a `"provider:model"` string persisted
alongside every recommendation/agent_opinion row, so providers can be compared
later without guessing which one produced which row.

**Why:** Local Ollama inference (`qwen3:8b`, then `qwen3:4b`) failed with
out-of-memory errors during model load and later hung at 100% CPU with no
response — the development machine cannot currently run even a 4B model
comfortably on CPU. Two free cloud bridges were evaluated (Groq — fast, LPU
hardware; Google Gemini — reliable native `json_schema` structured output).
Gemini was selected as the active default after successful end-to-end tests on
both the single-agent and multi-agent graphs.

**Important:** This does **not** replace the local-first strategy — it is a
stopgap. Switching back requires only changing `LLM_PROVIDER=ollama` in `.env`,
with no code changes.

---

### 2026-09-26 — Reserved architectural hooks for future crypto support

**Decision:** Even though crypto trading is not implemented until Phase 6+,
three seams are built into the schema and service design now:

1. `instrument.asset_type` distinguishes `EQUITY` / `CRYPTO` from the first
   migration, instead of treating "stock" as an implicit assumption.
2. `price_bar.timeframe` supports sub-daily granularity (`1h`, `1m`) and
   numeric fields use `NUMERIC(20,8)` precision, sufficient for crypto's smaller
   units, not just equity-scale prices.
3. The Java Execution service (Phase 3+) is planned around a Broker Adapter
   interface, with `PAPER_SIM` as the only implementation until a crypto
   testnet adapter is added later.

**Why:** These are cheap to decide now and expensive to retrofit later — none
of them add meaningful complexity to Phases 0–3, but avoiding them would force
a schema migration and interface rewrite when crypto is eventually added.

---

### 2026-09-26 — Considered but not yet adopted: Jev AI, Kronos

**Decision:** Both evaluated as good architectural fits, deliberately deferred:

- **Jev AI** (TypeSafe AI's "System One" decision model) — candidate for cheap,
  fast, non-hallucinating classification/confidence-gating (e.g. a risk gate
  between recommendation and execution). Early access; treat as experimental
  with an LLM-based fallback.
- **Kronos** — open-source foundation model for financial candlestick (K-line)
  forecasting (AAAI 2026). Planned as a second tool (`kronos_forecast()`)
  inside the Quant Agent, running locally via `transformers`/`torch`.

**Why deferred:** Both add a new unknown on top of a system still being
validated. Scheduled for a later iteration of the Quant Agent, once the Java
execution layer (Phase 3) exists and the base pipeline has proven stable.

---

### 2026-09-26 — Nodes return partial state updates only (LangGraph fan-out/fan-in fix)

**Decision:** All specialist and synthesis nodes return only the state keys
they change (e.g. `{"quant_opinion": opinion}`), never a full copy of state
(`{**state, ...}`).

**Why:** The first version of the Phase 2 graph had all three specialist nodes
return `{**state, <their_key>: opinion}`. Because they run in parallel
(fan-out from `START`), all three simultaneously "wrote" the unchanged `ticker`
value in the same superstep, and LangGraph raised
`InvalidUpdateError: At key 'ticker': Can receive only one value per step` —
concurrent writes to the same key require an `Annotated` reducer we hadn't
defined (and don't need, since `ticker` never changes). Returning only the
delta each node owns is the correct general LangGraph pattern, not just a fix.

---

### 2026-09-26 — Persistence added via table reflection, not duplicated schema

**Decision:** `agents/persistence.py` writes to `analysis_run`, `recommendation`,
and `agent_opinion` using SQLAlchemy Core with tables loaded via
`Table(..., autoload_with=engine)` (reflection) rather than redeclaring
`Base`/model classes inside `agents/`.

**Why:** Schema ownership belongs to Alembic in `data/` (see the earlier
decision). If `agents/` also declared its own ORM model classes for these
tables, two independent schema definitions would need to stay in sync by hand.
Reflection means `agents/` always sees whatever `data/`'s migrations actually
created, with zero duplication.

**Related:** `analysis_run`/`recommendation`/`agent_opinion` use `VARCHAR` +
`CHECK` constraints instead of native Postgres `ENUM` types (unlike
`instrument.asset_type`, which does use a native enum). This is deliberate:
these tables will eventually be written by the Java service too (once
`backtest_result` links to `recommendation` in Phase 3), and plain text with a
`CHECK` constraint avoids the extra per-driver configuration that Postgres
native enums require in JDBC.

---

### 2026-09-26 — Containerized the agents service; made DB host configurable per environment

**Decision:** Added `agents/Dockerfile` (python:3.12-slim, installs
`requirements.txt`, runs `uvicorn` on port 8000) and registered an `agents`
service in `infra/docker-compose.yml`, networked alongside `postgres`. Both
`agents/db.py` and `data/db.py` (and Alembic's `env.py`) now read
`POSTGRES_HOST` from the environment (default `localhost`) instead of
hardcoding it.

**Why:** This was a gap against our own "Docker from day one" decision —
`postgres` had a container from the start, but `agents/` did not. Inside the
Docker network, the database is reachable at hostname `postgres` on the
internal port `5432`, not `localhost:5433` (the host-mapped port used for
local, non-containerized development). The compose file's `agents` service
overrides `POSTGRES_HOST`/`POSTGRES_PORT` after loading the rest of `.env` via
`env_file`, so the same `.env` serves both the containerized and the local
`uvicorn --reload` workflow without duplication or manual edits.

**Day-to-day workflow note:** `docker compose up --build` for `agents` is
slower to iterate on than `uvicorn --reload` directly on the host, so the
recommended pattern is: run Postgres in Docker at all times, run `agents/`
directly on the host during active development, and periodically run the full
`docker compose up --build` as a "does this still deploy cleanly" check.

---

*(Add new entries above this line as future phases introduce or revise decisions.)*