"""MCP server for the Campus Customs back office.

Exposes the shop's operational database as MCP tools so that every agent in this
assignment reads the same facts from the same place. Every value a tool returns is
either read straight out of `data/campus_customs_new.db` or is plain arithmetic on
values read from it; nothing is invented.

The database is opened read-only. These three tools answer questions; they do not
spend money or move stock.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Default to the working copy made in Problem 2, never the pristine original.
#
# WARNING about CAMPUS_CUSTOMS_DB: an MCP client launches this server as a
# subprocess and does NOT necessarily pass your shell's environment through.
# Exporting CAMPUS_CUSTOMS_DB in a terminal and then connecting a client will
# silently have no effect here, and the tools will read and write the default
# database instead. To point the server somewhere else, set the variable in the
# client's own server config (the `env` block in .mcp.json, or the `env=`
# argument to a FastMCP StdioTransport) rather than in your shell.
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(
    os.environ.get("CAMPUS_CUSTOMS_DB", REPO_ROOT / "data" / "campus_customs_new.db")
)

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    """Open the shop database read-only, with rows that behave like dicts."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw() -> sqlite3.Connection:
    """Open the shop database for writing. Only `record_payment` uses this."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _desk_date() -> str:
    """Return `desk.date_today` — the date this shop's world is frozen at."""
    with closing(_connect()) as conn:
        row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else ""


def _days_until(target: str, as_of: str) -> int | None:
    """Whole days from `as_of` to `target`; negative means `target` is in the past."""
    try:
        return (date.fromisoformat(target) - date.fromisoformat(as_of)).days
    except ValueError:
        return None


@mcp.tool()
def check_stock(sku: str, size: str | None = None) -> dict[str, Any]:
    """Check how many units of a product are physically on the shelf right now.

    Reads the `inventory` table, which is keyed on (sku, size) — stock is counted
    separately for every size, so a product can be in stock in one size and sold
    out in another.

    Args:
        sku: Product code, e.g. "CC-TEE-WHITE".
        size: Optional size, e.g. "S", "M", "L", "XL", or "OS" for one-size items.
            Omit it to get every size carried for this sku.

    Returns:
        The matching inventory rows (size, qty, location), the product name, and
        the total units across the sizes returned. `found` is False when the
        database has no row for that sku/size.
    """
    sql = "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?"
    params: list[Any] = [sku]
    if size is not None:
        sql += " AND size = ?"
        params.append(size)
    sql += " ORDER BY size"

    with closing(_connect()) as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        return {
            "sku": sku,
            "size": size,
            "found": False,
            "rows": [],
            "total_qty": 0,
            "note": "No row exists in the inventory table for that sku/size.",
        }

    return {
        "sku": sku,
        "name": rows[0]["name"],
        "size": size,
        "found": True,
        "rows": [
            {
                "size": r["size"],
                "qty": r["qty"],
                "location": r["location"],
                "in_stock": r["qty"] > 0,
            }
            for r in rows
        ],
        "total_qty": sum(r["qty"] for r in rows),
    }


@mcp.tool()
def get_rent_due_and_cash_position(lease_id: int | None = None) -> dict[str, Any]:
    """Look up what rent is owed and when, against the money actually available.

    Reads the `leases` table for the rent amount and due date, `desk.date_today` to
    work out how many days are left, `cash_accounts` for the bank balance, and the
    open rows of `invoices` (joined to `vendors` for the supplier name) for money
    already promised to someone else.

    Open invoices are included on purpose. Cash minus rent alone overstates what is
    really free to spend, because unpaid bills have a prior claim on the same money.

    Args:
        lease_id: Which lease to report on, e.g. 1. Omit it to get every lease.

    Returns:
        The requested lease(s) with rent, due date and days remaining (negative if
        the date has passed); every cash account; every open invoice; and a cash
        position that nets total cash against *all* commitments, not just rent.
    """
    as_of = _desk_date()

    lease_sql = (
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases"
    )
    params: list[Any] = []
    if lease_id is not None:
        lease_sql += " WHERE id = ?"
        params.append(lease_id)
    lease_sql += " ORDER BY id"

    with closing(_connect()) as conn:
        lease_rows = conn.execute(lease_sql, params).fetchall()
        # Obligations are always totalled across every lease and every open
        # invoice, even when the caller filtered the display to one lease --
        # filtering the arithmetic would reintroduce the overstatement.
        # A lease whose rent has already been paid is not still owed. `leases`
        # has no paid flag, so a matching row in `payments` is the only record.
        all_rent_rows = conn.execute(
            "SELECT l.monthly_rent FROM leases l WHERE NOT EXISTS ("
            "SELECT 1 FROM payments p WHERE p.kind = 'rent' AND p.ref_id = l.id)"
        ).fetchall()
        cash_rows = conn.execute(
            "SELECT name, balance, date FROM cash_accounts ORDER BY name"
        ).fetchall()
        invoice_rows = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, "
            "i.status, i.description FROM invoices i "
            "LEFT JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.status != 'paid' ORDER BY i.due_date"
        ).fetchall()

    with closing(_connect()) as conn:
        paid_lease_ids = {
            r["ref_id"] for r in conn.execute(
                "SELECT ref_id FROM payments WHERE kind = 'rent' AND ref_id IS NOT NULL")
        }

    leases = [
        {
            "lease_id": r["id"],
            "space_name": r["space_name"],
            "landlord": r["landlord"],
            "monthly_rent": r["monthly_rent"],
            "next_due": r["next_due"],
            "days_until_due": _days_until(r["next_due"], as_of),
            "notes": r["notes"],
            "already_paid": bool(paid_lease_ids and r["id"] in paid_lease_ids),
        }
        for r in lease_rows
    ]
    accounts = [
        {"account": r["name"], "balance": r["balance"], "as_of": r["date"]}
        for r in cash_rows
    ]
    open_invoices = []
    for r in invoice_rows:
        days = _days_until(r["due_date"], as_of)
        open_invoices.append(
            {
                "invoice_id": r["id"],
                "vendor_id": r["vendor_id"],
                "vendor_name": r["vendor_name"],
                "amount": r["amount"],
                "due_date": r["due_date"],
                "days_until_due": days,
                "overdue": days is not None and days < 0,
                "status": r["status"],
                "description": r["description"],
            }
        )

    rent_total = sum(r["monthly_rent"] for r in all_rent_rows)
    invoices_total = sum(i["amount"] for i in open_invoices)
    committed_total = rent_total + invoices_total
    cash_total = sum(a["balance"] for a in accounts)

    return {
        "as_of": as_of,
        "leases": leases,
        "cash_accounts": accounts,
        "open_invoices": open_invoices,
        "cash_total": round(cash_total, 2),
        "obligations": {
            "rent_total": round(rent_total, 2),
            "open_invoices_total": round(invoices_total, 2),
            "total_committed": round(committed_total, 2),
        },
        "cash_available_after_all_commitments": round(cash_total - committed_total, 2),
        "all_commitments_covered_by_cash": cash_total >= committed_total,
    }


@mcp.tool()
def get_price_and_floor(sku: str, quantity: int | None = None) -> dict[str, Any]:
    """Get a product's selling price and the cost floor a discount must stay above.

    Reads the `pricing` table, which holds one row per sku: `unit_cost` (what the
    shop paid) and `list_price` (what it sells for). `unit_cost` is the floor — a
    discount below it loses money on every unit sold.

    Args:
        sku: Product code, e.g. "CC-HOOD-NAVY".
        quantity: Optional order size. Supply it to also get the totals for an
            order of that many units.

    Returns:
        The unit cost (the floor), the list price, the per-unit margin, and — when
        a quantity is given — the order's revenue at list, its cost, and the
        largest total discount that still clears cost. Every figure is either read
        from `pricing` or multiplied out from those two numbers.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()

    if row is None:
        return {
            "sku": sku,
            "found": False,
            "note": "No row exists in the pricing table for that sku.",
        }

    unit_cost = row["unit_cost"]
    list_price = row["list_price"]

    result: dict[str, Any] = {
        "sku": row["sku"],
        "found": True,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "margin_per_unit": round(list_price - unit_cost, 2),
        "price_floor": unit_cost,
        "floor_note": (
            "unit_cost is the break-even price; any unit price below it sells at a loss."
        ),
    }

    if quantity is not None:
        result["quantity"] = quantity
        result["total_at_list"] = round(list_price * quantity, 2)
        result["total_at_cost"] = round(unit_cost * quantity, 2)
        result["max_total_discount"] = round((list_price - unit_cost) * quantity, 2)

    return result


@mcp.tool()
def list_tickets(status: str | None = "open") -> dict[str, Any]:
    """List the requests sitting in the shop's inbox.

    Reads the `tickets` table. Each ticket carries only the columns its `type`
    needs, so `sku`/`size`/`qty` are filled in for product requests and null for a
    rent notice, while `lease_id` and `invoice_id` point at the rows that explain
    what the ticket is really about.

    Args:
        status: Filter by status, e.g. "open". Pass null to list every ticket.

    Returns:
        The matching tickets, oldest first, with their raw columns plus the
        `links` each one carries into other tables.
    """
    sql = (
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
        "status, notes, created_at FROM tickets"
    )
    params: list[Any] = []
    if status is not None:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY created_at, id"

    with closing(_connect()) as conn:
        rows = conn.execute(sql, params).fetchall()

    tickets = []
    for r in rows:
        d = dict(r)
        d["links"] = {
            "inventory": {"sku": r["sku"], "size": r["size"]} if r["sku"] else None,
            "pricing": {"sku": r["sku"]} if r["sku"] else None,
            "leases": {"lease_id": r["lease_id"]} if r["lease_id"] else None,
            "invoices": {"invoice_id": r["invoice_id"]} if r["invoice_id"] else None,
        }
        tickets.append(d)

    return {"status_filter": status, "count": len(tickets), "tickets": tickets}


@mcp.tool()
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Pull one request out of the inbox by its number.

    Reads a single row of `tickets`. Use this when an agent has been handed a
    ticket number and needs the exact sku, size, quantity, lease or invoice that
    ticket points at, rather than working from a summary someone typed.

    Args:
        ticket_id: The ticket number, e.g. 101.

    Returns:
        The ticket's raw columns and the links it carries into other tables, or
        `found: false` when no such ticket exists.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, "
            "invoice_id, status, notes, created_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    if row is None:
        return {
            "ticket_id": ticket_id,
            "found": False,
            "note": "No row exists in the tickets table with that id.",
        }

    d = dict(row)
    d["found"] = True
    d["links"] = {
        "inventory": {"sku": row["sku"], "size": row["size"]} if row["sku"] else None,
        "pricing": {"sku": row["sku"]} if row["sku"] else None,
        "leases": {"lease_id": row["lease_id"]} if row["lease_id"] else None,
        "invoices": {"invoice_id": row["invoice_id"]} if row["invoice_id"] else None,
    }
    return d


@mcp.tool()
def list_vendors() -> dict[str, Any]:
    """List the suppliers the shop can order from and how long each one takes.

    Reads the `vendors` table: each row's `specialty` says in words what that
    supplier handles, and `lead_days` says how many days an order takes to arrive.

    Important: the database does **not** record which vendor supplies which sku.
    The only recorded vendor-to-product link anywhere is through an existing row
    in `invoices` (its `description` names what was ordered). So do not state as
    fact that a given vendor stocks a given product — say which specialty looks
    like a match and that it would need confirming.

    Returns:
        Every vendor with its specialty and lead time, plus a note restating that
        no sku-to-vendor mapping exists in this database.
    """
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"
        ).fetchall()

    return {
        "vendors": [dict(r) for r in rows],
        "sku_to_vendor_mapping_exists": False,
        "note": (
            "No table maps a sku to a vendor. Match on the `specialty` wording and "
            "flag it as an inference, or cite an existing invoice that names the item."
        ),
    }


@mcp.tool()
def list_open_invoices() -> dict[str, Any]:
    """List the bills the shop still owes, with who they're owed to.

    Reads every row of `invoices` whose `status` is not "paid", joined to
    `vendors` for the supplier's name and lead time, and compares each `due_date`
    against `desk.date_today` so overdue bills are flagged rather than left for
    the reader to work out.

    Returns:
        Each unpaid invoice with its amount, due date, days until due (negative
        when overdue), the vendor behind it, and the total owed.
    """
    as_of = _desk_date()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.lead_days, i.amount, "
            "i.due_date, i.status, i.description FROM invoices i "
            "LEFT JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.status != 'paid' ORDER BY i.due_date"
        ).fetchall()

    invoices = []
    for r in rows:
        days = _days_until(r["due_date"], as_of)
        invoices.append(
            {
                "invoice_id": r["id"],
                "vendor_id": r["vendor_id"],
                "vendor_name": r["vendor_name"],
                "vendor_lead_days": r["lead_days"],
                "amount": r["amount"],
                "due_date": r["due_date"],
                "days_until_due": days,
                "overdue": days is not None and days < 0,
                "status": r["status"],
                "description": r["description"],
            }
        )

    return {
        "as_of": as_of,
        "count": len(invoices),
        "total_owed": round(sum(i["amount"] for i in invoices), 2),
        "invoices": invoices,
    }


@mcp.tool()
def record_payment(
    kind: str,
    amount: float,
    account: str,
    approved_by: str,
    ref_id: int | None = None,
) -> dict[str, Any]:
    """Pay a bill: write it to the books and take the money out of the account.

    This is the only tool here that changes the database. In one transaction it
    inserts a row into `payments`, reduces that account's `balance` in
    `cash_accounts`, and — when `kind` is "invoice" — sets that invoice's `status`
    to "paid" so the same bill is never counted as owed twice.

    It refuses, without writing anything, when: `approved_by` is blank (the
    `payments.approved_by` column exists because a human signs off on spending);
    the account does not exist; the amount is not positive; the payment would
    overdraw the account; or `kind` is "invoice" and that invoice is missing or
    already paid.

    Args:
        kind: What is being paid — "invoice" or "rent".
        amount: Amount in dollars. Must be positive.
        account: Which account to pay from, e.g. "checking".
        approved_by: Name of the person approving this. Required, cannot be blank.
        ref_id: The invoice id when kind is "invoice", or the lease id when kind
            is "rent".

    Returns:
        On success, the payment id, the account's new balance and what changed.
        On refusal, `recorded: false` and a `reason` saying which rule stopped it.
    """
    def refuse(reason: str) -> dict[str, Any]:
        return {"recorded": False, "reason": reason}

    if not approved_by or not approved_by.strip():
        return refuse(
            "approved_by is required: no payment is written without a named approver."
        )
    if amount is None or amount <= 0:
        return refuse("amount must be a positive number of dollars.")
    if kind not in {"invoice", "rent"}:
        return refuse("kind must be either 'invoice' or 'rent'.")
    if kind == "invoice" and ref_id is None:
        return refuse("kind 'invoice' requires ref_id to be the invoice id.")

    paid_at = _desk_date()

    with closing(_connect_rw()) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")

            acct = conn.execute(
                "SELECT name, balance FROM cash_accounts WHERE name = ?", (account,)
            ).fetchone()
            if acct is None:
                conn.rollback()
                return refuse(f"No account named {account!r} exists in cash_accounts.")
            if acct["balance"] < amount:
                conn.rollback()
                return refuse(
                    f"Payment of {amount} would overdraw {account!r}, which holds "
                    f"{acct['balance']}."
                )

            invoice_marked_paid = None
            if kind == "invoice":
                inv = conn.execute(
                    "SELECT id, amount, status FROM invoices WHERE id = ?", (ref_id,)
                ).fetchone()
                if inv is None:
                    conn.rollback()
                    return refuse(f"No invoice with id {ref_id} exists.")
                if inv["status"] == "paid":
                    conn.rollback()
                    return refuse(f"Invoice {ref_id} is already marked paid.")
                conn.execute(
                    "UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,)
                )
                invoice_marked_paid = ref_id

            cur = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, "
                "approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                (kind, ref_id, amount, account, paid_at, approved_by.strip()),
            )
            new_balance = round(acct["balance"] - amount, 2)
            conn.execute(
                "UPDATE cash_accounts SET balance = ? WHERE name = ?",
                (new_balance, account),
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            return refuse(f"Database error, nothing was written: {exc}")

    return {
        "recorded": True,
        "payment_id": cur.lastrowid,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "paid_at": paid_at,
        "approved_by": approved_by.strip(),
        "new_balance": new_balance,
        "invoice_marked_paid": invoice_marked_paid,
    }


if __name__ == "__main__":
    mcp.run()
