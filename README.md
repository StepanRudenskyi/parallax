# AI Trading Research Agent

A multi-agent AI system for equity and (future) cryptocurrency research. Multiple specialist agents analyze an instrument from different perspectives (sentiment, quantitative/technical, fundamental), a supervisor agent synthesizes their opinions into a single recommendation, and a separate execution/backtesting layer evaluates how that recommendation would have performed historically.

This is a personal, part-time hobby project. The architecture is designed to be "deployment-ready" from day one (Docker-first, stateless services, externalized state) even though the project currently runs only locally.

## Project Status

**Current phase: Phase 0 — Data & Environment Skeleton (COMPLETE)**

- PostgreSQL running via Docker Compose.
- Database schema for `instrument` and `price_bar` managed via Alembic migrations.
- Historical OHLCV data for AAPL, MSFT, NVDA seeded via a Python script using `yfinance`.

See [architecture.md](ai-trading-agent/docs/architecture.md) for the full phase roadmap and target high-level design, and [decisions.md](ai-trading-agent/docs/decisions.md) for the reasoning behind key technical choices.

## Technology Stack

| Layer | Technology | Status |
|---|---|---|
| AI backend | Python + LangGraph + FastAPI | Planned (Phase 1+) |
| Execution / Backtesting | Java + Spring Boot + ta4j | Planned (Phase 3+) |
| Frontend | Next.js | Planned (Phase 4+) |
| Database | PostgreSQL | Implemented |
| Local LLM | Ollama | Planned (Phase 1+) |
| Decision layer | Jev AI (TypeSafe, System-1 model) | Planned (Phase 2+) |
| Containerization | Docker / Docker Compose | Implemented |
| Data provider (equities) | yfinance (unofficial Yahoo Finance scraper) | Implemented |

## Repository Structure

```
ai-trading-agent/
├── agents/              # Python + LangGraph + FastAPI AI backend (Phase 1+)
├── execution/           # Java + Spring Boot + ta4j execution/backtesting service (Phase 3+)
├── web/                 # Next.js frontend (Phase 4+)
├── data/                # Database models, Alembic migrations, seed scripts (Phase 0)
│   ├── models.py        # SQLAlchemy declarative models (source of truth for schema)
│   ├── db.py            # Engine / session factory for standalone scripts
│   ├── seed_price_data.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env             # not committed — see .env.example
├── infra/               # Docker Compose files, environment templates
│   ├── docker-compose.yml
│   └── .env.example
├── docs/
│   ├── architecture.md
│   ├── database-schema.md
│   └── decisions.md
└── README.md
```

Single monorepo is used deliberately for a solo, slow-paced hobby project — see ADR-001 in [decisions.md](ai-trading-agent/docs/decisions.md).

## Getting Started (Phase 0)

Prerequisites: Docker Desktop, Python 3.11+, an available local port for PostgreSQL.

1. Start the database:
   ```
   cd infra
   docker compose up -d
   ```
2. Set up the Python environment for the data layer:
   ```
   cd ../data
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```
3. Copy `infra/.env.example` values into a new `data/.env` file (the seed/migration scripts connect from the host, so they use `localhost` and the host-mapped port, not the Docker-internal hostname).
4. Apply database migrations:
   ```
   alembic upgrade head
   ```
5. Seed historical price data:
   ```
   python seed_price_data.py
   ```
6. Verify:
   ```
   docker exec -it ai-trading-postgres psql -U trading_user -d trading_db -c "\dt"
   ```

## Roadmap Overview

| Phase | Goal | Key technologies |
|---|---|---|
| 0 | Data pipeline & Docker environment | PostgreSQL, Alembic, yfinance |
| 1 | Single LangGraph agent, no supervisor | LangGraph, FastAPI, Ollama |
| 2 | Multi-agent supervisor architecture | langgraph-supervisor, Jev AI |
| 3 | Execution / backtesting service | Spring Boot, ta4j |
| 4 | Frontend dashboard | Next.js |
| 5 | Observability & deployment hardening | structured logging, full Docker Compose stack |
| 6+ | Crypto paper/testnet trading | broker adapter pattern, exchange testnet APIs |

Full detail for every phase, including completion criteria, is in [architecture.md](ai-trading-agent/docs/architecture.md).

## License / Scope

Personal hobby/learning project. Not intended for real-money trading. Any future crypto execution will use paper trading or exchange testnets exclusively.