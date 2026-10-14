"""Direct database access for the API itself.

Deliberately separate from the MCP server. The MCP tools exist so that *agents*
can read the shop's data through a model; these functions exist so the dashboard
can read it without one. Putting a balance lookup through an LLM would be slow,
costly and less reliable than a SELECT.

Both point at the same file: `data/campus_customs_new.db`, the working copy.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRISTINE_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"


def _ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{WORKING_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rw() -> sqlite3.Connection:
    conn = sqlite3.connect(str(WORKING_DB))
    conn.row_factory = sqlite3.Row
    return conn


def desk_date() -> str:
    with closing(_ro()) as conn:
        row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else ""


def tickets() -> list[dict[str, Any]]:
    """Every ticket, with an explicit open/resolved flag for the board."""
    with closing(_ro()) as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, "
            "invoice_id, status, notes, created_at FROM tickets ORDER BY id"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["open"] = r["status"] == "open"
        d["resolved"] = r["status"] != "open"
        out.append(d)
    return out


def ticket(ticket_id: int) -> dict[str, Any] | None:
    with closing(_ro()) as conn:
        row = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, "
            "invoice_id, status, notes, created_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["open"] = row["status"] == "open"
    d["resolved"] = row["status"] != "open"
    return d


def set_ticket_status(ticket_id: int, status: str) -> bool:
    """Mark a ticket resolved (or back to open). Returns whether a row changed."""
    with closing(_rw()) as conn:
        cur = conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id)
        )
        conn.commit()
    return cur.rowcount > 0


def cash() -> dict[str, Any]:
    """The checking balance, with what is already committed against it."""
    with closing(_ro()) as conn:
        accounts = [dict(r) for r in conn.execute(
            "SELECT name, balance, date FROM cash_accounts ORDER BY name"
        ).fetchall()]
        # Rent already paid is no longer owed. `leases` has no paid flag, so the
        # only record of a settled lease is a row in `payments`; without this
        # the till keeps counting rent after it has gone out and reports a
        # negative available balance.
        rent = conn.execute(
            "SELECT COALESCE(SUM(l.monthly_rent),0) t FROM leases l "
            "WHERE NOT EXISTS (SELECT 1 FROM payments p "
            "WHERE p.kind = 'rent' AND p.ref_id = l.id)"
        ).fetchone()["t"]
        owed = conn.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM invoices WHERE status != 'paid'"
        ).fetchone()["t"]
        payments = [dict(r) for r in conn.execute(
            "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
            "FROM payments ORDER BY id DESC LIMIT 20"
        ).fetchall()]

    checking = next((a for a in accounts if a["name"] == "checking"), None)
    total = sum(a["balance"] for a in accounts)
    return {
        "as_of": desk_date(),
        "checking_balance": checking["balance"] if checking else None,
        "accounts": accounts,
        "rent_total": round(rent, 2),
        "open_invoices_total": round(owed, 2),
        "total_committed": round(rent + owed, 2),
        "available_after_all_commitments": round(total - rent - owed, 2),
        "payments": payments,
    }


def reset() -> dict[str, Any]:
    """Copy the pristine original over the working copy.

    This is the undo button for a demo: every payment, every balance change and
    every resolved ticket goes back to how the seed data shipped.
    """
    if not PRISTINE_DB.exists():
        raise FileNotFoundError(f"Original database missing at {PRISTINE_DB}")
    shutil.copyfile(PRISTINE_DB, WORKING_DB)
    return {
        "reset": True,
        "restored_from": PRISTINE_DB.name,
        "restored_to": WORKING_DB.name,
        "cash": cash(),
        "tickets": tickets(),
    }
