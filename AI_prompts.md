# AI Prompts

A log of the prompts I wrote while working through this homework assignment, one section per problem.

**How this file works:** every problem gets its own section below, added as we finish it. Each section
records the problem number and title, at least one prompt in my own words, a follow-up prompt when the
first one wasn't enough, and one sentence on what was lacking after the first prompt.

---

## Problem 1 — Vibe Coder Prompts

**Prompt 1 (my words):**
> Problem 1: Vibe Coder Prompts
>
> For all the work we're going to be doing please create AI_prompts.md and keep it updated as we go through the hw assignment. Have a section for each problem that contains the following:
>
> * The problem number and title
> * At least one prompt that was used to solve the problem
> * One follow up prompt if needed and one sentence on what was lacking after the first

**Follow-up prompt (my words):**
> Sorry can we move this to HW 5 folder and do all the work there

**What was lacking after the first prompt:** My first prompt described exactly what the log had to
contain but never said *where* the assignment lived, so the file landed in the `Lecture 7` folder the
session happened to be open in and had to be moved to `HW 5` before any other work started.

---

## Problem 2 — Study the Campus Customs Database

**Prompt 1 (my words):**
> Problem 2: Study the Campus Customs Database
>
> Open data/campus_cusotms.db and look through every table and its fields then copy the original file to data/campus_customs_new.db
> Please study the 3 open tickets to understand how they link to the other tables in the data
> Please start output/harness.md. For each table list the fields and one short line on why that table matters for the agents in very layman terms.

**Follow-up prompt (my words):**
> _(none needed — the prompt named the file, the copy, the three tickets and the output doc, so it ran in one pass.)_

**What was lacking after the first prompt:** Two small gaps that didn't need a new prompt to fix — I
typed the filename as `campus_cusotms.db` when the real file is `campus_customs.db`, and I asked why
each table matters "for the agents" before I'd actually said what the agents are, so those lines had
to be inferred from what the data itself makes possible rather than from a spec.

---

## Problem 3 — Build the MCP Server

**Prompt 1 (my words):**
> okay great please close this problem and let's move on to Problem 3: Build the MCP Server
>
> Please write an MCP server in mcp_server/ using FastMCP. It should communicate with data/campus_customs_new.db. Do not connect or run it yet. Every agent in this hw will use the tools in this MCP server. For now please write 3 tools that will be needed for the tickets in the database. Please make sure to keep the names clear, and only use the information in the database - do not invent information that does not exist in the database
>
> In output/harness.md, list each of the three MCP tools and include the following for each:
>
> * specify which table it reads
> * which ticket it helps unlock (101, 102, or 103)
> * One sentence on why that toll is the right one for that ticket
>
> You cannot write vague lines such as 'reads inventory' because those would give me a low score on the HW so please refrain from that those type of sentences
>
> Please add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the 3 tools it has in layman's terms

**Follow-up prompt (my words):**
> can you correct tool 2 so it doesn't overstate the headroom?

**What was lacking after the first prompt:** I asked for exactly three tools with one ticket each, which forced a 1:1 mapping and left nothing reading `tickets`, `invoices` or `vendors`, so no agent could see the overdue $840 invoice or the printer's 5-day lead time that ticket 101 actually depends on.

---

## Problem 4 — Add the MCP Server to Vibe Coder and Test Each Tool

**Prompt 1 (my words):**
> Thank you. Please close problem 3, let's start Problem 4: Add the MCP server to vibe coder and test each tool
>
> Please add the MCP server to this project to be able to call the tools. Save the connection JSON text in .mcp.json at the project root (or however claude saves local MCP server lists)
> While your connected please test each of the 3 MCP tools and save the evidence in output/mcp_smoke.json. Please include the following for each tool:
>
> * The prompt asked
> * The tool name
> * The tool output (must match the values in data/campus_customs_new.db)

**Follow-up prompt (my words):**
> please confirm that all the problems up to this point have been done correctly

**What was lacking after the first prompt:** The prompt was complete, but the connection config it asked for silently failed because `.mcp.json` said `python3`, which resolves to the system Python — the one without `fastmcp` — whenever a launcher starts the server with a minimal PATH.

---

## Problem 5 — Build the Agent Team and Grow the MCP Tools

**Prompt 1 (my words):**
> okay great let's close out problem 4 and move on to Problem 5: Build the agent team and grow the MCP tools
>
> Please build the agentic team for Campus customs using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. In one file per agent place the agent prompts in backend/prompts/
> Put the data types in backend/models/py and the agent files under backend/
> Use PORTKEY_API_KEY and only gpt-6-luna for every agent.
> Write the prompt in laymans terms with the shop rules that agent needs.
> More detailed prompts that cover all aspects of an agent's work and scope will give me a higher score on the hw

**Follow-up prompt (my words):**
> _(none needed — the roles, the file layout, the model and the "full connectivity" requirement were all specified up front.)_

**What was lacking after the first prompt:** The prompt said `backend/models/py`, which is not a valid path and had to be read as `backend/models.py`, and it named `gpt-6-luna` while the project's `AGENTS.md` says `gpt-5.6-luna`, so the model is now set in exactly one place to keep that conflict a one-line change.

---

## Problem 6 — Plan the Three Tickets

**Prompt 1 (my words):**
> Close out problem 5. Here are the instructions for Problem 6: Plan the three tickets
>
> Before wiring the backend, please write down what is the team is expected to do on each open ticket in layman's terms. Build output/desk_tickets.html which should be a page you can double-click with one tab per ticket
> Please also add empty Cash and Reflection tabs for later problems
>
> on each ticket tab, fill an Expected section only (leave room for an Actual section that will be filled in after the agents run)
> For wach ticket's Expected section write:
>
> * Who the Boss should call first and why
> * All the agent delegations you expect (it can't be that the 'Boss calls everyone")
> * Which MCP tools you expect that run to use
>
> Plans that send every specialist on every ticket will score low so please refrain from doing that. This plan will be compared to what actually happens with the agents resolve the 3 tickets

**Follow-up prompt (my words):**
> _(none needed — the "don't call everyone" constraint was the hard part and it was stated clearly
> up front.)_

**What was lacking after the first prompt:** The prompt asked who the Boss calls first but not how to justify who gets left out, which is where the marks actually are, so each ticket tab also got a “who is not called, and why” table.

---

## Problem 7 — Backend Routes

**Prompt 1 (my words):**
> Please close Problem 6. Here are the instructions for Problem 7: Backend routes
>
> The React frontend dashboard (coming soon in the next problem) needs a backend that it can call. So in backend/main.py, use FastAPI and add routes that do the following:
>
> * Return the three tickets and whether each is open or resolved
> * Take a ticket ID and run your agent team on that ticket
> * Return recent agent events (what each agent said and which tools they used) so the board can refresh
> * Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
> * Return the current checking balance from cash_accounts
> * Reset the database to the original values when running a fresh run
>
> From the backend/ folder, start the server with: uvicorn main:app --reload --port 8000
>
> In output/harness.md, list each route in one line (what URL / what it does)

**Follow-up prompt (my words):**
> _(none needed — the six routes were listed explicitly, including the one rule that shaped the
> design: agents prepare, the approve route pays.)_

**What was lacking after the first prompt:** The prompt said agents only prepare the payment but not how to stop them paying, which no prompt alone could do because `record_payment` was already sitting in the toolset every agent shares.

---

## Problem 8 — Agent Dashboard

**Prompt 1 (my words):**
> Great please close problem 7. Here are the instructions for Problem 8: Agent dashboard
>
> Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes built in Problem 7. At the minimum the board should have the following:
>
> * List all three tickets
> * Let you pick one ticket and start the agent team on it
> * Show each agent and what they're saying / doing while the ticket is running
> * Mark a ticket resolved when the run finishes
> * Show a short summary of what each agent did on that ticket
> * Let a human approve a pay or purchase when asked
> * Show the checking balance (it should drop after an approved pay)
>
> Make the dashboard look amazing and creative (no boring dashboards allowed). Tell the front end to talk to the backend at http://localhost:8000 On the backend allow the Vite page origin so the browser is allowed to call those routes
>
> Please start the board with the following command: npm run dev
>
> Write output/design.md with the dashboard look (layout, how agents read differently, howe resolved tickets and cash show up) and why, including the creative choices that were made

**Follow-up prompt 1 (my words):**
> I hate the blackpink theme, can you model after a fashion house

**Follow-up prompt 2 (my words):**
> I like the design a lot more but I wish that the design wasn't one boring thing to scroll through

**Follow-up prompt 3 (my words):**
> I would want the person to have to click on a card for the different tickets to see all the information. right now it's still just one never ending scrolling page

**What was lacking after the first prompt:** The brief said “amazing and creative” without saying what kind, so the first build defaulted to the project's black-and-pink palette and then to a single long scrolling page, each of which needed a follow-up to put right.

---

## Problem 9 — Resolve the Tickets

**Prompt 1 (my words):**
> Let's close that and open problem 9: Resolve the tickets
>
> Reset the working database data/campus_customs_new.db again. Not the starting checking balance. Run all 3 tickets on the board (101, 102, 103) until each is resolved
>
> Open output/desk_tickets.html from Problem 6. On each ticket tab, fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep the Expected section to compare the two.
>
> On the Cash tab of the same output/desk_tickets.html, itemize the money: starting checking balance (after the reset); for each ticket how cash changed when that ticket resolved and why (which pay / purchase, dollar amount); ending checking balance (must match cash_accounts in the working database)
>
> Wrong cash math will result in me losing points so please be sure that this is correct and confirm it is
>
> Also save output/resolved_tickets.json, output/resolved_board.html with a screenshot of the React board for each resolved ticket, append real runs to output/audit_trail.json, and finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules

**Follow-up prompt (my words):**
> _(none needed — the deliverables and the cash-accuracy requirement were stated explicitly.)_

**What was lacking after the first prompt:** Nothing was missing from the prompt, but running the team for real exposed four bugs that reading the code had not — a request budget that cut the Boss off mid-decision, `build_team()` failing on the second ticket, paid rent still counting as owed, and the board going blank on reload.

---

## Problem 10 — Reflection

**Prompt 1 (my words):**
> Okay I think we can close that problem finally. Here are the instructions for Problem 10: Reflection
>
> Open output/desk_tickets.html and fill the Reflection tab with my answers to the following questions. I wrote my answers but feel free to refine for clarity:
>
> * How would you evaluate the performance of the agents on each ticket and why? I think they did a decent job because they accomplished the task

**Follow-up prompt (my words):**
> Sorry forgot to write the rest: for each ticket how did Actual compare to the Expected plan; what would have been simpler as one agent with tools and why; describe three new problems Campus Customs might face that this agent team could solve with the tools you built; describe three new problems it could not solve, and explain the tools and agents you would need. Tie every answer to this app and the three tickets that were run, please use the ticket tabs and Cash tab on the same page as the evidence. Generic AI essays without Campus Customs details will be graded poorly.

**What was lacking after the first prompt:** My first message said “questions” but pasted only one
of the five, so the Reflection tab got built around a single answer and the other four — the
Expected-versus-Actual comparison, the one-agent question, and the two lists of future problems —
had to be added in a second pass.

---

## Problem 11 — Push to a Public GitHub Repository

**Prompt 1 (my words):**
> Please push my code to a public GitHub repository so graders will be able to clone it. Do not push my real .env to the GitHub repo. Do include both database files under data/ (the original and my working copy) so graders can run everything.
>
> _(attached: a screenshot of the expected file layout)_

**Follow-up prompt (my words):**
> it's created, go ahead and push

**What was lacking after the first prompt:** The repository could not be created from here — there
is no `gh` CLI on this machine and the only GitHub credential is one in the keychain that should not
be read out and used directly — so the work had to stop at a finished local commit until I created
the empty public repo myself and said so.

---

<!-- New problem sections get appended here as each problem is completed. -->
