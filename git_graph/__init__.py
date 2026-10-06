"""git-graph: élő, Git Graph-szerű commit-gráf Artifactként a Claude appban (lásd `cli`)."""
from __future__ import annotations

import os
from pathlib import Path

# A kód gyökere: a pluginban és a working tree-ben a csomag szülője, a stabil
# másolatnál (`~/.git-graph/bin/git-graph`, egy zip — `install.stable_bundle`) a
# `~/.git-graph`. Mellette a `page/` és a `.claude-plugin/plugin.json`.
_PARENT = Path(os.path.abspath(__file__)).parent.parent
ROOT = _PARENT.parent.parent if _PARENT.is_file() else _PARENT

MCP_NAME = "git-graph"        # a Claude app configjában ez a kulcs → a lapon host:git-graph
