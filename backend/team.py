"""Wires the five Campus Customs agents into a fully connected team.

Each agent is built on its own in its own module, knowing nothing about its
peers. This module imports all five and then hands every agent an `ask_<name>`
tool for each of the other four. That is what "full connectivity" means here:
any agent can delegate to any other, in either direction, including a specialist
pulling the Boss in when it cannot tell whose question it is.

Connectivity that complete would loop forever if nothing stopped it, so every
delegate tool enforces two guards before it calls anyone:

* **No revisiting.** An agent already in this run's chain cannot be asked again.
  That kills Boss -> Inventory -> Boss and every longer cycle with it.
* **A depth limit.** Past `TeamDeps.max_depth` hops, delegation is refused and
  the agent is told to answer with what it already has.

A refusal is returned to the model as an ordinary tool result, not raised. The
agent reads it, and the prompt tells it what to do next — answer with what it
has and say what is missing.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic_ai import Agent, RunContext

import events

from accounting import build_accounting_agent
from boss import build_boss_agent
from config import MAX_DELEGATION_DEPTH, usage_limits
from customer_service import build_customer_service_agent
from facilities import build_facilities_agent
from inventory import build_inventory_agent
from models import TEAM, BossDecision, TeamDeps

#: Who each agent is, in words the *other* agents see on the delegate tool.
ROLES: dict[str, str] = {
    "boss": "the Boss, who decides what the shop does and closes tickets",
    "inventory": "Inventory, who knows what is on the shelf and in what size",
    "accounting": "Accounting, who knows the money, the bills and the price floor",
    "facilities": "Facilities, who knows the lease, the rent and when it is due",
    "customer_service": "Customer Service, who writes the message the person receives",
}

_BUILDERS = {
    "boss": build_boss_agent,
    "inventory": build_inventory_agent,
    "accounting": build_accounting_agent,
    "facilities": build_facilities_agent,
    "customer_service": build_customer_service_agent,
}


def _make_delegate_tool(target: str, agents: dict[str, Agent]):
    """Build one `ask_<target>` tool: the agent loop's hop to a teammate."""

    async def ask_teammate(ctx: RunContext[TeamDeps], question: str) -> dict[str, Any]:
        deps: TeamDeps = ctx.deps

        if target in deps.chain:
            return {
                "delegated": False,
                "reason": (
                    f"{target} has already been consulted on this ticket. Use what "
                    f"they told you rather than asking again."
                ),
            }
        if deps.depth >= deps.max_depth:
            return {
                "delegated": False,
                "reason": (
                    f"Delegation limit of {deps.max_depth} hops reached. Answer with "
                    f"what you already have and say plainly what is still missing."
                ),
            }

        events.record(
            "agent_started", agent=target,
            summary=f"asked: {question[:180]}",
            detail={"depth": deps.depth + 1, "chain": [*deps.chain, target]},
        )
        result = await agents[target].run(
            question,
            deps=deps.descend(target),
            usage=ctx.usage,
            usage_limits=usage_limits(),
        )
        reply = result.output
        events.record(
            "agent_replied", agent=target,
            summary=getattr(reply, "answer", "")[:400],
            detail=reply.model_dump(),
        )
        return {
            "delegated": True,
            "agent": target,
            "question": question,
            "reply": result.output.model_dump(),
        }

    return ask_teammate


@lru_cache(maxsize=1)
def build_team() -> dict[str, Agent]:
    """Build all five agents and connect every one to every other.

    Cached, and that is load-bearing: the agent builders are themselves cached,
    so calling this twice would try to register `ask_inventory` on the very same
    Agent object a second time and raise a tool-name conflict. One wiring, reused
    for every run.

    Returns:
        The five agents by name. Each has four `ask_<name>` delegate tools
        attached, so the delegation graph is complete in both directions.
    """
    agents: dict[str, Agent] = {name: builder() for name, builder in _BUILDERS.items()}

    for name, agent in agents.items():
        for target in TEAM:
            if target == name:
                continue  # nobody delegates to themselves
            agent.tool(
                _make_delegate_tool(target, agents),
                name=f"ask_{target}",
                description=(
                    f"Ask {ROLES[target]} a specific question and get their answer "
                    f"back. Include the ticket number and any sku, size or quantity "
                    f"in the question. Use this when the answer belongs to their job, "
                    f"not when you could look it up with a tool you already have."
                ),
            )
    return agents


def delegation_graph(agents: dict[str, Agent] | None = None) -> dict[str, list[str]]:
    """Who can ask whom. Used by the connectivity check in `verify_team.py`."""
    return {name: [t for t in TEAM if t != name] for name in (agents or dict.fromkeys(TEAM))}


async def run_ticket(
    ticket_id: int,
    instruction: str | None = None,
    approver: str = "",
    max_depth: int = MAX_DELEGATION_DEPTH,
) -> BossDecision:
    """Work one ticket end to end and return the Boss's decision.

    This is the outer loop. The Boss is given the ticket, and from there the
    agent loop runs itself: the model calls MCP tools to read the shop's data and
    `ask_<name>` tools to pull teammates in, each of which runs its own loop and
    returns a structured reply, until the Boss has enough to decide.

    Args:
        ticket_id: Which ticket to work, e.g. 101.
        instruction: Optional extra steer from a human.
        approver: Name of the human approving spending this session. Leave it
            empty and no agent may pay anything — they will recommend instead.
        max_depth: How many delegation hops are allowed.

    Returns:
        The Boss's `BossDecision`, including the reply the requester should get.
    """
    agents = build_team()
    deps = TeamDeps(
        ticket_id=ticket_id,
        chain=["boss"],
        depth=0,
        max_depth=max_depth,
        approver=approver,
    )

    task = f"Work ticket {ticket_id} and decide what Campus Customs should do."
    if instruction:
        task += f"\n\nExtra instruction from a human: {instruction}"
    if approver:
        task += f"\n\nA human approver is available for this session: {approver}."
    else:
        task += (
            "\n\nNo human approver has been named this session, so no money may be "
            "paid. Recommend instead, and say what needs approving."
        )

    result = await agents["boss"].run(
        task, deps=deps, usage_limits=usage_limits()
    )
    return result.output
