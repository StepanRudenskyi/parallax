# Architecture

## 1. Purpose and Scope

This document describes the target high-level architecture of the AI Trading Research Agent, the phased build-out sequence, inter-component communication, and the scalability and extensibility decisions baked into the design from the start. The system is built incrementally; each phase is only started once the previous one works end-to-end. No phase is scheduled by date — completion is defined by explicit functional criteria.

## 2. Guiding Principles

- **Separation of concerns by language and responsibility.** The Python layer is responsible exclusively for *reasoning* (producing a recommendation and its justification). The Java layer is responsible exclusively for *execution simulation* (determining what would have happened if a recommendation had been acted on). Neither layer duplicates the other's logic.
- **Supervisor-first multi-agent pattern.** LangGraph supports several multi-agent topologies (supervisor, hierarchical, swarm). The supervisor pattern is adopted because routing is its only responsibility, which makes it more accurate and cheaper in tokens than hierarchical delegation, and simpler to reason about for a single part-time developer than a swarm/peer-to-peer topology.
- **State lives in PostgreSQL, not in process memory.** Both the LangGraph checkpointer and all business entities are persisted in PostgreSQL. This makes every service instance stateless and horizontally scalable without code changes, even though the project does not currently need more than one instance of anything.
- **Docker from day one.** Every service ships with a Dockerfile and is wired into `docker-compose.yml`, even while the project runs entirely on a single local machine. This is a deliberate "deployment-ready, not deployed" stance.
- **Crypto-ready abstractions without crypto-specific code.** The data model and execution-layer interfaces are generalized (`asset_type`, broker adapter interface) so that adding cryptocurrency support later is a matter of adding new implementations, not rewriting core logic.

## 3. High-Level Component Diagram

```
                         ┌─────────────────────┐
                         │   Next.js Frontend  │  (Phase 4)
                         │   (Browser / SSR)   │
                         └──────────┬──────────┘
                                    │ HTTPS / REST (JSON)
                                    ▼
                         ┌───────────────────────┐
                         │  Python AI Backend    │
                         │  FastAPI + LangGraph  │  (Phase 1-2)
                         │  (agents + supervisor)│
                         └───┬────────┬────────┬─┘
                    REST/gRPC│        │        │ REST
                             │        │        │
              ┌──────────────┘        │        └──────────────┐
              ▼                       ▼                       ▼
   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
   │ Java Execution/     │  │ PostgreSQL          │  │ Ollama (local LLM)  │
   │ Backtesting Service │  │ - market data       │  │ + Jev AI (System-1) │
   │ Spring Boot + ta4j  │  │ - agent checkpoints │  │ + Cloud LLM (later) │
   │ (Phase 3)           │  │ - recommendations   │  └─────────────────────┘
   └─────────┬───────────┘  │ - backtest results  │
             │              └─────────────────────┘
             ▼
   ┌──────────────────────┐
   │ Broker Adapter Layer │  (Crypto hook, Phase 6+)
   │ - Paper trading sim  │  (Phase 3)
   │ - Exchange testnet   │  (Phase 6+)
   └──────────────────────┘
```

## 4. Component Responsibilities

| Component | Responsibility | Explicitly NOT responsible for |
|---|---|---|
| Next.js Frontend | Render analysis requests, agent opinions, final recommendation, backtest charts | Any business logic, LLM calls, or data persistence |
| Python AI Backend | Data retrieval for agents, prompt construction, LLM orchestration via LangGraph, opinion synthesis via supervisor | Computing P&L, simulating trades, placing orders |
| Java Execution Service | Deterministic backtesting of recommendations against historical data, (later) paper/testnet order execution | Generating recommendations, calling LLMs |
| PostgreSQL | Single source of truth for market data, agent state (LangGraph checkpoints), recommendations, backtest results | Business logic of any kind |
| Ollama / Jev AI / Cloud LLM | Model inference (reasoning for Ollama/cloud, fast structured decisions for Jev AI) | Data persistence, orchestration logic |
| Broker Adapter Layer | Abstracting "what happens when a recommendation is acted on" behind one interface, with interchangeable implementations | Deciding whether to act on a recommendation |

## 5. Communication Matrix

| Source | Target | Channel | Sync/Async | Introduced in |
|---|---|---|---|---|
| Next.js | Python FastAPI | REST/HTTPS, JSON | Synchronous request-response | Phase 4 |
| FastAPI endpoint | LangGraph supervisor graph | In-process Python call (`.invoke()`/`.ainvoke()`) | Synchronous | Phase 1 |
| Supervisor agent | Specialist agents (sentiment/quant/fundamental) | LangGraph handoff via structured output / `Command` | Synchronous within the graph | Phase 2 |
| Agents | Ollama / Jev AI / Cloud LLM | REST over HTTP (localhost for Ollama, HTTPS for Jev/cloud) | Synchronous, with retry | Phase 1-2 |
| Python layer | PostgreSQL | SQL via SQLAlchemy / psycopg | Synchronous | Phase 0 |
| Python layer | Java Execution service | REST/HTTPS, JSON (gRPC evaluated later if latency becomes an issue) | Synchronous initially | Phase 3 |
| Java Execution service | PostgreSQL | JDBC | Synchronous | Phase 3 |
| Java Execution service | Broker Adapter (paper/testnet) | In-process Java interface call | Synchronous | Phase 3 (paper), Phase 6+ (testnet) |
| (Future) Market data ingestion | Agents / Execution service | Message queue (RabbitMQ candidate) | Asynchronous, streaming | Phase 6+ |

Note on internal agent communication: LangGraph agent-to-agent handoff is **not** a network call. It is a state transition within a single compiled graph — the supervisor node produces a structured decision (a Pydantic model with a `next_agent` field or equivalent) that determines which node executes next, and results are merged back into shared graph state via reducers. This is architecturally distinct from the REST boundary between Python and Java, which does involve real network serialization.

## 6. Sequence Flow — "Analyze Ticker" (Phase 1-2)

1. Client (curl/Postman in Phase 1, later Next.js in Phase 4) sends `POST /analyze {"ticker": "AAPL"}` to FastAPI.
2. FastAPI creates or resumes a `thread_id` (for the LangGraph checkpointer) and invokes the compiled graph.
3. The supervisor node makes a structured routing decision: invoke all three specialists (in parallel, from Phase 2 onward) or a subset.
4. Each specialist (sentiment / quant / fundamental) reads the data it needs from PostgreSQL, builds a prompt, calls its configured model (Ollama, Jev AI for classification sub-tasks, or a cloud LLM), and returns a structured opinion into graph state.
5. The supervisor receives all specialist opinions (aggregated in state via a reducer), and synthesizes a final recommendation with a confidence score.
6. The LangGraph PostgreSQL checkpointer persists the full state of every step, enabling later inspection of "why this recommendation" without re-invoking any LLM.
7. FastAPI returns the JSON response to the client: `{ recommendation, confidence, per_agent_reasoning }`.

## 7. Sequence Flow — "Backtest a Recommendation" (Phase 3+)

1. After step 6 above, the Python layer makes a REST call to the Java Execution service: `POST /backtest { ticker, recommendation, date }`.
2. Spring Boot receives the request and retrieves historical bars from PostgreSQL (same database instance, separate table ownership).
3. ta4j's `BacktestExecutor` runs the strategy implied by the recommendation over the historical series and computes metrics (P&L, number of trades, Sharpe ratio, max drawdown).
4. The Java service persists the result to PostgreSQL (`backtest_result` table) and returns a JSON response.
5. The Next.js frontend (Phase 4) renders the result as an overlay on the instrument's price chart.

## 8. Scalability Considerations

The system has two structurally different workload profiles, and each is scaled with the mechanism appropriate to it rather than by choosing a single "scalable language":

| Layer | Workload type | Bottleneck | Scaling lever |
|---|---|---|---|
| Python AI (FastAPI + LangGraph) | I/O-bound (waiting on LLM responses) | Number of concurrent LLM calls, not CPU | More stateless workers behind a load balancer; autoscale on in-flight graph runs, not CPU utilization |
| Java Execution (Spring Boot + ta4j) | CPU-bound (numerical computation over historical series) | Compute capacity | Horizontal cloning of stateless instances (12-factor pattern) |
| PostgreSQL | I/O + connection throughput | `max_connections`, disk I/O | Connection pooling (PgBouncer for Python, HikariCP for Java), read replicas if ever needed |

Because the LangGraph checkpointer stores all state in PostgreSQL rather than in-process memory, any FastAPI worker can pick up any request — this is what makes the Python layer horizontally scalable without sticky sessions. The Java Execution service is stateless by construction (12-factor Spring Boot), so adding replicas behind a reverse proxy requires no code changes.

None of this is enabled at the current hobby scale — it is explicitly deferred (see ADR-010 in `docs/decisions.md`) — but no current architectural decision blocks it from being enabled later.

## 9. Crypto Extension Points (Phase 6+)

Three architectural seams are established before crypto is actually implemented, specifically so the core system does not need to be rewritten later:

1. **`instrument.asset_type` abstraction.** The data model distinguishes `EQUITY` and `CRYPTO` at the instrument level from Phase 0 onward. Adding crypto support is a matter of adding a new data provider implementation, not changing the schema.
2. **Broker Adapter interface in the Java Execution service.** From Phase 3, execution logic is written against an interface with a single "paper trading simulator" implementation. A second implementation (exchange testnet client) is added in Phase 6+ without touching backtesting logic.
3. **Agent "philosophy" decoupled from asset class.** Sentiment/quant/fundamental agents operate on abstracted input (price series, news, fundamentals) rather than asset-specific logic, so the same agents can analyze a crypto pair once a crypto data provider exists.

## 10. Full Phase Roadmap

| Phase | Goal | Key technologies | Completion criterion |
|---|---|---|---|
| 0 | Data pipeline & Docker environment | PostgreSQL, Alembic, yfinance, Docker Compose | `docker compose up` starts a healthy database; a seed script populates historical OHLCV data; verifiable via SQL query |
| 1 | Single LangGraph agent (no supervisor) | LangGraph (linear `StateGraph`), FastAPI, Ollama, Pydantic structured output | A REST call returns a structured recommendation for a given ticker without crashing |
| 2 | Multi-agent supervisor architecture | `langgraph-supervisor`, PostgreSQL checkpointer, Jev AI for classification sub-tasks | One HTTP request triggers all three specialist agents and returns one synthesized, traceable recommendation |
| 3 | Execution / backtesting service | Spring Boot, ta4j, REST between Python and Java | A recommendation can be backtested against historical data and returns P&L/Sharpe/drawdown metrics |
| 4 | Frontend dashboard | Next.js (App Router) | A browser UI can trigger an analysis and display all three agent opinions plus the backtest result |
| 5 | Observability & deployment hardening | Structured logging, retries, full multi-service Docker Compose stack | The entire stack starts with one command on a clean machine; per-request LLM cost/latency is observable |
| 6+ | Crypto paper/testnet trading | Exchange testnet APIs (e.g., Binance testnet), broker adapter implementation | A crypto instrument can be analyzed and its recommendation executed against a testnet, with zero real funds at risk |

See `docs/decisions.md` for the reasoning behind the technology choices referenced above.