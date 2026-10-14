"""The Boss agent.

Runs the shop and closes tickets. The only agent that produces a decision
rather than advice.

Built lazily by `build_boss_agent()` so that importing this module never needs a
Portkey key — the team can be compiled and inspected offline. The agent is given
the shared Campus Customs MCP toolset here; its delegate tools (`ask_...`, one
per teammate) are attached later by `team.py`, which is what gives the team full
connectivity without this module importing its peers.

Its system prompt is read at build time from `backend/prompts/boss.md`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from config import build_model, load_prompt, shop_toolset
from models import TeamDeps, BossDecision


@lru_cache(maxsize=1)
def build_boss_agent() -> Agent[TeamDeps, BossDecision]:
    """Return the Boss agent, built once and reused."""
    return Agent(
        build_model(),
        name="boss",
        deps_type=TeamDeps,
        output_type=BossDecision,
        instructions=load_prompt("boss"),
        toolsets=[shop_toolset()],
        retries=2,
    )
