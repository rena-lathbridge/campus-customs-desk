"""Pending payments, and the one code path that actually spends money.

The split this module exists to enforce: **agents prepare, humans approve, this
module pays.** When the team finishes a ticket and its decision involves money,
a `Pending` approval is parked here. Nothing has moved yet. Only when a person
hits approve does `approve()` run, and only then does cash change.

The spending itself still goes through the MCP server's `record_payment` tool
rather than a SQL statement written here, so every guard that tool enforces —
named approver, no overdraw, no double payment, one transaction across payments,
cash_accounts and invoices — applies to the dashboard exactly as it applies to an
agent. There is one way to spend money in this project, and this is a caller of
it, not a second one.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import events
from db import WORKING_DB

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = PROJECT_ROOT / "mcp_server" / "server.py"

_ids = itertools.count(1)
_lock = threading.Lock()
_pending: dict[int, "Pending"] = {}


@dataclass
class Pending:
    id: int
    run_id: str
    ticket_id: int | None
    kind: str
    ref_id: int | None
    amount: float
    account: str
    what: str
    created_at: str
    status: str = "awaiting_approval"  # or approved / declined / failed
    decided_by: str = ""
    decided_at: str = ""
    result: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def propose(
    *, run_id: str, ticket_id: int | None, kind: str, ref_id: int | None,
    amount: float, account: str, what: str,
) -> Pending:
    """Park a payment the team recommended. Moves no money."""
    with _lock:
        p = Pending(
            id=next(_ids), run_id=run_id, ticket_id=ticket_id, kind=kind,
            ref_id=ref_id, amount=round(float(amount), 2), account=account or "checking",
            what=what, created_at=_now(),
        )
        _pending[p.id] = p
    events.record(
        "decision", agent="boss", summary=f"Payment proposed, awaiting a human: {what}",
        detail=p.as_dict(), run_id=run_id, ticket_id=ticket_id,
    )
    return p


def get(approval_id: int) -> Pending | None:
    with _lock:
        return _pending.get(approval_id)


def listing(status: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        rows = sorted(_pending.values(), key=lambda p: p.id)
    return [p.as_dict() for p in rows if status is None or p.status == status]


async def _call_record_payment(args: dict[str, Any]) -> dict[str, Any]:
    """Spend, by calling the MCP server's one writing tool."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER)],
        # The server does NOT inherit this process's environment, so the database
        # path has to be handed over explicitly or the tool writes to its default.
        env={"CAMPUS_CUSTOMS_DB": str(WORKING_DB)},
    )
    async with Client(transport) as client:
        res = await client.call_tool("record_payment", args)
        if res.data is not None:
            return res.data
        return json.loads(res.content[0].text)


async def approve(approval_id: int, approved_by: str) -> dict[str, Any]:
    """Execute a parked payment. This is the moment cash actually changes."""
    p = get(approval_id)
    if p is None:
        return {"ok": False, "error": f"No approval with id {approval_id}."}
    if p.status != "awaiting_approval":
        return {"ok": False, "error": f"Approval {approval_id} is already {p.status}."}
    if not approved_by or not approved_by.strip():
        return {"ok": False, "error": "approved_by is required to approve a payment."}

    result = await _call_record_payment({
        "kind": p.kind, "amount": p.amount, "account": p.account,
        "approved_by": approved_by.strip(), "ref_id": p.ref_id,
    })

    recorded = bool(result.get("recorded"))
    with _lock:
        p.status = "approved" if recorded else "failed"
        p.decided_by = approved_by.strip()
        p.decided_at = _now()
        p.result = result

    events.record(
        "approval",
        agent="human",
        summary=(
            f"{approved_by.strip()} approved ${p.amount:,.2f} — {p.what}. "
            f"New balance ${result.get('new_balance', '?')}."
            if recorded
            else f"Payment refused: {result.get('reason', 'unknown reason')}"
        ),
        detail={"approval": p.as_dict(), "tool_result": result},
        run_id=p.run_id, ticket_id=p.ticket_id,
    )
    return {"ok": recorded, "approval": p.as_dict(), "payment": result}


def decline(approval_id: int, declined_by: str, reason: str = "") -> dict[str, Any]:
    """Reject a parked payment. Moves no money, and cannot be undone."""
    p = get(approval_id)
    if p is None:
        return {"ok": False, "error": f"No approval with id {approval_id}."}
    if p.status != "awaiting_approval":
        return {"ok": False, "error": f"Approval {approval_id} is already {p.status}."}
    with _lock:
        p.status = "declined"
        p.decided_by = declined_by.strip()
        p.decided_at = _now()
        p.result = {"declined": True, "reason": reason}
    events.record(
        "approval", agent="human",
        summary=f"{declined_by.strip()} declined ${p.amount:,.2f} — {p.what}."
                + (f" Reason: {reason}" if reason else ""),
        detail=p.as_dict(), run_id=p.run_id, ticket_id=p.ticket_id,
    )
    return {"ok": True, "approval": p.as_dict()}


def clear() -> None:
    """Drop every parked approval. Used by the reset route."""
    with _lock:
        _pending.clear()
