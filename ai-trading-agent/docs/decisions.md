# Architectural Decisions Log

> Living document, append-only in spirit — new entries go at the bottom. Each entry
> should capture: what was decided, why, and what alternative was rejected. This
> exists so that, months from now, we don't re-litigate a decision without
> remembering why it was made.

---

### 2026-09-26 — Monorepo over multiple repositories

**Decision:** Single repository (`ai-trading-agent`) containing `agents/`
(Python), `execution/` (Java), `web/` (Next.js, later), `data/` (migrations),
and `infra/` (Docker Compose).

**Why:** At evenings-and-weekends pace, cross-repo version syncing (a Python change
breaking a Java contract) creates friction disproportionate to the benefit of
separate repos. A monorepo keeps everything reviewable and buildable together.

---

### 2026-09-26 — Plain PostgreSQL over TimescaleDB

**Decision:** Use vanilla PostgreSQL 16 for all phases unless intraday
(minute/tick-level) data across many instruments becomes a real requirement.

**Why:** At hobby scale, TimescaleDB's hypertables and compression add
operational complexity without a measurable benefit. Premature optimization
for a scale we don't have.

---

### 2026-09-26 — REST first between Python and Java, gRPC deferred

**Decision:** Python↔Java communication starts as plain REST/JSON. gRPC is a
possible later upgrade, not a requirement.

**Why:** REST is simpler to debug and sufficient for the request volume of a
hobby project. Confirmed workable end-to-end in Phase 3 (`agents` calls
`execution`'s `/backtest/{ticker}` synchronously via `requests`).

---

### 2026-09-26 — Supervisor pattern for multi-agent orchestration, implemented as a custom graph

**Decision:** Hand-written LangGraph `StateGraph` (fan-out to three specialist
nodes, fan-in to a synthesis node) instead of the `langgraph-supervisor`
prebuilt package.

**Why:** The prebuilt package targets ReAct tool-calling agents sharing a
`messages` state, which doesn't match our fixed two-step specialist pipelines.
A hand-written graph was more transparent for someone new to LangGraph.

---

### 2026-09-26 — Docker Compose from day one, even for local-only use

**Decision:** Every service gets a Dockerfile and is orchestrated via Docker
Compose from its first commit, even before anything is deployed anywhere.

**Why:** Keeps the project "deployment-ready" without requiring an actual
deployment decision now. By the end of Phase 3, all three backend services
(`postgres`, `agents`, `execution`) run together via one `docker compose up --build`.

---

### 2026-09-26 — Alembic (Python) owns all schema migrations

**Decision:** All DDL changes go through Alembic migrations in `data/`. Both
the Java (`execution`) and Python (`agents`) services connect with schema
mutation disabled on their side (`hibernate.ddl-auto: none` for Java) — they
read and write rows, never structure.

**Why:** Two languages independently managing schema changes on a shared
database is a predictable source of conflicts. A single owner removes that
class of bug. Confirmed working in Phase 3: `execution` writes rows into
`backtest_result` via JPA, but the table itself was created by an Alembic
migration, not by Hibernate.

---

### 2026-09-26 — Phased LLM strategy: local-first, cloud when it earns it (revised same day)

**Decision:** Target is Ollama locally at zero cost; paid cloud APIs adopted
later once quality, not cost, is the binding constraint.

**Update:** Local Ollama inference failed with out-of-memory errors and later
hung at 100% CPU on the development machine. `agents/llm_provider.py` now
exposes `get_llm()` (provider via `LLM_PROVIDER` env var: `ollama` | `groq` |
`google`), currently defaulting to **Google Gemini** (`gemini-2.5-flash`, free
tier). `get_active_model_label()` persists a `"provider:model"` string
alongside every recommendation/agent_opinion row. Switching back to Ollama
requires only an env var change, no code changes. Groq (free, LPU hardware)
remains available as a second bridge option.

---

### 2026-09-26 — Reserved architectural hooks for future crypto support

**Decision:** `instrument.asset_type` (`EQUITY`/`CRYPTO`), sub-daily
`price_bar.timeframe`, `NUMERIC(20,8)` precision, and a planned Broker Adapter
interface in the Java service are all reserved now, ahead of Phase 6+.

**Why:** Cheap to decide now, expensive to retrofit later — a schema
migration and interface rewrite would otherwise be needed when crypto lands.

---

### 2026-09-26 — Considered but not yet adopted: Jev AI, Kronos

**Decision:** Both are good architectural fits (Jev AI as a cheap
classification/confidence-gate; Kronos as a forecasting tool inside the Quant
Agent) but deliberately deferred until the pipeline they'd extend is fully
stable through Phase 3.

---

### 2026-09-26 — Nodes return partial state updates only (LangGraph fan-out/fan-in fix)

**Decision:** All LangGraph nodes return only the state keys they change, never
a full copy of state.

**Why:** Parallel specialist nodes writing an unchanged shared key
(`ticker`) in the same superstep raised `InvalidUpdateError` — concurrent
writes require an `Annotated` reducer. Returning only the owned delta is the
correct general pattern, not a one-off fix.

---

### 2026-09-26 — Persistence added via table reflection, not duplicated schema (agents side)

**Decision:** `agents/persistence.py` writes to `analysis_run`,
`recommendation`, `agent_opinion` using SQLAlchemy Core tables loaded via
`Table(..., autoload_with=engine)`, never redeclaring ORM model classes in
`agents/`. These three tables use `VARCHAR` + `CHECK` constraints instead of
native Postgres `ENUM` types, specifically so the Java service could later
write to related tables without per-driver enum configuration.

---

### 2026-09-26 — Containerized the agents service; made DB host configurable per environment

**Decision:** `agents/Dockerfile` + `docker-compose` service. `POSTGRES_HOST`
is read from the environment (default `localhost`) in both `agents/db.py` and
`data/`'s Alembic `env.py`, overridden to `postgres` inside the Docker network.

**Day-to-day workflow:** Postgres always runs in Docker; `agents`/`execution`
run directly on the host during active development for faster iteration;
`docker compose up --build` is a periodic "does this still deploy cleanly" check.

---

### 2026-09-26 — `backtest_result` requires `instrument_id`, not just an optional `recommendation_id`

**Decision:** Added `instrument_id` (required) to `backtest_result`, in
addition to the originally-specified `recommendation_id` (still nullable).

**Why:** The original schema (from `docs/database-schema.md`) only had
`recommendation_id`, which meant a standalone backtest (not tied to any
recommendation) had no way to identify which instrument it ran against. This
was caught while implementing the first version of the Java backtester, not
during initial schema design — a reminder that schemas designed on paper
before any code exists should be expected to need small corrections once
real usage exposes gaps.

---

### 2026-09-26 — Java writes business data without owning schema; JPA entity uses app-assigned UUIDs

**Decision:** `BacktestResultEntity` (Java/JPA) has no `@GeneratedValue` on its
`@Id` — the UUID is generated in Java code (`UUID.randomUUID()`) before
`save()`, matching how Python generates UUIDs for `analysis_run`/`recommendation`.

**Why:** Consistent ID generation strategy across both languages, and avoids
relying on a Postgres-side default (`gen_random_uuid()`) that Alembic would
need to declare and Java would need to know about after the fact.

---

### 2026-09-26 — Phase 3: real Python→Java link, explicitly scoped as retrospective context, not forward validation

**Decision:** After persisting a recommendation, `agents/main.py` calls
`execution_client.trigger_backtest(ticker, recommendation_id)`, which `POST`s
to the Java service's `/backtest/{ticker}` with the recommendation's UUID.
Java runs the same full-history SMA(20)+RSI(14) strategy as before, but now
stores the given `recommendation_id` on the resulting `backtest_result` row
instead of `NULL`.

**Why scoped this way:** A recommendation made *today* cannot be genuinely
forward-tested — the future price bars it would need don't exist yet. Rather
than fabricate a fake forward-test, this link answers a more honest question:
"how has the underlying strategy performed historically, for context on this
recommendation" — not "was this specific recommendation correct." A true
forward-test would require waiting for future data to accumulate and is
tracked as a possible Phase 5+ addition (e.g. a scheduled job that re-checks
past recommendations against bars that have since arrived).

**Resilience:** `execution_client.py` fails soft — if the Java service is
down or errors, `/analyze` still returns the recommendation, with
`backtest_context` containing an error message instead of blocking the whole
response. A backtest is supporting context, not a hard dependency of analysis.

---

*(Add new entries above this line as future phases introduce or revise decisions.)*