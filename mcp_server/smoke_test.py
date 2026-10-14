"""Smoke-test the campus-customs MCP server.

Launches `mcp_server/server.py` over stdio as a real MCP client, calls all three
tools with the arguments the three open tickets imply, checks every returned field
against the raw values in `data/campus_customs_new.db`, and writes the evidence to
`output/mcp_smoke.json`.

Run with:  python3 mcp_server/smoke_test.py
"""
import asyncio, json, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs_new.db"

CASES = [
    {
        "ticket": 101,
        "prompt": "Ticket 101 - Tauhid Zaman wants one Classic Bulldog Tee "
                  "(CC-TEE-WHITE) in size S. Do we have one on the shelf right now?",
        "tool": "check_stock",
        "arguments": {"sku": "CC-TEE-WHITE", "size": "S"},
    },
    {
        "ticket": 102,
        "prompt": "Ticket 102 - Elm City Properties says the shop rent is due. How much "
                  "is it, when is it due, and how much cash is actually free once "
                  "everything we already owe is taken into account?",
        "tool": "get_rent_due_and_cash_position",
        "arguments": {"lease_id": 1},
    },
    {
        "ticket": 103,
        "prompt": "Ticket 103 - The Yale AI Club wants 20 Basic Hoodie Big Yale "
                  "(CC-HOOD-NAVY) in size M and is asking for a bulk discount. What do "
                  "we sell them for, and how far down can the price go before the shop "
                  "loses money on the order?",
        "tool": "get_price_and_floor",
        "arguments": {"sku": "CC-HOOD-NAVY", "quantity": 20},
    },
]


def db_rows(sql, params=()):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# The raw database values each tool's output has to agree with.
def expectations():
    return {
        "check_stock": {
            "source_query": "SELECT sku, name, size, qty, location FROM inventory "
                            "WHERE sku='CC-TEE-WHITE' AND size='S'",
            "rows": db_rows("SELECT sku, name, size, qty, location FROM inventory "
                            "WHERE sku=? AND size=?", ("CC-TEE-WHITE", "S")),
        },
        "get_rent_due_and_cash_position": {
            "source_query": "leases(id=1) + desk.date_today + cash_accounts + "
                            "invoices WHERE status!='paid'",
            "lease": db_rows("SELECT id, space_name, landlord, monthly_rent, next_due "
                             "FROM leases WHERE id=1"),
            "desk_date_today": db_rows("SELECT date_today FROM desk LIMIT 1"),
            "cash_accounts": db_rows("SELECT name, balance, date FROM cash_accounts"),
            "unpaid_invoices": db_rows("SELECT id, vendor_id, amount, due_date, status "
                                       "FROM invoices WHERE status!='paid' ORDER BY due_date"),
            "rent_already_paid": bool(db_rows(
                "SELECT 1 FROM payments WHERE kind='rent' AND ref_id=1")),
        },
        "get_price_and_floor": {
            "source_query": "SELECT sku, unit_cost, list_price FROM pricing "
                            "WHERE sku='CC-HOOD-NAVY'",
            "rows": db_rows("SELECT sku, unit_cost, list_price FROM pricing WHERE sku=?",
                            ("CC-HOOD-NAVY",)),
        },
    }



def checks_101(out, exp):
    row = exp["rows"][0]
    o = out["rows"][0]
    return [
        ("name", out["name"], row["name"]),
        ("rows[0].size", o["size"], row["size"]),
        ("rows[0].qty", o["qty"], row["qty"]),
        ("rows[0].location", o["location"], row["location"]),
        ("rows[0].in_stock", o["in_stock"], row["qty"] > 0),
        ("total_qty", out["total_qty"], row["qty"]),
    ]


def checks_102(out, exp):
    """Checks for the rent-and-cash tool.

    Derives the expected obligations from live state rather than assuming any:
    once rent is paid it is no longer owed, and once every invoice is settled
    there are no open ones to check.
    """
    from datetime import date

    lease, cash = exp["lease"][0], exp["cash_accounts"][0]
    bal = cash["balance"]
    today = exp["desk_date_today"][0]["date_today"]
    d = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days

    rent = 0.0 if exp["rent_already_paid"] else lease["monthly_rent"]
    amt = sum(i["amount"] for i in exp["unpaid_invoices"])

    rows = [
        ("as_of", out["as_of"], today),
        ("leases[0].monthly_rent", out["leases"][0]["monthly_rent"], lease["monthly_rent"]),
        ("leases[0].next_due", out["leases"][0]["next_due"], lease["next_due"]),
        ("leases[0].days_until_due", out["leases"][0]["days_until_due"], d),
        ("cash_total", out["cash_total"], bal),
        ("open_invoices count", len(out["open_invoices"]), len(exp["unpaid_invoices"])),
        ("obligations.rent_total", out["obligations"]["rent_total"], rent),
        ("obligations.open_invoices_total", out["obligations"]["open_invoices_total"], amt),
        ("obligations.total_committed", out["obligations"]["total_committed"], rent + amt),
        ("cash_available_after_all_commitments",
         out["cash_available_after_all_commitments"], round(bal - rent - amt, 2)),
        ("all_commitments_covered_by_cash",
         out["all_commitments_covered_by_cash"], bal >= rent + amt),
    ]
    for n, inv in enumerate(exp["unpaid_invoices"]):
        di = (date.fromisoformat(inv["due_date"]) - date.fromisoformat(today)).days
        rows += [
            (f"open_invoices[{n}].invoice_id", out["open_invoices"][n]["invoice_id"], inv["id"]),
            (f"open_invoices[{n}].amount", out["open_invoices"][n]["amount"], inv["amount"]),
            (f"open_invoices[{n}].days_until_due",
             out["open_invoices"][n]["days_until_due"], di),
            (f"open_invoices[{n}].overdue", out["open_invoices"][n]["overdue"], di < 0),
        ]
    return rows


def checks_103(out, exp):
    row = exp["rows"][0]
    cost, lst, q = row["unit_cost"], row["list_price"], 20
    return [
        ("unit_cost", out["unit_cost"], cost),
        ("list_price", out["list_price"], lst),
        ("price_floor", out["price_floor"], cost),
        ("margin_per_unit", out["margin_per_unit"], lst - cost),
        ("total_at_list", out["total_at_list"], lst * q),
        ("total_at_cost", out["total_at_cost"], cost * q),
        ("max_total_discount", out["max_total_discount"], (lst - cost) * q),
    ]


CHECKS = {101: checks_101, 102: checks_102, 103: checks_103}


def build_checks(ticket, out, exp):
    return [
        {"field": f, "tool_output_value": tv, "database_value": dv, "match": tv == dv}
        for f, tv, dv in CHECKS[ticket](out, exp)
    ]


def unwrap(result):
    for attr in ("data", "structured_content"):
        val = getattr(result, attr, None)
        if val is not None:
            return val
    content = getattr(result, "content", None)
    if content:
        return json.loads(content[0].text)
    return None


async def main():
    exp = expectations()
    client = Client(str(ROOT / "mcp_server" / "server.py"))
    async with client:
        listed = await client.list_tools()
        tool_names = sorted(t.name for t in listed)
        results = []
        for case in CASES:
            res = await client.call_tool(case["tool"], case["arguments"])
            out = unwrap(res)
            e = exp[case["tool"]]
            verified = build_checks(case["ticket"], out, e)
            results.append({**case, "tool_output": out, "database_values": e,
                            "verification": {
                                "fields_checked": len(verified),
                                "all_match": all(c["match"] for c in verified),
                                "checks": verified}})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "server": "campus-customs",
        "transport": "stdio (fastmcp Client -> mcp_server/server.py)",
        "config_file": ".mcp.json",
        "database": "data/campus_customs_new.db",
        "tools_advertised_by_server": tool_names,
        "all_tools_match_database": all(r["verification"]["all_match"] for r in results),
        "tests": results,
    }
    out = ROOT / "output" / "mcp_smoke.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("tools advertised:", tool_names)
    print("wrote", out)
    for r in results:
        v = r["verification"]
        print(f"  ticket {r['ticket']:>3}  {r['tool']:<32} "
              f"{v['fields_checked']} fields checked -> "
              f"{'ALL MATCH' if v['all_match'] else 'MISMATCH'}")

asyncio.run(main())
