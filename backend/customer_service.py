"""The Customer Service agent.

Owns the words that reach a person. Holds no numbers of its own.

Built lazily by `build_customer_service_agent()` so that importing this module never needs a
Portkey key — the team can be compiled and inspected offline. The agent is given
the shared Campus Customs MCP toolset here; its delegate tools (`ask_...`, one
per teammate) are attached later by `team.py`, which is what gives the team full
connectivity without this module importing its peers.

Its system prompt is read at build time from `backend/prompts/customer_service.md`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from config import build_model, load_prompt, shop_toolset
from models import TeamDeps, SpecialistReply


@lru_cache(maxsize=1)
def build_customer_service_agent() -> Agent[TeamDeps, SpecialistReply]:
    """Return the Customer Service agent, built once and reused."""
    return Agent(
        build_model(),
        name="customer_service",
        deps_type=TeamDeps,
        output_type=SpecialistReply,
        instructions=load_prompt("customer_service"),
        toolsets=[shop_toolset()],
        retries=2,
    )
