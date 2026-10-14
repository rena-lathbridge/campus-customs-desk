"""Data types shared by the Campus Customs agent team.

Three groups:

* **Dependencies** — `TeamDeps`, the object every agent carries through a run. It
  holds the ticket being worked, who has been consulted already, and the
  delegation depth, which is what stops the team talking to itself forever.
* **Evidence** — `Fact`, the shape an agent uses to cite a database value. The
  shop rule is that no number reaches a customer or a decision unless it came out
  of a tool, so facts carry the table and column they came from.
* **Answers** — `SpecialistReply` for the four specialists and `BossDecision` for
  the Boss, who is the only agent that closes a ticket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

#: The five agents on the team. Used for delegation routing and escalation.
AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

#: Every agent can reach every other agent, so the roster doubles as the routing
#: table — `team.py` builds one delegate tool per *other* agent from this list.
TEAM: tuple[AgentName, ...] = (
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
)


@dataclass
class TeamDeps:
    """What each agent carries with it for the length of one run.

    Attributes:
        ticket_id: The ticket being worked, when there is one.
        chain: Who has been consulted so far, in order, starting with whoever was
            asked first. A delegate tool refuses to call an agent already in this
            list, which is how a Boss -> Inventory -> Boss loop is prevented.
        depth: How many delegation hops deep this run is.
        max_depth: The hop limit. Past it, delegate tools refuse and tell the
            agent to answer with what it already has.
        approver: The human who has signed off on spending in this session.
            Empty means nobody has, and no agent may pay anything.
    """

    ticket_id: int | None = None
    chain: list[str] = field(default_factory=list)
    depth: int = 0
    max_depth: int = 3
    approver: str = ""

    def descend(self, to_agent: str) -> "TeamDeps":
        """Return the deps a delegated agent should run with: one hop deeper."""
        return TeamDeps(
            ticket_id=self.ticket_id,
            chain=[*self.chain, to_agent],
            depth=self.depth + 1,
            max_depth=self.max_depth,
            approver=self.approver,
        )


class Fact(BaseModel):
    """One value read out of the shop database, with its source attached.

    Agents are required to cite rather than assert. If a number has no `Fact`
    behind it, the shop rules say it should not have been stated.
    """

    table: str = Field(description="Database table the value came from, e.g. 'inventory'.")
    field_name: str = Field(description="Column name, e.g. 'qty'.")
    value: str = Field(description="The value as the tool returned it.")
    means: str = Field(description="One plain sentence on what this means for the shop.")


class MoneyImpact(BaseModel):
    """What a proposed action would do to the shop's cash.

    An agent fills this in to *propose* a payment. It never executes one: the
    approve route in `main.py` is what actually moves money, and it needs `kind`
    and `ref_id` to know which bill is being settled.
    """

    kind: Literal["invoice", "rent", "none"] = Field(
        default="none",
        description="What would be paid: 'invoice' for a supplier bill, 'rent' for "
        "the lease, or 'none' when the answer involves money but pays nothing.",
    )
    ref_id: int | None = Field(
        default=None,
        description="The invoice id when kind is 'invoice', the lease id when 'rent'.",
    )
    account: str = Field(default="checking", description="Which account it comes out of.")
    what: str = Field(
        default="",
        description="One short line a human can read before approving, e.g. "
        "'clear the overdue reprint bill from Bulldog Print Co'.",
    )
    amount: float = Field(description="Dollars moving, as a positive number.")
    leaves_available: float | None = Field(
        default=None,
        description="Cash left afterwards once every other commitment is counted.",
    )
    affordable: bool = Field(description="Whether the shop can cover this right now.")
    needs_human_approval: bool = Field(
        default=True,
        description="True whenever real money would move. Spending always needs a human.",
    )


class SpecialistReply(BaseModel):
    """The answer shape for Inventory, Accounting, Facilities and Customer Service."""

    answer: str = Field(description="The answer in plain language, for a person to read.")
    facts: list[Fact] = Field(
        default_factory=list,
        description="Every database value the answer leans on. Empty only if the "
        "answer genuinely needed no data.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Anything actually changed in the database, or empty if nothing was.",
    )
    money: MoneyImpact | None = Field(
        default=None, description="Filled in when the answer involves spending."
    )
    blocked_by: str = Field(
        default="",
        description="What stops this being finished, if anything. Empty when nothing does.",
    )
    unknown: str = Field(
        default="",
        description="Anything the database simply does not record, stated plainly "
        "rather than guessed. Empty when nothing was missing.",
    )
    consulted: list[str] = Field(
        default_factory=list, description="Other agents asked during this answer."
    )


class TeamStep(BaseModel):
    """One hop in the Boss's working: who was asked, and what came back."""

    agent: str = Field(description="Which teammate was asked.")
    asked: str = Field(description="The question put to them.")
    learned: str = Field(description="The useful part of what they said back.")


class BossDecision(BaseModel):
    """The Boss's closing answer on a ticket. Only the Boss produces one."""

    ticket_id: int | None = Field(default=None, description="Ticket this settles.")
    decision: str = Field(description="What the shop is going to do, in plain language.")
    reply_to_requester: str = Field(
        description="The message the person who raised the ticket should receive."
    )
    rationale: str = Field(description="Why this is the right call, citing the numbers.")
    steps: list[TeamStep] = Field(
        default_factory=list, description="Who was consulted and what they contributed."
    )
    facts: list[Fact] = Field(
        default_factory=list, description="The database values the decision rests on."
    )
    money: MoneyImpact | None = Field(
        default=None, description="Filled in when the decision involves spending."
    )
    needs_human_approval: bool = Field(
        default=False,
        description="True whenever money would move or a price would change.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="What could still go wrong, or what this decision costs elsewhere.",
    )
    unresolved: str = Field(
        default="", description="Anything left open, including data the shop does not hold."
    )
