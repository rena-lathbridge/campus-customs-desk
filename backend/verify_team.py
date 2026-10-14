"""Structural check on the Campus Customs agent team — no model calls, no cost.

Confirms that all five agents build, that every agent is connected to every
other, that each one carries the shared MCP toolset, that they all run on the
same single model, and that the delegation guards actually refuse a cycle and a
too-deep hop. Run it with:

    python3 backend/verify_team.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import MODEL_NAME  # noqa: E402
from models import TEAM, TeamDeps  # noqa: E402
from team import ROLES, _make_delegate_tool, build_team  # noqa: E402


async def main() -> int:
    agents = build_team()
    failures: list[str] = []

    print(f"model in use: {MODEL_NAME}")
    print(f"agents built: {', '.join(sorted(agents))}\n")

    if set(agents) != set(TEAM):
        failures.append(f"roster mismatch: {sorted(agents)} != {sorted(TEAM)}")

    # Every agent reaches every other agent, and never itself.
    for name, agent in agents.items():
        # _function_toolset is where Agent.tool() registrations land.
        tool_names = set(agent._function_toolset.tools)
        expected = {f"ask_{t}" for t in TEAM if t != name}
        missing = expected - tool_names
        if missing:
            failures.append(f"{name} is missing delegate tools: {sorted(missing)}")
        if f"ask_{name}" in tool_names:
            failures.append(f"{name} can delegate to itself")
        print(f"  {name:<17} delegates to {len(expected)}: "
              f"{', '.join(sorted(t.removeprefix('ask_') for t in expected))}")

    # One shared MCP toolset, one shared model.
    print()
    for name, agent in agents.items():
        has_mcp = any(
            getattr(ts, "id", None) == "campus-customs"
            for ts in getattr(agent, "toolsets", [])
        )
        print(f"  {name:<17} MCP toolset attached: {has_mcp}")
        if not has_mcp:
            failures.append(f"{name} has no campus-customs MCP toolset")

    models = {str(getattr(a.model, "model_name", a.model)) for a in agents.values()}
    print(f"\n  distinct models across the team: {models}")
    if models != {MODEL_NAME}:
        failures.append(f"expected every agent on {MODEL_NAME}, found {models}")

    # The two delegation guards, exercised directly.
    print("\nguards:")
    tool = _make_delegate_tool("inventory", agents)

    class Ctx:
        def __init__(self, deps):
            self.deps = deps
            self.usage = None

    cycle = await tool(Ctx(TeamDeps(chain=["boss", "inventory"], depth=1)), "q")
    print(f"  revisit refused: {not cycle['delegated']}  -> {cycle.get('reason','')[:60]}")
    if cycle["delegated"]:
        failures.append("delegating to an agent already in the chain was allowed")

    deep = await tool(Ctx(TeamDeps(chain=["boss"], depth=3, max_depth=3)), "q")
    print(f"  depth   refused: {not deep['delegated']}  -> {deep.get('reason','')[:60]}")
    if deep["delegated"]:
        failures.append("delegating past max_depth was allowed")

    print()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("All structural checks passed. No model calls were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
