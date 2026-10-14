"""FastAPI backend for the Campus Customs desk dashboard.

Start it from the `backend/` folder:

    uvicorn main:app --reload --port 8000

What this server is for: the React board shows the three open tickets, lets a
person run the agent team on one, watches the agents work, and then approves or
declines any spending the team recommends.

The rule the routes are built around is that **agents prepare and humans pay**.
The team runs with no named approver, the MCP `record_payment` tool is blocked
for agents at the toolset level, and the only code path that moves money is
`POST /api/approvals/{id}/approve`.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import approvals
import db
import events
from config import MAX_DELEGATION_DEPTH, MODEL_NAME, AgentNotConfigured
from models import TEAM

app = FastAPI(
    title="Campus Customs desk",
    description="Backend for the ticket board: tickets, agent runs, events, "
                "approvals, cash and reset.",
    version="1.0.0",
)

#: The last decision the team reached on each ticket, so the board can still
#: show "what each agent did" after a page reload instead of going blank.
_last_run: dict[int, dict[str, Any]] = {}

# The dashboard is served by Vite on port 5173 in development, so that is the
# origin the browser is allowed to call these routes from.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    instruction: str = Field(default="", description="Optional extra steer from a human.")
    max_depth: int = Field(default=MAX_DELEGATION_DEPTH, ge=1, le=5)


class ApproveRequest(BaseModel):
    approved_by: str = Field(description="Name of the person approving. Required.")


class DeclineRequest(BaseModel):
    declined_by: str = Field(description="Name of the person declining. Required.")
    reason: str = Field(default="")


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Is the server up, and what is it configured with."""
    return {
        "ok": True,
        "model": MODEL_NAME,
        "team": list(TEAM),
        "database": db.WORKING_DB.name,
        "shop_date": db.desk_date(),
    }


@app.get("/api/tickets")
def list_tickets() -> dict[str, Any]:
    """The three tickets, each flagged open or resolved."""
    rows = db.tickets()
    return {
        "shop_date": db.desk_date(),
        "count": len(rows),
        "open": sum(1 for t in rows if t["open"]),
        "resolved": sum(1 for t in rows if t["resolved"]),
        "tickets": rows,
    }


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """One ticket, with any approvals its runs have parked."""
    row = db.ticket(ticket_id)
    if row is None:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    row["approvals"] = [a for a in approvals.listing() if a["ticket_id"] == ticket_id]
    row["last_run"] = _last_run.get(ticket_id)
    return row


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int, body: RunRequest | None = None) -> dict[str, Any]:
    """Run the agent team on one ticket and return the Boss's decision.

    No approver is passed to the team, so nothing is paid here. If the decision
    involves money it comes back with `needs_human_approval` and a parked
    approval the board can show an approve button for.
    """
    if db.ticket(ticket_id) is None:
        raise HTTPException(404, f"No ticket {ticket_id}.")

    body = body or RunRequest()
    run_id = uuid.uuid4().hex[:8]
    token = events.current_run.set((run_id, ticket_id))
    events.record(
        "run_started", agent="boss",
        summary=f"Running the team on ticket {ticket_id}.",
        detail={"model": MODEL_NAME, "max_depth": body.max_depth},
    )

    try:
        from team import run_ticket as run_team

        decision = await run_team(
            ticket_id,
            instruction=body.instruction or None,
            approver="",  # agents prepare; they never pay
            max_depth=body.max_depth,
        )
    except AgentNotConfigured as exc:
        events.record("error", summary=str(exc))
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:  # surfaced to the board rather than swallowed
        events.record("error", summary=f"{type(exc).__name__}: {exc}")
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc
    finally:
        events.current_run.reset(token)

    events.record(
        "decision", agent="boss", summary=decision.decision[:400],
        detail=decision.model_dump(), run_id=run_id, ticket_id=ticket_id,
    )
    _last_run[ticket_id] = {"run_id": run_id, "decision": decision.model_dump()}

    parked = None
    money = decision.money
    if money and money.kind in {"invoice", "rent"} and money.amount > 0:
        parked = approvals.propose(
            run_id=run_id, ticket_id=ticket_id, kind=money.kind, ref_id=money.ref_id,
            amount=money.amount, account=money.account,
            what=money.what or decision.decision[:120],
        ).as_dict()
    elif not decision.needs_human_approval:
        # Nothing to approve and nothing to pay: the ticket is settled.
        db.set_ticket_status(ticket_id, "resolved")

    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "decision": decision.model_dump(),
        "awaiting_approval": parked,
        "ticket": db.ticket(ticket_id),
        "events_through": events.latest_seq(),
    }


@app.get("/api/events")
def recent_events(since: int = 0, limit: int = 200) -> dict[str, Any]:
    """Agent events since a sequence number: who spoke, and which tools they used.

    The board polls this with the `latest_seq` it last saw, so each refresh gets
    only what is new.
    """
    rows = events.since(since, limit)
    return {"since": since, "latest_seq": events.latest_seq(), "count": len(rows), "events": rows}


@app.get("/api/approvals")
def list_approvals(status: str | None = None) -> dict[str, Any]:
    """Payments the team has prepared, and what became of them."""
    rows = approvals.listing(status)
    return {"count": len(rows), "approvals": rows}


@app.post("/api/approvals/{approval_id}/approve")
async def approve_payment(approval_id: int, body: ApproveRequest) -> dict[str, Any]:
    """Approve a prepared payment. **This is the route that changes cash.**

    It calls the MCP server's `record_payment`, so every guard applies: a named
    approver, no overdraw, no paying a bill twice, and the payment row, the
    balance and the invoice status all move in one transaction.
    """
    result = await approvals.approve(approval_id, body.approved_by)
    if not result.get("ok"):
        detail = result.get("error") or result.get("payment", {}).get("reason", "refused")
        raise HTTPException(400, detail)

    parked = approvals.get(approval_id)
    if parked and parked.ticket_id is not None:
        db.set_ticket_status(parked.ticket_id, "resolved")

    return {**result, "cash": db.cash(), "ticket": db.ticket(parked.ticket_id) if parked else None}


@app.post("/api/approvals/{approval_id}/decline")
def decline_payment(approval_id: int, body: DeclineRequest) -> dict[str, Any]:
    """Decline a prepared payment. Moves no money; leaves the ticket open."""
    result = approvals.decline(approval_id, body.declined_by, body.reason)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "could not decline"))
    return result


@app.get("/api/cash")
def cash() -> dict[str, Any]:
    """The checking balance, plus what is already committed against it."""
    return db.cash()


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    """Put the database back to the original seed values for a fresh run.

    Copies the pristine `campus_customs.db` over the working copy, then clears
    the event log and any parked approvals so the board starts clean.
    """
    try:
        result = db.reset()
    except FileNotFoundError as exc:
        raise HTTPException(500, str(exc)) from exc
    approvals.clear()
    events.clear()
    _last_run.clear()
    events.record("reset", agent="human", summary="Database reset to the original seed values.")
    return result
