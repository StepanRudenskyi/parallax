# Database Schema

## 1. Ownership Model

PostgreSQL is shared by two services written in different languages (Python, Java), which creates a risk of both attempting to own the schema simultaneously. To avoid this class of bug, ownership is split explicitly:

- **The Python layer (`data/` module, Alembic) owns all schema migrations.** Tables are created and altered exclusively through Alembic revisions, generated from SQLAlchemy models defined in `data/models.py`.
- **The Java Execution service is schema read-only.** It connects via JDBC/JPA to existing tables but has Hibernate's `ddl-auto` disabled (`none`). It never creates or alters tables.
- **LangGraph-managed tables are not designed manually.** When `PostgresSaver.setup()` is called once from the Python layer, LangGraph automatically creates and owns `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, and `checkpoint_migrations`. These are treated as an opaque subsystem, not part of the application's own schema.

## 2. Business Entities

### 2.1 `instrument`

Reference table for tradeable instruments, shared across equities and (future) crypto.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4()` | |
| `ticker` | VARCHAR(20) | NOT NULL | e.g. `AAPL`, later `BTC-USD` |
| `asset_type` | ENUM(`EQUITY`, `CRYPTO`) | NOT NULL, default `EQUITY` | Crypto extension hook (see `architecture.md` §9) |
| `source` | VARCHAR(50) | NOT NULL | Data provider identifier, e.g. `yfinance`, later `binance` |
| `currency` | VARCHAR(10) | NOT NULL, default `USD` | |
| `is_active` | BOOLEAN | NOT NULL, default `TRUE` | |
| `created_at` | TIMESTAMPTZ | server default `now()` | |

Unique constraint: `(ticker, source)` — the same ticker can exist from multiple sources without collision.

**Status: implemented (Phase 0).**

### 2.2 `price_bar`

Historical and (later) streaming OHLCV bars.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BIGSERIAL | PK | Expected to be the largest table by row count |
| `instrument_id` | UUID | FK → `instrument.id`, NOT NULL | |
| `ts` | TIMESTAMPTZ | NOT NULL | Bar timestamp |
| `timeframe` | ENUM(`1d`, `1h`, `1m`) | NOT NULL, default `1d` | `1m` reserved for future crypto intraday data |
| `open`, `high`, `low`, `close` | NUMERIC(20,8) | NOT NULL | Higher precision than typical equity needs, chosen upfront to also fit crypto price granularity without a future migration |
| `volume` | NUMERIC(24,8) | NULLABLE | |
| `source` | VARCHAR(50) | NOT NULL | |

Unique constraint: `(instrument_id, ts, timeframe)` — prevents duplicate rows on repeated data imports; enables idempotent seed/ingestion scripts via `INSERT ... ON CONFLICT DO NOTHING`.

Recommended additional index: `(ts)` alone, for cross-instrument range queries (e.g. "latest N bars across all instruments").

**Status: implemented (Phase 0).**

### 2.3 `news_item` (planned — Phase 2)

Raw input for the sentiment agent.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | |
| `instrument_id` | UUID | FK, NULLABLE | Nullable because a news item may relate to zero, one, or multiple instruments; a `news_instrument` join table can be introduced later if many-to-many becomes necessary |
| `published_at` | TIMESTAMPTZ | NOT NULL | |
| `fetched_at` | TIMESTAMPTZ | server default `now()` | |
| `headline` | TEXT | NOT NULL | |
| `raw_text` | TEXT | NULLABLE | |
| `source_url` | VARCHAR(500) | NULLABLE | |

**Status: planned, not yet migrated.**

### 2.4 `analysis_run` (planned — Phase 1-2)

Metadata for a single invocation of the LangGraph graph. Deliberately separated from `recommendation` — this row represents "an execution happened," independent of whether it produced a usable result.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `instrument_id` | UUID | FK, NOT NULL | |
| `thread_id` | VARCHAR | NOT NULL | Logical (non-FK) reference into LangGraph's `checkpoints` table; enables correlating a business record with the full graph execution trace for debugging |
| `status` | ENUM(`RUNNING`, `COMPLETED`, `FAILED`) | NOT NULL | |
| `triggered_by` | ENUM(`MANUAL`, `SCHEDULED`, `API`) | NOT NULL | Hook for future scheduled/automated analysis runs |
| `requested_at`, `completed_at` | TIMESTAMPTZ | | |

**Status: planned, not yet migrated.**

### 2.5 `recommendation` (planned — Phase 1-2)

The supervisor's final synthesized verdict. One-to-one with `analysis_run`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `analysis_run_id` | UUID | FK, UNIQUE, NOT NULL | Enforces 1:1 with `analysis_run` |
| `final_verdict` | ENUM(`BUY`, `HOLD`, `SELL`) | NOT NULL | |
| `confidence` | NUMERIC(4,3) | NOT NULL | Range 0–1 |
| `summary_text` | TEXT | NOT NULL | |
| `model_used` | VARCHAR(100) | NOT NULL | Which LLM/provider produced the synthesis — used for later cost/quality comparison between Ollama and cloud providers |
| `created_at` | TIMESTAMPTZ | server default `now()` | |

**Status: planned, not yet migrated.**

### 2.6 `agent_opinion` (planned — Phase 2)

Individual specialist opinion within an `analysis_run`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `analysis_run_id` | UUID | FK, NOT NULL | |
| `agent_name` | ENUM(`SENTIMENT`, `QUANT`, `FUNDAMENTAL`) | NOT NULL | Extensible — new specialist types can be added by extending the enum |
| `verdict` | ENUM(`BUY`, `HOLD`, `SELL`, `NEUTRAL`) | NOT NULL | |
| `confidence` | NUMERIC(4,3) | NOT NULL | |
| `reasoning_text` | TEXT | NOT NULL | |
| `raw_output_json` | JSONB | NOT NULL | Stores the raw structured LLM output alongside the parsed columns; tolerates minor changes in LLM output shape without requiring a migration |
| `model_used` | VARCHAR(100) | NOT NULL | |
| `latency_ms` | INTEGER | NULLABLE | Enables performance/cost comparison across Ollama, Jev AI, and cloud LLM calls |
| `created_at` | TIMESTAMPTZ | server default `now()` | |

**Status: planned, not yet migrated.**

### 2.7 `backtest_result` (planned — Phase 3)

Result of a ta4j backtest run against a recommendation or an independent strategy test.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | |
| `recommendation_id` | UUID | FK, NULLABLE | Nullable — strategies can be backtested independently of a specific live recommendation |
| `strategy_name` | VARCHAR(100) | NOT NULL | ta4j's `BacktestExecutor` supports comparing multiple strategies over one series |
| `start_date`, `end_date` | DATE | NOT NULL | |
| `pnl_absolute`, `pnl_percent` | NUMERIC | NOT NULL | |
| `sharpe_ratio` | NUMERIC | NULLABLE | |
| `max_drawdown` | NUMERIC | NULLABLE | |
| `num_trades` | INTEGER | NOT NULL | |
| `raw_result_json` | JSONB | NULLABLE | |
| `executed_at` | TIMESTAMPTZ | server default `now()` | |

**Status: planned, not yet migrated (Phase 3 scope).**

### 2.8 `trade_execution` (planned — Phase 6+)

Reserved for the broker adapter layer. Remains empty until crypto/paper execution is implemented.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | |
| `instrument_id` | UUID | FK, NOT NULL | |
| `backtest_result_id` | UUID | FK, NULLABLE | |
| `broker_type` | ENUM(`PAPER_SIM`, `BINANCE_TESTNET`, ...) | NOT NULL | Extensible enum for future broker adapter implementations |
| `side` | ENUM(`BUY`, `SELL`) | NOT NULL | |
| `quantity`, `price` | NUMERIC(20,8) | NOT NULL | |
| `status` | ENUM(`PENDING`, `FILLED`, `CANCELLED`) | NOT NULL | |
| `external_order_id` | VARCHAR | NULLABLE | Reference into the actual exchange/testnet order, when applicable |
| `executed_at` | TIMESTAMPTZ | | |

**Status: planned, not yet migrated (Phase 6+ scope).**

## 3. Entity Relationships

```
instrument (1) ──── (N) price_bar
instrument (1) ──── (N) analysis_run
analysis_run (1) ──── (N) agent_opinion
analysis_run (1) ──── (0..1) recommendation
recommendation (1) ──── (0..1) backtest_result
recommendation.analysis_run.thread_id ──logical──> checkpoints (LangGraph-managed)
instrument (1) ──── (N) trade_execution
```

## 4. Indexes and Constraints Summary

| Table | Constraint / Index | Purpose |
|---|---|---|
| `instrument` | UNIQUE `(ticker, source)` | Prevents duplicate instrument records per data provider |
| `price_bar` | UNIQUE `(instrument_id, ts, timeframe)` | Enables idempotent data ingestion (`ON CONFLICT DO NOTHING`) |
| `price_bar` | INDEX `(ts)` | Cross-instrument time-range queries |
| `analysis_run` | INDEX `(thread_id)` | Fast lookup of LangGraph execution trace during debugging |
| `agent_opinion` | INDEX `(analysis_run_id)` | Fetching all opinions for a run |
| `recommendation` | UNIQUE `(analysis_run_id)` | Enforces 1:1 with `analysis_run` |

## 5. Data Type Rationale

`NUMERIC(20,8)` was chosen for price fields (rather than a narrower type like `NUMERIC(10,2)`) specifically to accommodate cryptocurrency price precision without requiring a future migration — this is a deliberate crypto-readiness decision made at Phase 0, even though only equities are ingested initially.

`JSONB` columns (`agent_opinion.raw_output_json`, `backtest_result.raw_result_json`) exist alongside structured relational columns rather than replacing them. This hybrid approach preserves query-ability (via the relational columns) while tolerating schema drift in LLM output format (via the JSON blob) without forcing an immediate migration every time a prompt or model changes its output shape.

## 6. Migration Workflow

1. Modify SQLAlchemy models in `data/models.py`.
2. Generate a migration: `alembic revision --autogenerate -m "<description>"`.
3. **Manually review** the generated migration file in `data/alembic/versions/` before applying — autogenerate is a starting point, not a guarantee of correctness (e.g., enum changes and data backfills are not always auto-detected correctly).
4. Apply: `alembic upgrade head`.
5. Verify via `psql \dt` and a manual `SELECT`.