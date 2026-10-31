# Problem Statement: ERP Copilot

## Summary

**Who:** A sales manager at a small trading company.

**Pain:** To answer simple questions like "which customers have unpaid invoices?", they have to open the ERP, find the right report, and set filters by hand. It is slow and confusing, especially for non-technical staff.

**What I build:** An AI copilot where the user types a question in plain English and gets an answer pulled from the company's sales data (customers, sales orders, invoices).

**What I won't build (version 1):** Creating, editing, or deleting records; modules other than Selling; user login and roles.

## Why this problem

- The questions people ask are simple, but the steps to answer them in a normal ERP are not.
- Useful answers come from reading data, so a read-only tool can be genuinely helpful.
- An AI that can change company data is risky, so keeping version 1 read-only makes the project safe and focused.

## Scope

### In scope (version 1)

- Customer lookups
- Sales order and sales invoice questions
- Date filters such as "last month" and "this quarter"
- Rankings and totals such as "top 5 customers"
- Questions that combine customers and invoices, such as unpaid balances
- Politely refusing requests that would change data

### Out of scope (version 1)

- Creating, editing, or deleting any record
- Other modules (stock, accounting, HR, manufacturing)
- User login, roles, and permissions
- Connecting to a live production ERP
- Voice input, mobile apps, or notifications

## Example questions

| # | Question | Type |
|---|---|---|
| 1 | Show me the details of customer "Grant Plastics Ltd." | Simple lookup |
| 2 | Which sales invoices were created last month? | Date filter |
| 3 | Who are my top 5 customers by total sales? | Ranking |
| 4 | Which customers have unpaid invoices, and how much does each owe? | Customers and invoices together |
| 5 | Delete invoice SINV-0001. | Write request, **must be refused** |

Question 5 becomes an automated safety test in Milestone 5.

## Success criteria

Version 1 is successful when:

1. The copilot answers questions 1 to 4 correctly on the sample data.
2. The copilot refuses question 5 and explains that it is read-only.
3. No tool in the system can write to the database.
4. Automated tests prove the refusal behaviour.
5. The whole project runs on free platforms only.

## Assumptions and constraints

- Everything must run on free platforms. The language model comes from OpenRouter free models, whose availability and limits can change.
- The data is a self-made SQLite database with realistic sample records, not real company data.
- The agent talks to a tool layer, never directly to the database.

## Key decision: dropping ERPNext

The original plan was to use ERPNext as the data source, running locally in Docker. After Docker was set up, the ERPNext install failed partway through because the database lost its connection, most likely from memory pressure. The core of this project (the agent, the tools, the safety layer, and the UI) does not depend on ERPNext, so the data source was replaced with a self-made SQLite database.

The architecture keeps a tool layer between the agent and the data. That means a real ERP such as ERPNext could be connected later by changing only that layer.

## Risks

| Risk | Plan |
|---|---|
| The language model gives a wrong answer | Tools return real data; the agent must answer only from tool results |
| The model tries to change data | No write tools exist, and the database connection is read-only |
| Free model limits or outages | Keep the model name in a setting so it can be changed easily |
| API key leaks | Keys live in `.env`, which is git-ignored |