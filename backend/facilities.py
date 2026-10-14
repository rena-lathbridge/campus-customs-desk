"""The Facilities agent.

Owns the premises and the rent calendar. Narrow scope, high stakes.

Built lazily by `build_facilities_agent()` so that importing this module never needs a
Portkey key — the team can be compiled and inspected offline. The agent is given
the shared Campus Customs MCP toolset here; its delegate tools (`ask_...`, one
per teammate) are attached later by `team.py`, which is what gives the team full
connectivity without this module importing its peers.

Its system prompt is read at build time from `backend/prompts/facilities.md`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from config import build_model, load_prompt, shop_toolset
from models import TeamDeps, SpecialistReply


@lru_cache(maxsize=1)
def build_facilities_agent() -> Agent[TeamDeps, SpecialistReply]:
    """Return the Facilities agent, built once and reused."""
    return Agent(
        build_model(),
        name="facilities",
        deps_type=TeamDeps,
        output_type=SpecialistReply,
        instructions=load_prompt("facilities"),
        toolsets=[shop_toolset()],
        retries=2,
    )
