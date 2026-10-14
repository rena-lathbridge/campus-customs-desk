# Campus Customs — the back office

A five-agent team that works the Campus Customs shop's ticket queue, and a board to watch it do it.

Three tickets land on the desk: a customer wants a tee that is out of stock, the landlord wants
rent, and a student group wants twenty hoodies at a discount. The shop has $3,400 in the bank and
$3,240 of obligations. The team has to answer all three honestly without over-promising, without
selling below cost, and without spending a penny on its own authority.

---

## What's here

| Path | What it is |
|---|---|
| `data/` | `campus_customs.db` is the original seed, never written to. `campus_customs_new.db` is the working copy everything reads and writes. |
| `mcp_server/server.py` | A FastMCP server exposing the shop's database as eight tools. Seven read; one spends. |
| `backend/` | The FastAPI backend and the PydanticAI agent team. |
| `backend/prompts/*.md` | One system prompt per agent, in plain markdown. |
| `frontend/` | The React + Vite + TypeScript board. |
| `output/` | Every deliverable: the harness notes, the plan-vs-actual write-up, the run record and the screenshots. |

### The team

| Agent | Owns |
|---|---|
| **Boss** | The decision. The only agent that closes a ticket. |
| **Inventory** | What is on the shelf, counted per size. |
| **Accounting** | Balances, unpaid bills, the price floor. |
| **Facilities** | The lease and the rent calendar. |
| **Customer Service** | The words that reach a person. |

Every agent can delegate to every other — twenty edges — with two guards stopping it looping: an
agent already in a branch's chain cannot be re-asked, and delegation is refused past a depth limit.

---

## Running it

### 1. Install

```bash
python3 -m pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2. Add your key

```bash
cp .env.example .env     # then put your real PORTKEY_API_KEY in it
```

The real `.env` is git-ignored and is not in this repository. Without it the board still runs and
shows the tickets, the cash and the completed run; only starting a *new* agent run needs the key.

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Start the board

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The backend allows exactly that origin.

---

## Using the board

The database ships in its **post-run state**: all three tickets resolved, checking at **$160.00**,
both payments recorded. That is the state the write-ups in `output/` describe.

- **Reset day** puts it back to $3,400.00 with three open tickets.
- **Run team on #N** runs the agent team on a ticket. This makes real model calls and costs money.
- When a run proposes a payment, it appears in the till as a chit. **Nothing is paid until a human
  types a name and approves it** — see below.

Verify everything without spending anything:

```bash
python3 mcp_server/smoke_test.py   # exercises the MCP tools against the database
python3 backend/verify_team.py     # checks the team wiring; makes no model calls
```

---

## The rule the whole thing is built around

**Agents prepare payments. Humans make them.** Enforced three ways, not just asked for in a prompt:

1. The run route passes no approver, so by the team's own rules no agent may pay.
2. `record_payment` is blocked at the toolset — an agent's call never reaches the server.
3. The approve route reaches the MCP server through its own client, so blocking agents doesn't
   block people.

The payment itself still goes through `record_payment`, so every guard applies to the dashboard too:
a named approver, no overdraw, no paying a bill twice, and one transaction across `payments`,
`cash_accounts` and `invoices`.

---

## Notes for anyone running this

- **`.mcp.json`** uses `python3`. If your MCP client starts the server with a minimal `PATH` it may
  pick a Python without `fastmcp`; put an absolute interpreter path there if so.
- **`CAMPUS_CUSTOMS_DB`** is ignored if you export it in a shell — an MCP client does not pass your
  environment to the server it launches. Set it in the client's own config instead.
- **The event log is in memory.** Restarting the backend empties the board's wire; the database is
  untouched.

---

## Where to look first

`output/desk_tickets.html` — one tab per ticket with what was predicted before the run and what
actually happened, plus the itemised cash ledger and the reflection. Open it in a browser; it needs
no server.
