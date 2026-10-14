# Campus Customs — Agent Harness Notes

Working notes on `data/campus_customs.db` for the agents we're about to build.

- **Original file:** `data/campus_customs.db` (53,248 bytes)
- **Working copy:** `data/campus_customs_new.db` — byte-identical copy (same SHA-1, `f447ca6a…`). All
  agent writes should go to the copy so the original stays clean to re-test against.
- **"Today" in this world:** `2026-08-31`, read from the `desk` table. Every due date below is
  measured against that, not against the real calendar.

This is a **back-office database**, not the storefront one. There is no customer-facing catalogue,
no users, no product images. It's the stuff a small shop's manager deals with: what's on the shelf,
what it cost, who we owe, what's in the bank, and what people are asking us for.

---

## The tables

### `desk`
**Fields:** `date_today`, `notes`

The agent's calendar. One row, holding the date the whole scenario is frozen at.

> **Why it matters:** this is how the agent knows what "due in 2 days" or "overdue" actually means.
> Without it the agent would use the real date and get every deadline wrong.

---

### `inventory`
**Fields:** `sku`, `name`, `size`, `qty`, `location` — primary key is `(sku, size)`

What's physically on the shelves, counted separately for every size.

> **Why it matters:** this is the agent's honesty check. Before it promises anyone an item it has to
> look here, because the shop is out of two things right now and a wrong promise is a broken promise.

**What's actually in stock (10 rows, 4 products):**

| SKU | Name | S | M | L | XL | OS | Location |
|---|---|---|---|---|---|---|---|
| CC-HOOD-NAVY | Basic Hoodie Big Yale | 4 | 8 | 14 | 6 | — | Aisle A |
| CC-TEE-WHITE | Classic Bulldog Tee | **0** | 5 | 3 | 2 | — | Aisle B |
| CC-HAT-BLUE | Yale Cap | — | — | — | — | 40 | Aisle C |
| CC-MUG-CREST | Crest Mug | — | — | — | — | **0** | Aisle D |

Two zeros, and both matter: the sold-out tee in size S is exactly what a customer is waiting on.

---

### `pricing`
**Fields:** `sku`, `unit_cost`, `list_price`

What each item costs us and what we sell it for. One row per product, no size breakdown.

> **Why it matters:** this is the agent's floor. Any discount it considers has to stay above
> `unit_cost`, or the shop loses money on every item it sells.

| SKU | Unit cost | List price | Margin |
|---|---|---|---|
| CC-HOOD-NAVY | $22.00 | $58.00 | $36.00 (62%) |
| CC-TEE-WHITE | $8.00 | $28.00 | $20.00 (71%) |
| CC-HAT-BLUE | $6.00 | $22.00 | $16.00 (73%) |
| CC-MUG-CREST | $3.50 | $14.00 | $10.50 (75%) |

---

### `vendors`
**Fields:** `id`, `name`, `specialty`, `lead_days`

The suppliers we can call when we need more stock, and how long each one takes.

> **Why it matters:** when something's sold out, this tells the agent *how long* the fix takes, so it
> can give the customer a real date instead of a vague "soon".

| ID | Name | Specialty | Lead time |
|---|---|---|---|
| 1 | Bulldog Print Co | apparel reprint | 5 days |
| 2 | Elm City Gifts | mugs and small goods | 3 days |
| 3 | QuickShip CT | local courier | 1 day |

Note the split: vendor 1 handles the hoodie and the tee, vendor 2 handles the mug. Nobody listed
restocks the cap, but there are 40 of those anyway.

---

### `leases`
**Fields:** `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

The shop's rent. One row — the Chapel Street storefront.

> **Why it matters:** rent is the biggest bill in the building and it can't be skipped. The agent has
> to treat it as money already spoken for, not spare cash.

| ID | Space | Landlord | Rent | Next due |
|---|---|---|---|---|
| 1 | Chapel Street shop | Elm City Properties | $2,400.00 | 2026-09-02 (2 days out) |

---

### `cash_accounts`
**Fields:** `name`, `balance`, `date`

The bank balance. One account.

> **Why it matters:** this is the hard ceiling on everything. The agent can want to pay two bills and
> still only have one pile of money — this table is what forces it to choose.

| Account | Balance | As of |
|---|---|---|
| checking | **$3,400.00** | 2026-08-31 |

---

### `payments`
**Fields:** `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

The record of money actually sent out. **Currently empty — nothing has been paid yet.**

> **Why it matters:** this is the agent's receipt book. Writing a row here is the agent spending real
> money, and the `approved_by` column says a human has to sign off first.

`ref_id` is a loose pointer — it means "invoice 501" when `kind` is an invoice payment and "lease 1"
when it's rent. There's no foreign key enforcing it, so the agent has to set it correctly itself.

---

### `invoices`
**Fields:** `id`, `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description`

Bills a vendor has sent us that we haven't settled.

> **Why it matters:** this is what we owe and when. One bill is already late, so the agent is walking
> into a problem rather than a clean slate.

| ID | Vendor | Amount | Due | Status | For |
|---|---|---|---|---|---|
| 501 | 1 — Bulldog Print Co | $840.00 | 2026-08-28 | open | Rush reprint CC-TEE-WHITE S |

**That due date is 3 days in the past.** The invoice is overdue as of today.

---

### `tickets`
**Fields:** `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` → `leases.id`,
`invoice_id` → `invoices.id`, `status`, `notes`, `created_at`

The inbox. Every request a human has made of the shop, each one still `open`.

> **Why it matters:** this is the agent's to-do list, and it's the hub the whole database hangs off.
> Each ticket carries pointers into the other tables, so one ticket is really a question that spans
> stock, price, cash and suppliers at once.

The optional columns are what make it a hub — a ticket fills in only the ones its `type` needs, and
leaves the rest `NULL`.

---

## The three open tickets, and how they link

All three are `status = open` and were created on 2026-08-31 — the same day the clock is frozen at.

### Ticket 101 — `customer_order` — Tauhid Zaman, "Bulldog tee"

Carries `sku = CC-TEE-WHITE`, `size = S`, `qty = 1`, `invoice_id = 501`.

```
tickets.101
  ├─ sku + size ──→ inventory(CC-TEE-WHITE, 'S')  →  qty = 0        ← SOLD OUT
  ├─ sku ────────→ pricing(CC-TEE-WHITE)          →  $8.00 / $28.00
  └─ invoice_id ─→ invoices(501)  $840, due 08-28, OPEN (3 days late)
                        └─ vendor_id ─→ vendors(1) Bulldog Print Co, lead 5 days
```

**What the chain says in plain terms:** a customer wants a small tee. There are none. A reprint has
already been ordered from Bulldog Print Co and the bill for it, $840, is sitting unpaid and overdue.
The printer takes 5 days. So the honest answer to this customer depends on a *money* decision, not a
stock decision — and even in the best case the tee is roughly 5 days out from whenever we pay.

### Ticket 102 — `rent_notice` — Elm City Properties, "Rent due"

Carries `lease_id = 1`, and no sku/size/qty.

```
tickets.102
  └─ lease_id ──→ leases(1) Chapel Street shop, $2,400.00, next_due 2026-09-02
```

**What the chain says in plain terms:** rent of $2,400 is due in 2 days. The ticket's own note says
"due in 2 days", and the lease's `next_due` of 09-02 against a `date_today` of 08-31 agrees — the
data is internally consistent, so the agent can trust either source.

### Ticket 103 — `price_override` — Yale AI Club, "Bulk hoodie discount"

Carries `sku = CC-HOOD-NAVY`, `size = M`, `qty = 20`, and no invoice or lease.

```
tickets.103
  ├─ sku + size ──→ inventory(CC-HOOD-NAVY, 'M')  →  qty = 8        ← only 8 of the 20 asked for
  ├─ sku ────────→ pricing(CC-HOOD-NAVY)          →  $22.00 / $58.00
  └─ (restock path) ─→ vendors(1) apparel reprint, lead 5 days
```

**What the chain says in plain terms:** a student org wants 20 medium hoodies at a discount. We have
8. The other 12 would need a reprint from the same printer we already owe money to. At list price the
order is $1,160; our cost is $440; the discount can go down toward $22/unit before the shop starts
losing money, and the agent shouldn't go near that floor without a reason.

---

## The squeeze these three tickets create together

The tickets aren't independent — they compete for one $3,400 checking balance:

| Obligation | Amount | Deadline |
|---|---|---|
| Invoice 501 (unblocks ticket 101) | $840.00 | 2026-08-28 — **already late** |
| Rent, lease 1 (ticket 102) | $2,400.00 | 2026-09-02 — 2 days out |
| **Total** | **$3,240.00** | |
| Cash on hand | $3,400.00 | |
| **Left over** | **$160.00** | |

Both bills fit, but only barely — $160 of headroom, and nothing left for a reprint of the 12 extra
hoodies in ticket 103. Ticket 103's revenue ($1,160 at list) would comfortably cover that reprint,
but the cash arrives *after* the shop would have to spend it, and the order can't be fully filled
from the shelf either way.

**So the shape of the problem for the agents is:** three tickets, one bank account, one printer with
a 5-day lead time, and a pricing floor nobody should cross. Every table above exists to stop the
agent from answering any one ticket in a way that quietly breaks the other two.

---

# The MCP server

Everything above is what the database *holds*. This section is what the agents are actually allowed
to *ask*. The server lives in `mcp_server/server.py`, is built with FastMCP, and reads
`data/campus_customs_new.db` — the working copy, opened read-only. All three tools are
question-answering tools: none of them writes a row, spends money, or moves stock.

One tool per open ticket.

---

## Tool 1 — `check_stock(sku, size=None)`

**Table it reads:** `inventory`, and only `inventory`. It selects on the table's own
`(sku, size)` primary key and returns that row's `name`, `qty` and `location`; passing `size=None`
widens the query to every size row carried for the sku and sums their `qty`. It joins to nothing
else — `pricing`, `vendors` and `invoices` are all out of scope for this tool.

**Ticket it unlocks:** **101** — Tauhid Zaman, 1 × `CC-TEE-WHITE` in size `S`.

**Why it's the right tool for that ticket:** Ticket 101 names an exact `(sku, size)` pair, and
`inventory` is the only table in the database that counts stock per size, so this tool's lookup on
`('CC-TEE-WHITE', 'S')` returns the single row — `qty = 0`, Aisle B — that decides whether the agent
can hand the customer a tee today or has to redirect the answer to the reprint already on order.

**What it returns for ticket 101:** `qty = 0`, `in_stock = false`, `location = "Aisle B"`. Note what
this tool deliberately does *not* say: it reports the shelf is empty but not when it refills, because
that answer lives in `invoices` and `vendors`, not here.

---

## Tool 2 — `get_rent_due_and_cash_position(lease_id=None)`

**Table it reads:** `leases` is the primary table — selected by `id`, returning `space_name`,
`landlord`, `monthly_rent`, `next_due` and `notes`. It reads three supporting sources alongside it:
`desk.date_today` (to turn each `next_due` into a countdown in days rather than a bare date string),
every row of `cash_accounts` (for `balance`), and every row of `invoices` whose `status` is not
`'paid'`, `LEFT JOIN`ed to `vendors` so each bill carries the supplier's name. It then nets total
cash against rent *and* those open invoices together.

**Ticket it unlocks:** **102** — Elm City Properties, "Rent due".

**Why it's the right tool for that ticket:** Ticket 102 carries a `lease_id` of 1 and no sku, size or
quantity at all, so the lease row is the only thing it points at — and since an affordable bill and
an unaffordable one look identical in `leases` alone, this tool returns the $2,400.00 rent due
2026-09-02 beside the $3,400.00 balance *and* the $840.00 already owed on invoice 501, which is the
combination that turns the ticket into a decision the agent can defend.

**What it returns for ticket 102:** `monthly_rent = 2400.0`, `next_due = "2026-09-02"`,
`days_until_due = 2` (against a `desk.date_today` of 2026-08-31), `cash_total = 3400.0`,
`obligations.rent_total = 2400.0`, `obligations.open_invoices_total = 840.0`,
`obligations.total_committed = 3240.0`, `cash_available_after_all_commitments = **160.0**`,
`all_commitments_covered_by_cash = true`. The `open_invoices` list carries invoice 501 — Bulldog
Print Co, $840.00, due 2026-08-28, `days_until_due = -3`, `overdue = true`.

**Note on the arithmetic:** the `leases` list honours the `lease_id` filter, but the obligation
totals are always computed across *every* lease and *every* unpaid invoice. Filtering the maths to
one lease would make the tool report more free cash than the shop has, which is the exact failure
this tool is built to avoid.

## Tool 3 — `get_price_and_floor(sku, quantity=None)`

**Table it reads:** `pricing`, and only `pricing`. It selects the single row for the sku and returns
both of its numeric columns — `unit_cost` and `list_price` — then derives `margin_per_unit` from
them, plus `total_at_list`, `total_at_cost` and `max_total_discount` when a `quantity` is supplied.
It does not read `inventory`, so it will quote a price for a product whether or not any exist.

**Ticket it unlocks:** **103** — Yale AI Club, 20 × `CC-HOOD-NAVY` in size `M`, asking for a bulk
discount.

**Why it's the right tool for that ticket:** Ticket 103 is a request to change a price, and
`pricing.unit_cost` is the only figure anywhere in this database that says how far a price is allowed
to move before the shop starts losing money on each unit — so surfacing that $22.00 floor next to the
$58.00 list price is what lets the agent reason about a discount from recorded numbers instead of
inventing a percentage.

**What it returns for ticket 103** (called with `quantity=20`): `unit_cost = 22.0`,
`list_price = 58.0`, `price_floor = 22.0`, `margin_per_unit = 36.0`, `total_at_list = 1160.0`,
`total_at_cost = 440.0`, `max_total_discount = 720.0`. The $720 is the absolute limit — a discount
of exactly that much prices the order at cost and earns the shop nothing.

---

## What these three tools deliberately leave out

Worth recording now, because it shapes what the agents can and can't conclude:

- **Nothing reads `tickets`.** The agents are handed a ticket; they can't browse the queue.
- **Nothing reads `vendors.lead_days`.** Tool 2 names Bulldog Print Co as the vendor behind invoice
  501, but no tool reports the 5-day reprint lead time, so no agent can yet put a date on when the
  sold-out tee in ticket 101 comes back.
- **Nothing writes to `payments`.** No agent can spend money with the tools as they stand, which is
  the right default while `approved_by` still implies a human signature.

The cash figure, though, is now honest: tool 2 reports **$160.00** available after both rent and the
overdue invoice, matching the squeeze described earlier in this document rather than the $1,000 that
rent-only arithmetic would suggest.

---

# The agent team

Five PydanticAI agents, all on `gpt-6-luna` through the Portkey gateway, all sharing the one MCP
toolset above. Code under `backend/`, prompts one-file-per-agent under `backend/prompts/`, data types
in `backend/models.py`, wiring in `backend/team.py`.

| Agent | Owns | Must not do |
|---|---|---|
| **Boss** | The decision, the sequencing, the trade-off when two tickets want the same money. The only agent that closes a ticket. | Count stock, work out affordability, or write the customer's words itself. |
| **Inventory** | What is on the shelf, counted per size, and what restocking would take. | Quote prices or judge affordability. |
| **Accounting** | Balances, unpaid bills, the price floor, and the only tool that spends. | Estimate stock, or pay without a named human approver. |
| **Facilities** | The lease, the rent, the due date. Insists rent comes first. | Count days by hand, or move the money itself. |
| **Customer Service** | The words that reach a person. | Originate any number, or promise what the data doesn't support. |

**Full connectivity:** every agent carries an `ask_<name>` tool for each of the other four — 20
delegation edges, each direction separate, including a specialist pulling the Boss in. Two guards
stop that looping forever: an agent already in the run's chain cannot be asked again (which kills
Boss → Inventory → Boss and every longer cycle), and past `max_depth` hops delegation is refused.
A refusal comes back as an ordinary tool result, and each prompt tells the agent to answer with what
it has and say what is missing.

## The five new MCP tools

The three original tools couldn't support a team — nothing read the ticket queue, nothing reported a
vendor's lead time, and nothing could act. These five close that gap.

### `list_tickets(status="open")` and `get_ticket(ticket_id)`
**Tables read:** `tickets`. Both return the raw columns plus a `links` block naming the
`(sku, size)` pair, the `lease_id` and the `invoice_id` that ticket points at, so an agent can see
where to look next without knowing the schema.
**Who uses them:** the Boss, to work a ticket from the real row rather than a paraphrase, and to see
what else is competing for the same money. Customer Service, to get the requester's name and the
exact size before drafting.
**Why they're right:** a ticket's `type` decides which of its optional columns are filled, so the
difference between a rent notice and a product request is which fields are null — returning the
links makes that structure legible instead of something each agent has to rediscover.

### `list_vendors()`
**Table read:** `vendors` — `specialty` and `lead_days` for all three suppliers.
**Who uses it:** Inventory, when the question turns into "when could we get more?".
**Why it's right, and its one trap:** `lead_days` is the only restock-timing figure in the database.
But **no table maps a sku to a vendor** — the only recorded product-to-vendor link anywhere is the
`description` text on an existing invoice. The tool therefore returns
`sku_to_vendor_mapping_exists: false` alongside the rows, and Inventory's prompt spends a paragraph
on the difference between "there's a supplier specialising in apparel reprints with a five-day lead
time, which looks like a match" and "the tee takes five days." The first is a labelled inference; the
second is an invention that leaves a customer waiting on an order nobody placed.

### `list_open_invoices()`
**Tables read:** `invoices` where `status != 'paid'`, `LEFT JOIN vendors` for the supplier name and
lead time, against `desk.date_today` for the overdue flag.
**Who uses it:** Accounting, when the question is specifically about bills rather than the whole cash
position.
**Why it's right:** it returns `days_until_due` as a signed number, so invoice 501 reports `-3` and
`overdue: true` rather than leaving an agent to compare two date strings and get it wrong.

### `record_payment(kind, amount, account, approved_by, ref_id)`
**Tables written:** `payments` (insert), `cash_accounts` (balance decremented), and `invoices`
(status set to `paid` when `kind` is `"invoice"`) — all in one transaction, so a crash can't leave
money gone with the bill still owed.
**Who uses it:** Accounting, and only Accounting.
**Why it's right:** `payments.approved_by` exists because a person signs off on spending, so the tool
requires a non-empty approver and refuses without one. It also refuses to overdraw, to pay a
nonexistent account or invoice, or to pay a bill twice. All five refusals are returned as
`recorded: false` with a reason rather than raised, and the prompts say a refusal is a correct
outcome, not an error to retry around.

**Verified refusals** (tested against a throwaway copy): missing approver, overdraw, unknown account,
invalid kind, nonexistent invoice, and double payment. A real payment of $840 moved cash
3400 → 2560, open invoices 840 → 0, and left available at $160 either way — which is the figure the
earlier squeeze analysis predicted.

## A footgun worth recording

`CAMPUS_CUSTOMS_DB` is **ignored if you export it in a shell**. An MCP client launches the server as a
subprocess without passing the parent environment through, so the server silently falls back to its
default database. This was found the hard way: a test meant for a throwaway copy wrote a real payment
into `data/campus_customs_new.db`, which had to be restored from the pristine original. Set the
variable in the client's own config — the `env` block in `.mcp.json`, or `env=` on a FastMCP
`StdioTransport` — and never assume a shell export reached the server.

## What the team still cannot do

- **No agent can see another ticket's decision.** Each run works one ticket. The Boss can *read* the
  other open tickets, but there is no shared state recording what was decided about them, so two runs
  could each approve spending that together overdraws the account.
- **`payments.ref_id` is unenforced.** No foreign key ties it to an invoice or a lease, so correctness
  there depends on `record_payment` setting it properly, not on the schema.

---

# Backend routes

FastAPI app in `backend/main.py`. Started from the `backend/` folder with
`uvicorn main:app --reload --port 8000`. Interactive docs at `/docs`.

| Route | What it does |
|---|---|
| `GET /api/health` | Is the server up, which model the team runs on, and the shop's frozen date. |
| `GET /api/tickets` | All three tickets with an explicit `open` / `resolved` flag, plus the counts. |
| `GET /api/tickets/{id}` | One ticket, with any payments its runs have parked for approval. |
| `POST /api/tickets/{id}/run` | Runs the agent team on that ticket and returns the Boss's decision; parks an approval if money is involved. |
| `GET /api/events?since=N` | Agent events after sequence `N` — who spoke, what they said, which MCP tools they called. The board polls this. |
| `GET /api/approvals` | Payments the team has prepared, and what became of each. |
| `POST /api/approvals/{id}/approve` | **The only route that moves money.** Executes a prepared payment and resolves its ticket. |
| `POST /api/approvals/{id}/decline` | Rejects a prepared payment. Moves no money, leaves the ticket open. |
| `GET /api/cash` | The checking balance, what is committed against it, and recent payments. |
| `POST /api/reset` | Restores the database from the pristine original and clears events and approvals. |

## How "agents prepare, humans pay" is actually enforced

Not by asking nicely in a prompt. Three separate mechanisms:

1. **The run route passes no approver.** `run_ticket` is always called with `approver=""`, so by the
   team's own rules no agent may pay.
2. **`record_payment` is blocked at the toolset.** `config.AGENT_BLOCKED_TOOLS` screens every MCP
   call an agent makes; a call to `record_payment` never reaches the server and comes back telling
   the agent to propose instead. Verified by a test that fails loudly if the call gets through.
3. **The approve route uses its own MCP client.** It bypasses the agent toolset entirely, so the
   human path still works while the agent path stays shut.

The payment still goes through the MCP server's `record_payment` rather than SQL written in the
route, so every guard that tool enforces — named approver, no overdraw, no double payment, one
transaction across `payments`, `cash_accounts` and `invoices` — applies to the dashboard too. There
is one way to spend money in this project and the route is a caller of it, not a second one.

## Verified end to end

Against a live server on a spare port, and through `TestClient` for the money path:

| Check | Result |
|---|---|
| Read routes over HTTP | `health`, `tickets`, `tickets/{id}`, `cash`, `events`, `approvals` all 200; unknown ticket 404s |
| Approve with a blank name | 400, cash unchanged at $3,400 |
| Approve properly | cash $3,400 → **$2,560**, invoice 501 settled, ticket 101 → `resolved` |
| Approve the same payment twice | 400, "already approved" |
| Decline | status `declined`, cash untouched |
| Agent calling `record_payment` | blocked before reaching the server, told to propose instead |
| `POST /api/reset` | cash back to $3,400, all 3 tickets open, approvals and events cleared |

---

# The dashboard

React + Vite + TypeScript in `frontend/`, started with `npm run dev`, talking to the backend at
`http://localhost:8000`. Full design rationale in `output/design.md`.

| Region | What it holds |
|---|---|
| **The spike** (left) | The three tickets as index cards. Resolved ones take a green `SETTLED` rubber stamp. |
| **The floor** (centre) | Five agent stations. Each renders in its own voice — Boss as a decree, Inventory as a count, Accounting in tabular numerals, Facilities date-forward, Customer Service as a letter. Idle agents stay visible and dimmed, so *who was not called* is readable. |
| **The till** (right) | Checking balance, a meter splitting it into rent / unpaid bills / genuinely free, a torn-edge receipt of payments, and the approval form. |
| **The wire** (bottom) | Every event in sequence: agent started, agent replied, tool called, decision, approval. |

The approve button stays disabled until a name is typed, matching the backend rule that refuses an
unsigned payment. Polling runs at 700 ms during a run and 3 s when idle.

---

# Safety rules

The rules that stop this team doing something the shop would regret, and where each is actually
enforced — in code, not only in a prompt.

| Rule | Enforced by |
|---|---|
| **Agents may never spend money.** | `config.AGENT_BLOCKED_TOOLS` screens every MCP call an agent makes. A call to `record_payment` never reaches the server; the agent is told to propose instead. The run route also passes no approver. |
| **Only a human moves cash.** | `POST /api/approvals/{id}/approve` is the single code path that spends. It reaches the MCP server through its own client, so blocking agents does not block people. |
| **No payment without a signature.** | `record_payment` refuses a blank `approved_by`. The dashboard disables approve until a name is typed. Both payment rows in the database carry one. |
| **Never overdraw.** | `record_payment` checks the balance inside the same transaction and refuses. |
| **Never pay a bill twice.** | Paying an invoice sets its status to `paid` in the same transaction; a second attempt is refused. |
| **A payment is all-or-nothing.** | `payments` insert, `cash_accounts` decrement and `invoices` update run in one `BEGIN IMMEDIATE` transaction, so a crash cannot leave money gone with the bill still owed. |
| **Never sell below cost.** | `get_price_and_floor` returns `unit_cost` as an explicit floor, and Accounting's prompt treats it as a hard limit. On ticket 103 the team declined to pick a discount at all rather than guess one. |
| **Never invent a fact.** | Agents cite a `Fact` with its table and column. `list_vendors` returns `sku_to_vendor_mapping_exists: false`, and on both product tickets the team reported the supplier link as unconfirmed instead of promising a date. |
| **The team cannot loop forever.** | Each delegate tool refuses an agent already in that branch's chain and refuses past `max_depth` hops. |
| **One ticket has one bill.** | Delegated agents share the Boss's usage object, so a whole ticket runs under one `UsageLimits` budget. |
| **The original data is never touched.** | Agents and the API read and write `campus_customs_new.db`. `campus_customs.db` is only ever a copy source, and `POST /api/reset` restores from it. |

**A caveat worth recording:** the no-revisiting guard is *per branch*, not global. On ticket 101 the
Boss consulted Accounting, then Facilities consulted Accounting again on its own branch — allowed,
because Accounting was not in that branch's chain. It cost one extra model call and produced the
same $160. A global rule would be cheaper; a per-branch rule lets a specialist get its own answer.
This run showed the trade-off is real.

---

# What actually happened

Database reset, all three tickets run, all three resolved.

| Ticket | Agents that worked it | Hops | Outcome | Cash |
|---|---|---|---|---|
| **101** | Inventory, Accounting, Facilities, Customer Service | 5 | No promise made — out of stock, restock unconfirmed. Overdue invoice recommended. | −$840.00 |
| **102** | Facilities, Accounting | 2 | Rent confirmed against the lease and found affordable. | −$2,400.00 |
| **103** | Inventory, Accounting, Customer Service | 3 | 8 offered at list; no discount quoted without a human price. | $0.00 |

**Checking: $3,400.00 → $160.00**, matching `cash_accounts` exactly. Both payments were prepared by
the team and approved by a human; neither was made by an agent.

Where the plan was wrong: ticket 101 was predicted not to involve Facilities, and it did. Tickets
102 and 103 matched their plans, including the arguable call to send 103 to Inventory before
Accounting. Full comparison in `output/desk_tickets.html`.

## Files

| File | What it holds |
|---|---|
| `output/harness.md` | This document. |
| `output/desk_tickets.html` | Per-ticket Expected vs Actual, and the itemised cash ledger. |
| `output/resolved_tickets.json` | Final status, outcome, per-agent contribution and approvals. |
| `output/resolved_board.html` | Screenshots of the live board for each resolved ticket. |
| `output/audit_trail.json` | Full run record including all 61 events. |
| `output/mcp_smoke.json` | The Problem 4 tool tests. |
| `output/design.md` | Dashboard design rationale. |
