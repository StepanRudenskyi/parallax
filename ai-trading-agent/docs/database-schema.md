# Database Schema

> Living document. This describes the **target** schema. Tables are only created
> when the phase that needs them actually lands — check the "Status" column before
> assuming a table exists.

## Schema Ownership

The Python layer (via Alembic, in `data/`) owns all schema migrations for
business tables, even for tables primarily written by the Java service (e.g.
`backtest_result`). The Java service connects with `hibernate.ddl-auto: none`
— it reads and writes rows, but never alters structure. Confirmed working in
Phase 3: `execution` writes into `backtest_result` via JPA against a table
that Alembic created.

LangGraph-managed tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
`checkpoint_migrations`) would be created automatically by `PostgresSaver.setup()`
if/when a checkpointer is wired in — not yet done as of Phase 3. Currently,
`analysis_run.thread_id` is populated with a request-scoped UUID generated in
`agents/main.py`, not an actual LangGraph checkpoint thread.

## Tables

### `instrument` — Status: ✅ Implemented (Phase 0)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `ticker` | VARCHAR(20) | |
| `asset_type` | ENUM(`EQUITY`, `CRYPTO`) | crypto hook from day one |
| `source` | VARCHAR(50) | e.g. `yfinance` |
| `currency` | VARCHAR(10) | default `USD` |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

Unique constraint: (`ticker`, `source`).

### `price_bar` — Status: ✅ Implemented (Phase 0)

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, PK | |
| `instrument_id` | UUID, FK → `instrument.id` | |
| `ts` | TIMESTAMPTZ | |
| `timeframe` | ENUM(`1d`, `1h`, `1m`) | sub-daily reserved for crypto |
| `open`, `high`, `low`, `close` | NUMERIC(20,8) | crypto-scale precision |
| `volume` | NUMERIC(24,8) | nullable |
| `source` | VARCHAR(50) | |

Unique constraint: (`instrument_id`, `ts`, `timeframe`).

### `news_item` — Status: Not implemented (sentiment agent uses live `yfinance` calls, no persistence yet)

Originally planned for Phase 2, but the sentiment agent currently fetches
headlines live on each request rather than persisting them. Revisit if/when
caching or historical sentiment analysis becomes necessary.

### `analysis_run` — Status: ✅ Implemented (Phase 2)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `instrument_id` | FK | |
| `thread_id` | VARCHAR | currently a request-scoped UUID, not a real LangGraph checkpoint thread (no checkpointer wired in yet) |
| `status` | VARCHAR + CHECK(`RUNNING`, `COMPLETED`, `FAILED`) | |
| `triggered_by` | VARCHAR + CHECK(`MANUAL`, `SCHEDULED`, `API`) | |
| `requested_at`, `completed_at` | TIMESTAMPTZ | |

### `recommendation` — Status: ✅ Implemented (Phase 2)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | 1:1 with `analysis_run` |
| `analysis_run_id` | FK, unique | |
| `final_verdict` | VARCHAR + CHECK(`BUY`, `HOLD`, `SELL`) | |
| `confidence` | NUMERIC(4,3) | 0–1 |
| `summary_text` | TEXT | |
| `model_used` | VARCHAR | `"provider:model"`, e.g. `google:gemini-2.5-flash` |
| `created_at` | TIMESTAMPTZ | |

### `agent_opinion` — Status: ✅ Implemented (Phase 2)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `analysis_run_id` | FK | |
| `agent_name` | VARCHAR + CHECK(`SENTIMENT`, `QUANT`, `FUNDAMENTAL`) | |
| `verdict` | VARCHAR + CHECK(`BUY`, `HOLD`, `SELL`) | |
| `confidence` | NUMERIC(4,3) | |
| `reasoning_text` | TEXT | |
| `raw_output_json` | JSONB | full structured LLM output, for debugging without migrations |
| `model_used`, `latency_ms` | VARCHAR, INTEGER | `latency_ms` reserved, not yet populated |
| `created_at` | TIMESTAMPTZ | |

**Note:** `agent_opinion`/`recommendation`/`analysis_run` deliberately use
`VARCHAR` + `CHECK` instead of native Postgres `ENUM` (unlike `instrument`/
`price_bar`), so a future writer in another language (e.g. Java, if it ever
needs to write here) doesn't need per-driver enum configuration.

### `backtest_result` — Status: ✅ Implemented (Phase 3)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | app-assigned (Java generates `UUID.randomUUID()`, not DB default) |
| `instrument_id` | UUID, FK → `instrument.id`, **NOT NULL** | added during implementation — see `docs/decisions.md` |
| `recommendation_id` | UUID, FK → `recommendation.id`, nullable | set when triggered from a Python recommendation; `NULL` for standalone runs |
| `strategy_name` | VARCHAR(200) | |
| `start_date`, `end_date` | DATE | span of the price data actually used |
| `bar_count` | INTEGER | |
| `num_trades` | INTEGER | |
| `position_count` | INTEGER | completed round-trip positions |
| `pnl_percent` | NUMERIC(10,6) | `(net_return - 1) * 100` |
| `max_drawdown` | NUMERIC(10,6) | fraction, e.g. `0.096` = 9.6% |
| `sharpe_ratio` | NUMERIC(10,6) | column reserved, not yet computed/populated |
