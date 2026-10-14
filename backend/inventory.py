"""The Inventory agent.

Owns the shelf: what is in stock, by size, and what restocking would take.

Built lazily by `build_inventory_agent()` so that importing this module never needs a
Portkey key — the team can be compiled and inspected offline. The agent is given
the shared Campus Customs MCP toolset here; its delegate tools (`ask_...`, one
per teammate) are attached later by `team.py`, which is what gives the team full
connectivity without this module importing its peers.

Its system prompt is read at build time from `backend/prompts/inventory.md`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from config import build_model, load_prompt, shop_toolset
from models import TeamDeps, SpecialistReply


@lru_cache(maxsize=1)
def build_inventory_agent() -> Agent[TeamDeps, SpecialistReply]:
    """Return the Inventory agent, built once and reused."""
    return Agent(
        build_model(),
        name="inventory",
        deps_type=TeamDeps,
        output_type=SpecialistReply,
        instructions=load_prompt("inventory"),
        toolsets=[shop_toolset()],
        retries=2,
    )
