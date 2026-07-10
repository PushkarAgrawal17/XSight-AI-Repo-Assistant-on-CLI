"""Graph enrichment: writes relationship edges produced by upstream resolver
subsystems into an already-built graph.

Kept separate from graph/builder.py, which owns only initial graph
construction (nodes, contains, same-module inherits). Each future
relationship type (imports, calls, ...) gets its own thin add_*_edges
function here, so builder.py doesn't accumulate unrelated wiring logic.

Enrichment performs no resolution and no deduplication - both are the
producing resolver's responsibility. This module only writes edges.
"""

import networkx as nx

from xsight.imports.models import ImportEdge
from xsight.calls.models import CallEdge


def add_import_edges(graph: nx.MultiDiGraph, edges: list[ImportEdge]) -> None:
    for edge in edges:
        graph.add_edge(edge.source_module, edge.target_module, type="imports")


def add_calls_edges(graph: nx.MultiDiGraph, edges: list[CallEdge]) -> None:
    for edge in edges:
        graph.add_edge(edge.caller_id, edge.callee_id, type="calls")
