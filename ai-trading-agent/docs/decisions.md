# Architecture Decision Log

This log records the reasoning behind significant technical decisions, in lightweight ADR (Architecture Decision Record) format. Each entry captures the context, the decision, and the consequences, so the rationale is not lost as the project evolves over an extended, part-time timeline.

---

## ADR-001: Monorepo instead of multiple repositories

**Context:** The project spans three languages/runtimes (Python, Java, Next.js/TypeScript) plus infrastructure config. Multi-repo setups are common in team environments to allow independent versioning and access control.

**Decision:** Use a single monorepo (`agents/`, `execution/`, `web/`, `data/`, `infra/`, `docs/`).

**Rationale:** This is a solo project developed at irregular, low-frequency intervals (evenings/weekends). Multi-repo setups introduce synchronization overhead (a Python-side contract change breaking an unreleased Java-side assumption, coordinating PRs across repos) that is disproportionately costly for a single developer working in short, spaced-out sessions. A monorepo keeps all context in one place and one Git history.

**Consequences:** CI/CD (when eventually introduced) will need path-based triggers to avoid rebuilding all services on every commit. This is an acceptable future cost given the current benefit.

---

## ADR-002: PostgreSQL instead of TimescaleDB (for now)

**Context:** The project stores time-series OHLCV data. TimescaleDB is a PostgreSQL extension purpose-built for time-series workloads (hypertables, compression policies).

**Decision:** Use plain PostgreSQL. Do not install TimescaleDB at this stage.

**Rationale:** At hobby scale (a handful of tickers, daily/hourly bars), plain PostgreSQL is fully sufficient — TimescaleDB's advantages (compression, specialized time-partitioning) only become material at intraday/tick-level data volumes across many instruments. Installing it now would be a premature optimization that adds operational complexity (extension management, hypertable configuration) without a corresponding benefit.

**Consequences:** If the project later ingests minute/tick-level data across many instruments (particularly relevant for the Phase 6+ crypto extension), TimescaleDB should be re-evaluated at that point. The `price_bar` schema (single flat table, timestamp column, composite unique index) is compatible with a later conversion to a TimescaleDB hypertable without a data model rewrite.

---

## ADR-003: REST first, gRPC evaluated later, for Python↔Java communication

**Context:** The Python AI backend and Java Execution service need to exchange recommendation and backtest data.

**Decision:** Use REST/HTTPS with JSON payloads initially. Do not introduce gRPC at this stage.

**Rationale:** REST requires no additional tooling (protobuf schema definitions, code generation pipeline) and is sufficient for the current request volume and latency requirements (a handful of manual analysis requests per session). Introducing gRPC now would add setup and learning overhead disproportionate to the current need, particularly given the developer's stated unfamiliarity with the Python AI/LLM stack — one new technology at a time is preferable to stacking unfamiliar tools.

**Consequences:** If request volume or latency requirements increase substantially (e.g., high-frequency backtesting loops), gRPC with protobuf-defined contracts should be reconsidered. Because the REST contract is already narrow and JSON-schema-defined, migrating specific endpoints to gRPC later is a bounded, incremental change rather than an architectural rewrite.

---

## ADR-004: Supervisor pattern over hierarchical/swarm for multi-agent orchestration

**Context:** LangGraph supports multiple multi-agent topologies: supervisor (single coordinator routes to specialists), hierarchical (nested supervisors), and swarm (peer-to-peer handoff).

**Decision:** Adopt the supervisor pattern for the sentiment/quant/fundamental agent team.

**Rationale:** The supervisor pattern's routing logic has a single responsibility (deciding who should act next), which makes it more accurate and cheaper in LLM tokens than hierarchical delegation, and easier to reason about and debug for a developer new to LangGraph than a peer-to-peer swarm topology. Hierarchical and swarm patterns are more appropriate for larger agent counts or more dynamic, unpredictable collaboration patterns than the current fixed three-specialist team requires.

**Consequences:** If the number of specialist agents grows significantly (e.g., separate agents per data source, or per asset class), a hierarchical supervisor-of-supervisors structure should be reconsidered rather than growing a single flat supervisor's routing logic indefinitely.

---

## ADR-005: Phased LLM strategy — local-first, cloud when it matters

**Context:** LLM API costs are non-trivial at scale but often negligible at hobby-project volume; local models via Ollama are free but generally weaker at complex reasoning than frontier cloud models.

**Decision:**
- **Phases 0-2 (learning, graph development, prompt iteration):** Ollama exclusively, using a tool-calling-capable model (e.g., Qwen3 8B/30B-A3B, or Hermes 4 14B) sized to available local hardware.
- **Phases 3-4 (stabilizing graph, higher-quality synthesis needed):** Hybrid — local models for simpler extraction/classification tasks (sentiment classification, indicator formatting), a paid cloud API for the supervisor's final synthesis step where reasoning quality matters most.
- **Phase 5+ (stable, production-like system):** Cloud API for supervisor and sentiment reasoning; local models retained only for high-volume, low-complexity tasks.

**Rationale:** Iterating on prompts and graph structure benefits from unlimited, free, zero-latency-cost experimentation, which only local inference provides. Paid API costs become justified only once the system's structure is stable enough that spending is not wasted on debugging graph logic rather than improving recommendation quality.

**Consequences:** Each agent node must support a configurable `model` parameter independent of other nodes, so that migrating individual agents from local to cloud models does not require structural changes to the graph.

---

## ADR-006: Jev AI (TypeSafe System-1 model) as a decision/classification layer, not a reasoning replacement

**Context:** Jev is a non-autoregressive "System-1" decision model (Choice/Score/Noul question types) released by TypeSafe AI in September 2026, offering millisecond-scale, low-cost, calibrated-confidence structured decisions rather than generated text.

**Decision:** Use Jev AI for narrow classification/gating sub-tasks — sentiment classification (bullish/bearish/neutral), and a confidence gate between the Python recommendation layer and the Java execution layer (a `Noul` question determining whether a recommendation is confident enough to proceed to backtesting). Do not use it as a substitute for the reasoning LLM in the supervisor or specialist agents.

**Rationale:** Jev's architecture is designed for exactly this class of problem — bounded, typed decisions — and is dramatically cheaper and faster than an LLM call for the same task. Reasoning tasks (constructing an argument for why an instrument looks attractive) still require a generative LLM.

**Consequences:** Because Jev AI was in early access as of this decision, a fallback to LLM-based structured classification (via Ollama) must be maintained in case the Jev API proves unstable or changes materially.

---

## ADR-007: ta4j for the Java backtesting engine

**Context:** The Java Execution service needs to simulate strategy performance over historical price series.

**Decision:** Use the ta4j library (`BarSeriesManager` for single-strategy backtests, `BacktestExecutor` for comparing multiple strategies over one series) rather than building a backtesting engine from scratch.

**Rationale:** ta4j is a mature, actively maintained, open-source Java technical-analysis and backtesting library that directly matches the project's need to backtest multiple agent-derived strategies against the same historical series. Building an equivalent engine from scratch would consume disproportionate hobby-time budget on infrastructure rather than on the actual multi-agent research problem.

**Consequences:** Backtest result fields (`pnl_absolute`, `sharpe_ratio`, `max_drawdown`, `num_trades`) are chosen to align with what ta4j readily exposes, minimizing custom calculation code.

---

## ADR-008: Crypto-readiness baked into the core data model and execution interface

**Context:** Cryptocurrency trading is an explicit future goal (Phase 6+), but is deliberately not implemented early, to avoid front-loading complexity into an already ambitious hobby project.

**Decision:** Establish three seams now, without implementing crypto logic:
1. `instrument.asset_type` distinguishes `EQUITY`/`CRYPTO` from Phase 0.
2. Price fields use `NUMERIC(20,8)` precision, sufficient for crypto's finer-grained pricing, from Phase 0.
3. The Java Execution service's order-placement logic is written against a Broker Adapter interface with a single "paper trading simulator" implementation from Phase 3; a second implementation (exchange testnet client) is added only in Phase 6+.

**Rationale:** Retrofitting asset-class generality and an execution abstraction after the fact typically requires touching code that has since accumulated assumptions specific to equities. Establishing the seam early costs little (an enum value, a wider numeric type, one interface instead of one concrete class) and avoids a disruptive rewrite later.

**Consequences:** No crypto-specific data provider, streaming ingestion, or exchange integration is implemented before Phase 6 — the seams exist, but remain unused until then.

---

## ADR-009: Python/Alembic owns all schema migrations; Java is schema read-only

**Context:** Both the Python and Java services read and write the same PostgreSQL database.

**Decision:** All `CREATE`/`ALTER TABLE` operations happen exclusively through Alembic migrations defined against SQLAlchemy models in `data/models.py`. The Java service's ORM (if/when JPA/Hibernate is used) has `ddl-auto` disabled and never modifies schema.

**Rationale:** Allowing two independent ORMs in two languages to both believe they own schema evolution is a well-known source of migration conflicts and silent schema drift. Assigning single ownership eliminates this failure mode entirely, at negligible cost (the Java service simply maps to tables that already exist).

**Consequences:** Any schema change needed by the Java service (e.g., a new column required for backtest results) must be requested/implemented as a Python-side Alembic migration, even though the Java service is the primary consumer of that table.

---

## ADR-010: Docker Compose from day one; no orchestration platform (Kubernetes) yet

**Context:** The project currently runs entirely on a single local development machine, with a single user.

**Decision:** Every service is containerized and wired into `docker-compose.yml` from its introduction, but no container orchestration platform (Kubernetes, Nomad) is introduced at this stage. Likewise, message queues (RabbitMQ/Kafka), connection poolers (PgBouncer), and horizontal autoscaling are deferred.

**Rationale:** These tools solve problems (multi-instance coordination, load distribution across replicas, decoupling producers/consumers at scale) that do not exist at current hobby scale, and introducing them now would be premature optimization that consumes limited development time without a corresponding benefit. However, because every service is already stateless with state externalized to PostgreSQL (see `architecture.md` §8), none of these tools are blocked by any current design choice — they can be introduced later purely as infrastructure additions.

**Consequences:** If the project ever needs multi-instance scaling, the migration path is: `docker compose --scale` for a first step, then Kubernetes with HPA/KEDA (scaling LangGraph workers on in-flight run depth rather than CPU) if load genuinely requires it. This is documented as a deferred, not rejected, capability.