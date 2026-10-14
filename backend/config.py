"""Model and MCP wiring for the Campus Customs agent team.

Every agent on the team uses the same model, reached through the same Portkey
gateway, and the same MCP toolset. Centralising it here means the model is named
in exactly one place and the shop's tools are defined in exactly one place.

The Portkey key is read from `.env` and never logged. `build_model()` is lazy on
purpose: importing an agent module must not require a key, so the team can be
inspected, compiled and unit-tested offline.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server" / "server.py"
PROMPTS_DIR = BACKEND_DIR / "prompts"


def load_prompt(agent: str) -> str:
    """Read one agent's system prompt from `backend/prompts/<agent>.md`.

    The prompts live as markdown rather than Python so they can be read and
    edited without touching code; each file is self-contained, carrying the
    shared shop rules as well as that agent's own job.
    """
    path = PROMPTS_DIR / f"{agent}.md"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file for {agent!r} at {path}")
    return path.read_text(encoding="utf-8").strip()

# Most specific first; load_dotenv does not overwrite what is already set.
for _candidate in (
    BACKEND_DIR / ".env",
    PROJECT_ROOT / ".env",
    PROJECT_ROOT.parent / ".env",
):
    if _candidate.exists():
        load_dotenv(_candidate)

#: The one model the whole team runs on. Named here and nowhere else.
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")

#: Cost control. One ticket should not turn into an unbounded pile of model calls.
#:
#: These are *whole-team* budgets, not per-agent ones: delegated agents are run
#: with the Boss's usage object so one ticket has one bill. A four-agent run
#: needs roughly 20-25 requests, so 12 was too tight and cut the Boss off before
#: it could write its decision.
REQUEST_LIMIT = int(os.getenv("CC_REQUEST_LIMIT", "60"))
TOOL_CALLS_LIMIT = int(os.getenv("CC_TOOL_CALLS_LIMIT", "80"))
#: How many delegation hops deep the team may go before it must answer with
#: whatever it already has.
MAX_DELEGATION_DEPTH = int(os.getenv("CC_MAX_DELEGATION_DEPTH", "3"))


class AgentNotConfigured(RuntimeError):
    """PORTKEY_API_KEY is missing, so no model call can be made."""


def usage_limits():
    """Per-run ceilings applied to every agent."""
    from pydantic_ai.usage import UsageLimits

    return UsageLimits(request_limit=REQUEST_LIMIT, tool_calls_limit=TOOL_CALLS_LIMIT)


@lru_cache(maxsize=1)
def build_model():
    """A PydanticAI model bound to an AsyncOpenAI client pointed at Portkey.

    The Portkey key goes in twice: as the OpenAI bearer token and in the
    ``x-portkey-api-key`` header, which is what the gateway expects.
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise AgentNotConfigured(
            "PORTKEY_API_KEY is not set. Add it to the .env file at the repository "
            "root; it is a secret and must not be committed or printed."
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


#: Tools an agent may never call. `record_payment` moves real money, and the
#: rule for this project is that agents prepare a payment and a human approves
#: it — so the dashboard's approve route calls that tool through its own MCP
#: client, and agents are blocked here rather than merely asked not to.
AGENT_BLOCKED_TOOLS = {"record_payment"}


async def _log_and_guard_tool_call(ctx, call_tool, name, args):
    """Wrap every MCP tool call: block spending, and log the rest for the board.

    The agent's own name is pulled off the run context so the dashboard can show
    which teammate reached for which tool, rather than an unattributed list.
    """
    import events

    agent = ""
    try:
        agent = getattr(getattr(ctx, "agent", None), "name", "") or ""
    except Exception:  # introspection must never break a tool call
        agent = ""

    if name in AGENT_BLOCKED_TOOLS:
        events.record(
            "tool_call", agent=agent, tool=name,
            summary=f"Blocked: agents may not call {name}.",
            detail={"arguments": args, "blocked": True},
        )
        return {
            "recorded": False,
            "blocked": True,
            "reason": (
                "Agents cannot make payments. Propose it instead: put the amount, "
                "the kind ('invoice' or 'rent') and the ref_id in your reply's "
                "`money` field and set needs_human_approval to true. A human "
                "approves it on the dashboard, and that is what moves the cash."
            ),
        }

    result = await call_tool(name, args)
    events.record(
        "tool_call", agent=agent, tool=name,
        summary=f"called {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})",
        detail={"arguments": args},
    )
    return result


@lru_cache(maxsize=1)
def shop_toolset():
    """The Campus Customs MCP server, as a toolset every agent shares.

    Built once and reused, so the five agents talk to one server process and
    therefore to one consistent view of the database. Every call through it is
    logged to the event stream and screened against `AGENT_BLOCKED_TOOLS`.
    """
    from pydantic_ai.mcp import MCPToolset

    return MCPToolset(
        MCP_SERVER_PATH,
        id="campus-customs",
        process_tool_call=_log_and_guard_tool_call,
    )
