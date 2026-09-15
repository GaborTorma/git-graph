#!/usr/bin/env python3
"""git-graph-probe — eldobható MCP szerver EGYETLEN `ping` toollal.

Egyetlen kérdést hivatott eldönteni, mielőtt bárki a valódi git-graph MCP
szerverbe kezd:

    egy publikált Claude Artifact oldal el tud-e érni egy `host:<név>`
    hivatkozással olyan helyi MCP szervert, amit a `claude mcp add`
    regisztrált?

Ha igen → mehet a rendes szerver. Ha nem → az élő-gráf terv elesik, és nem kell
napokat beletenni.

A `ping` szándékosan ad vissza VÁLTOZÓ értékeket (hívásszámláló, időbélyeg),
hogy a lapon látszódjon: tényleg minden hívás új, nem cache-ből jön.

Eldobható: `claude mcp remove git-graph-probe` és a mappa törölhető.
"""
from __future__ import annotations

import datetime
import os
import platform
import sys

from mcp.server.mcpserver import MCPServer

# A nevet kívülről kapja, mert két példány fut: egyik a Claude Code
# regisztrációjából, másik a Claude Desktop configjából — a ping válaszából
# derül ki, MELYIK ér el az Artifact-oldalig.
NAME = os.environ.get("PROBE_NAME", "git-graph-probe")
ORIGIN = os.environ.get("PROBE_ORIGIN", "ismeretlen")

mcp = MCPServer(
    name=NAME,
    instructions="Kapcsolat-teszt: egyetlen ping tool, változó válasszal.",
)

_calls = 0


@mcp.tool(description="Kapcsolat-teszt. Visszaadja a szerver adatait és egy "
                      "hívásonként növekvő számlálót.")
def ping(message: str = "") -> dict:
    """A hívó által küldött üzenetet visszatükrözi, szerver-oldali kontextussal."""
    global _calls
    _calls += 1
    return {
        "pong": True,
        "echo": message,
        "call": _calls,                       # növekszik → látszik, hogy él
        "server": NAME,
        "origin": ORIGIN,   # "claude-code" vagy "claude-desktop"
        "pid": os.getpid(),
        "host": platform.node(),
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
