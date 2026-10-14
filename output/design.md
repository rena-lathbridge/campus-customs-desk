# The Desk — dashboard design

The board for the Campus Customs agent team. React + Vite + TypeScript in `frontend/`, talking to
the FastAPI backend at `http://localhost:8000`.

```bash
npm run dev     # from frontend/, serves on http://localhost:5173
```

---

## The idea it's built on

A dashboard full of identical cards tells you nothing at a glance. You have to *read* it to learn
anything, and by then the run is over.

So this one is built as **a place rather than a report**, and styled after a minimalist fashion
house — Jil Sander, The Row, Céline. Tickets are catalogue entries down the left. The five agents
are stations on the floor. The till is on the right. A wire runs along the bottom.

The whole aesthetic is **restraint**. Bone paper, ink type, hairline rules, and one oxblood accent
used about six times on the entire page. No shadows, no gradients, no rounded corners, no filled
buttons except the single thing you are meant to press. Space does the work that decoration would
otherwise do — which is also why it suits a data-dense board: nothing competes with the numbers.

| | |
|---|---|
| Paper | `#f6f4ef` bone |
| Ink | `#16150f` |
| Rules | `#dcd7cb` hairline, `#16150f` for section breaks |
| Accent | `#8c2f2a` oxblood — live state, selection, resolution, money that moved |
| Display | Didot / Bodoni 72 — headings, the balance, decisions, letters |
| Labels | Tiny uppercase sans at `.22em` tracking |
| Data | SF Mono, tabular numerals |

Two type sizes do almost all the work: a large light Didot for anything that is a *statement*, and a
small letterspaced uppercase sans for anything that is a *label*. Everything else is set in between.

---

## Layout: nothing is a long scroll

A fixed three-column floor with a wire beneath it. Each column scrolls on its own, so the till never
leaves the screen while you read.

**Why this shape.** The three columns are the three questions you have while a run is going: *what
are we working on*, *who is doing what*, and *what is it costing us*. Keeping the till in permanent
view is the most important layout decision on the board, because money is the constraint every
ticket runs into, and a balance you have to scroll to find is a balance you forget to check.

### Everything is behind a click

The first two builds put all of a ticket's detail on one page, and you read it by scrolling —
five agent blocks, then a summary, then the reply, then the risks, one after another. Correct
information, exhausting to use, and the end of the page was always off-screen.

The centre column is now **progressive**. You click to go deeper, and every level fits on one
screen:

```
  click a ticket on the spike
        ↓
  ┌─ the opener ─────────────────────┐   ticket number at 74px, subject, requester
  │  THE TEAM · THE DECISION ·       │   four views, one click each
  │  THE REPLY · RISKS               │
  ├──────────────────────────────────┤
  │  01 BOSS            (full width) │   the contact sheet: all five agents,
  │  ────────────────────────────    │   two lines each, tool count, no scroll
  │  02 INVENTORY │ 03 ACCOUNTING    │
  │  04 FACILITIES│ 05 CUST. SERVICE │
  └──────────────────────────────────┘
        ↓ click a plate
  ┌─ the full station ───────────────┐   that agent alone, set in its own voice,
  │  INVENTORY      ← all five       │   every word, every tool it called
  └──────────────────────────────────┘
```

**The contact sheet** is the key move. Five plates on one screen — the Boss across the top because
its decision frames everything else, then the four specialists in a 2×2. Each plate carries only
what you need to decide whether to look closer: who, whether they worked, a two-line excerpt, and a
tool count. An agent that was never called is greyed, unclickable, and says *not called* — because
who the Boss skipped is a finding, not an absence.

**The other three views** each hold what used to be stacked below the fold:

| View | What it holds |
|---|---|
| **The team** | The contact sheet, and any agent you click into. |
| **The decision** | The Boss's decree, what each teammate contributed, and the reasoning. |
| **The reply** | The message that left the building, alone on the page as a centred pull quote. |
| **Risks** | What the decision still costs, numbered, plus anything left open. |

Measured: at 1560×1040 the team view, the opened-agent view, the reply and risks all fit with
**zero overflow**. Only the decision view runs slightly long, and only when an agent wrote a great
deal.

## How the agents read differently

This is the part the board is really for.

A generic dashboard gives all five agents the same coloured chip and the same chat bubble. But these
five produce genuinely different kinds of output — a stock count, a bank balance, a due date, a
decision, a drafted apology — and flattening them into one typeface throws away information you
could have read instantly.

So each agent has **its own rendering of what it says — and its own shape on the page**. The voice
drives the layout, not just the typeface:

| Agent | Voice | Reads as |
|---|---|---|
| **Boss** | `decree` | Light Didot at full width, ruled top and bottom. A pronouncement, because it is one — the Boss is the only agent that closes a ticket. |
| **Inventory** | `count` | Mono, loose leading. Stock is a number, and the number is the answer. |
| **Accounting** | `ledger` | Mono with **tabular numerals**, so dollar figures line up digit over digit the way they would in a ledger. |
| **Facilities** | `calendar` | Mono, date-forward. Facilities exists to say *when*. |
| **Customer Service** | `letter` | Italic Didot, inset from the left and set narrow. It is the only agent writing to a human, so it breaks the page's alignment and is set as correspondence rather than data. |

The hues are **tonal, not bright**: oxblood, olive, sage, slate and clay, all desaturated to within a
few steps of grey, and each appears only as a single hairline beside its station. In the old
black-and-pink build the colour did the identifying; here the typography does, and the colour is
barely there. That is deliberate — five saturated highlights would have fought the restraint the
rest of the page depends on.

**Three states, not two.** A station is `idle` (dropped to 38% opacity), `live` (hairline at full
strength, oxblood label, three dots before any words arrive), or `spoke`. Idle agents stay on screen
rather than hiding, because *who was not called* is as interesting as who was — it is exactly what
the Problem 6 plan predicted, and the greyed-out stations make the comparison visible.

**Tool names** sit under each agent's words as small mono labels on hairline underlines, attributed
per-agent from the run context. A blocked call renders struck through in oxblood — which is how
`record_payment` appears if an agent ever reaches for it.

---

## How resolved tickets show up

Tickets are catalogue entries, not cards: no borders, no fill, just generous space and a hairline
between each. Hovering shifts an entry 10px right; the selected one shifts further and grows a thin
oxblood rule down its left edge.

Resolution is a **letterpress marque** — the word `SETTLED` in small caps, oxblood, ruled above and
below, which animates in by tightening from `.9em` tracking to `.3em` over half a second. The type
*sets itself* rather than being stamped on.

That replaced a green rubber stamp that thudded in at 2.6× scale. The stamp was fun and completely
wrong for this house: resolution should read as something recorded, not something whacked onto the
page. Restraint is the louder gesture here.

---

## How cash shows up

The till is a single large Didot figure, because the checking balance is the number everything else
is measured against.

Underneath is the part most dashboards would omit: a **hairline meter** splitting that balance into
rent, unpaid bills, and what is genuinely free. The shop started with $3,400 in the bank and $160
actually free. A board that shows only $3,400 is telling you something true and useless. The meter
makes the gap between *balance* and *available* visible at a glance — and when everything is settled
the row relabels itself to "nothing owed · all free" rather than showing three empty segments.

**When an approved payment lands**, the figure turns oxblood and a `−$840.00 just paid` delta rises
beneath it for four seconds. Below, a plain ruled list records each payment with who signed for it.

---

## How approval works

The approval block is set as a **chit that wants initialling**: an oxblood label, the amount in
Didot, a rule-only text field reading *"Type your name to sign"*, and an `authorised by` line.

The approve button stays disabled, outlined and grey until a name is typed, then fills solid ink and
turns oxblood on hover. That is not decoration — the backend refuses an unsigned payment, and the
form is built so the refusal never happens. Enter submits.

This is the one place on the board where a human changes the world, so it gets the only solid filled
control on the page.

---

## The wire

A fixed 150px strip along the bottom, mono, newest at the end, auto-scrolling. Every event:
timestamp, kind, agent, message. Only `decision`, `approval` and `error` take the accent; everything
else sits in grey, so the two things that matter stand out of the stream without the stream becoming
a rainbow. A small oxblood pip breathes while a run is live.

The stations show you the *current* state; the wire shows you the *sequence*. Watching the order
agents get pulled in is how you tell whether the team routed the ticket the way the plan said it
would.

---

## Creative choices, and why

1. **A room, not a report.** The spike / floor / till / wire metaphor gives every fact one fixed
   home, so you orient once instead of re-reading headings.
2. **Five voices instead of five colours.** The strongest idea here, and the one that survived the
   restyle unchanged. Typography carries meaning colour alone cannot — tabular numerals for money,
   a letter for correspondence, a decree for the decision.
3. **One accent, roughly six uses.** Oxblood marks live state, selection, resolution, and money that
   actually moved. Because it is rationed, it reads as significant every time it appears.
4. **Rules, not boxes.** Nothing on this board is in a container. Hairlines separate; space groups.
   It is what makes a dense operational tool read as composed rather than crowded.
5. **The marque instead of the stamp.** Resolution recorded, not shouted.
6. **The meter under the balance.** Refuses to let the headline number mislead. The design argues
   with the data on purpose.
7. **Idle agents stay on screen.** Who was not called is a finding, not an absence.
8. **One filled button on the page.** Everything else is a rule-underlined word. The only solid
   block of ink is the thing that commits the shop.
9. **The voice sets the shape, not just the type.** Five agents in five typefaces but five
   identical boxes still reads as a list; five agents occupying genuinely different amounts and
   alignments of the page reads as a spread.
10. **Depth instead of length.** The real fix for the endless page was not better rhythm — it was
   refusing to show everything at once. A contact sheet you click into holds exactly as much
   information as the old scroll, and asks you to read about a tenth of it.
11. **Idle plates stay clickable-looking but aren't.** Greyed, disabled, labelled *not called*.
   The gap in the sheet is the point.
11. **Polling adapts.** 700ms while a run is live, 3s when idle — immediate when it matters, quiet
   when it does not.

The two output pages — `desk_tickets.html` and `resolved_board.html` — use the same palette, type
scale and hairline system, so the whole hand-in reads as one house.

---

## Wiring

The frontend calls `http://localhost:8000` (set once in `src/api.ts`). The backend allows the Vite
origin via CORS middleware in `backend/main.py`:

```python
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]
```

Verified: a preflight from the Vite origin returns a matching `access-control-allow-origin`, and a
request from any other origin gets no allow header at all.
