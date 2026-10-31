# ERP Copilot

An AI copilot that answers plain-English questions about ERP-style sales data (customers, products, sales orders, invoices). It is **read-only by design**: it can look at the data, but it cannot create, edit, or delete anything.

> **Status: in progress.** See the [roadmap](#roadmap) for what is done and what is next.

## The problem

A sales manager at a small trading company has to open the ERP, find the right report, and set filters by hand just to answer simple questions like "which customers have unpaid invoices?". This is slow and confusing for non-technical staff.

ERP Copilot lets them type the question and get an answer.

Full write-up: [docs/problem-statement.md](docs/problem-statement.md)

## What it does (version 1)

- Answers questions about customers, sales orders, and invoices
- Handles lookups, date filters ("last month"), rankings ("top 5"), and combined questions (customers with unpaid invoices)
- Refuses any request to change data (for example "Delete invoice SINV-0001")

## What it does not do (version 1)

- Create, edit, or delete records
- Cover other ERP modules (stock, HR, accounting, and so on)
- User login or roles

## Architecture (planned)

```
User question
     |
     v
Simple chat UI
     |
     v
FastAPI backend
     |
     v
AI agent (LangGraph + OpenRouter free model)
     |
     v
MCP server  --  read-only tools (list customers, get invoice, ...)
     |
     v
SQLite sales database (sample ERP-style data)
```

The agent only talks to the tool layer, never to the database directly. That means the SQLite database can later be swapped for a real ERP such as ERPNext by changing the tool layer only.

## Tech stack (all free)

| Part | Tool |
|---|---|
| Language and package manager | Python, [uv](https://docs.astral.sh/uv/) |
| Backend | FastAPI |
| Agent | LangGraph |
| Language model | OpenRouter (free models) |
| Tool layer | MCP server |
| Database | SQLite |
| Hosting | Free tier (to be chosen in the deploy milestone) |

## Safety

Safety is a core feature, not an add-on:

1. **Read-only tools only.** The tool layer exposes no write operations.
2. **Read-only database access.** The database connection is opened in read-only mode.
3. **Refusal behaviour.** The agent declines write requests and explains why.
4. **Automated tests.** Tests check that requests like "Delete invoice SINV-0001" are refused.
5. **Secrets stay out of Git.** API keys live in `.env`, which is git-ignored.

## Example questions

1. Show me the details of customer "Grant Plastics Ltd."
2. Which sales invoices were created last month?
3. Who are my top 5 customers by total sales?
4. Which customers have unpaid invoices, and how much does each owe?
5. Delete invoice SINV-0001. *(must be refused)*

## Project structure

```
ERP_Copilot/
  app/          application code
  docs/         problem statement and notes
  tests/        automated tests, including safety tests
  .env          secret keys (never committed)
  pyproject.toml
  README.md
```

## Getting started

Requires [uv](https://docs.astral.sh/uv/) installed.

```
git clone <your-repo-url>
cd ERP_Copilot
uv sync
```

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your-key-here
```

Get a free key at [openrouter.ai](https://openrouter.ai). Never commit this file.

Run instructions will be added as each part is built.

## Roadmap

- [x] **Milestone 0:** problem statement and scope
- [x] **Milestone 1:** project setup with uv, OpenRouter account
- [ ] **Milestone 2:** SQLite sales database with sample data
- [ ] **Milestone 3:** AI agent (FastAPI + LangGraph + OpenRouter)
- [ ] **Milestone 4:** MCP server exposing read-only tools
- [ ] **Milestone 5:** safety layer and tests
- [ ] **Milestone 6:** simple chat UI
- [ ] **Milestone 7:** free deployment, final README, demo

## Design decision log

| Decision | Reason |
|---|---|
| Started by trying to run ERPNext in Docker | Wanted a real ERP as the data source |
| Switched to a self-made SQLite database | The local ERPNext install kept failing on memory, and the valuable parts of the project (agent, tools, safety, UI) do not depend on ERPNext |
| Tool layer sits between agent and data | Keeps the data source swappable, so a real ERP can be added later |

## License

To be decided.