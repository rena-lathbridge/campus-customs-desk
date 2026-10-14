"""A live log of what the agent team is doing, for the dashboard to poll.

The board needs to show two things as a run unfolds: which agent is talking, and
which shop tool it reached for. Both land here.

Events are kept in a bounded in-memory ring and handed out by sequence number, so
the board asks for everything `since` the last number it saw rather than
re-reading the whole log. Nothing is persisted — a server restart starts a fresh
log, which is the right behaviour for something that exists to animate a board.

`current_run` is a context variable rather than an argument because the MCP
tool-call hook fires deep inside PydanticAI, far from any code of ours that knows
which ticket is being worked.
"""

from __future__ import annotations

import itertools
import threading
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

EventKind = Literal[
    "run_started", "agent_started", "agent_replied", "tool_call",
    "decision", "approval", "reset", "error",
]

MAX_EVENTS = 500

_seq = itertools.count(1)
_lock = threading.Lock()
_events: list["Event"] = []

#: (run_id, ticket_id) for whatever run is currently executing on this task.
current_run: ContextVar[tuple[str, int | None]] = ContextVar(
    "current_run", default=("", None)
)


@dataclass
class Event:
    seq: int
    at: str
    run_id: str
    ticket_id: int | None
    kind: EventKind
    agent: str = ""
    tool: str = ""
    summary: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def record(
    kind: EventKind,
    *,
    agent: str = "",
    tool: str = "",
    summary: str = "",
    detail: dict[str, Any] | None = None,
    run_id: str | None = None,
    ticket_id: int | None = None,
) -> Event:
    """Append one event and return it."""
    ctx_run, ctx_ticket = current_run.get()
    ev = Event(
        seq=next(_seq),
        at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        run_id=run_id if run_id is not None else ctx_run,
        ticket_id=ticket_id if ticket_id is not None else ctx_ticket,
        kind=kind,
        agent=agent,
        tool=tool,
        summary=summary,
        detail=detail or {},
    )
    with _lock:
        _events.append(ev)
        if len(_events) > MAX_EVENTS:
            del _events[: len(_events) - MAX_EVENTS]
    return ev


def since(seq: int = 0, limit: int = 200) -> list[dict[str, Any]]:
    """Every event newer than `seq`, oldest first."""
    with _lock:
        rows = [e for e in _events if e.seq > seq]
    return [e.as_dict() for e in rows[-limit:]]


def latest_seq() -> int:
    with _lock:
        return _events[-1].seq if _events else 0


def clear() -> None:
    """Drop the log. Used by the reset route so a fresh run starts clean."""
    with _lock:
        _events.clear()
