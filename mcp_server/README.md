# Campus Customs MCP Server

## What this is for

This is the shared toolbox for every agent in this assignment.

The Campus Customs shop keeps all its real numbers — stock, prices, rent, bank balance — in one
database. An agent on its own can't see any of that, and if we let each agent guess, they'd each
guess differently. This MCP server sits in between: agents ask it questions, it looks the answer up
in the database, and it hands back only what's actually recorded there. Nothing is estimated,
assumed, or made up.

Because every agent calls the same server, they all work from the same version of the truth.

## Which database it uses

`data/campus_customs_new.db` — the working copy made in Problem 2, not the original
`campus_customs.db`. The original stays untouched so we always have a clean copy to start over from.

The server opens that file **read-only**. These three tools can look things up but cannot change
anything, spend money, or move stock.

You can point it somewhere else with the `CAMPUS_CUSTOMS_DB` environment variable — but set it in
the **client's** server config, not in your shell. An MCP client starts this server as a subprocess
and does not pass your shell environment through, so an exported variable is silently ignored and the
tools quietly use the default database instead. Use the `env` block in `.mcp.json`, or the `env=`
argument to a FastMCP `StdioTransport`.

### One tool writes

Seven of the eight tools only read. `record_payment` changes the database: it records a payment,
reduces the account balance, and marks an invoice paid. It refuses to run without a named human
approver, and refuses to overdraw the account or pay the same bill twice.

## The three tools, in plain terms

### `check_stock`
**"Do we actually have this, in this size, right now?"**

You give it a product code and (optionally) a size. It tells you how many are sitting on the shelf
and which aisle they're in. Sizes are counted separately, so a shirt can be available in medium and
completely gone in small — this is how an agent avoids promising a customer something the shop
doesn't have.

### `get_rent_due_and_cash_position`
**"What rent do we owe, when is it due, and what money is genuinely free to pay it?"**

It returns the shop's rent, the date it's due, how many days away that is, the money in the bank —
and the unpaid bills that already have a claim on that money. All in one answer.

The unpaid bills matter. If you only subtract rent from the bank balance, the shop looks like it has
far more spare cash than it does, because a supplier is already waiting to be paid out of the same
account. This tool subtracts everything, so the number it calls "available" is a number an agent can
actually spend.

### `get_price_and_floor`
**"What do we sell this for, and how cheap could we go before we lose money?"**

It returns what the shop paid for an item and what it charges for it. That first number is the floor:
sell below it and the shop loses money on every single unit. If you also tell it how many units
someone wants, it works out what that order is worth and the biggest total discount that still breaks
even. This is what lets an agent consider a bulk discount responsibly instead of inventing one.

## Running it

The server is registered with this project in `.mcp.json` at the project root, so Claude Code starts
it automatically and the three tools become callable. That config pins an **absolute** path to the
Python interpreter on purpose: a bare `python3` resolves to the system Python when a launcher starts
the server with a minimal `PATH`, and the system Python does not have `fastmcp` installed, so the
server would fail to start.

To install the dependency or start it by hand:

```bash
pip install -r mcp_server/requirements.txt
python3 mcp_server/server.py
```

To check that all three tools work and that their answers match the database:

```bash
python3 mcp_server/smoke_test.py
```

That connects as a real MCP client over stdio, calls each tool with the arguments the three open
tickets imply, compares every field against the raw database values, and writes the evidence to
`output/mcp_smoke.json`.

Built with [FastMCP](https://github.com/jlowin/fastmcp), the standalone `fastmcp` package (v4+).
Note that it has to be that package: MCP Python SDK v2 renamed its own bundled FastMCP class to
`MCPServer`, so `from mcp.server.fastmcp import FastMCP` no longer resolves.
