"""Build a repository knowledge graph from parsed modules.

Transforms the parser's IR (ParsedModule/ParsedClass/ParsedFunction) into a
self-contained NetworkX graph. Downstream consumers depend only on the graph
and its flattened node/edge attributes - not on parser dataclasses.

Phase 1 scope:
    Nodes: module, class, function
    Edges: contains (module->class, module->function, class->method)
           inherits (same-module base classes only)

Import edges are deferred to a future phase pending a proper repository-aware
import resolver (see Phase 1 handoff doc).
"""

import networkx as nx

from pathlib import Path
from xsight.parser.models import ParsedClass, ParsedFunction, ParsedModule


def build(modules: list[ParsedModule]) -> nx.MultiDiGraph:
    """Build the repository graph from a complete set of parsed modules.

    Construction happens in two passes: all nodes (and contains edges) are
    added first, then inheritance edges are resolved. This guarantees edge
    resolution never depends on traversal order.
    """
    graph = nx.MultiDiGraph()

    for module in modules:
        _add_module_nodes(graph, module)

    for module in modules:
        _add_inheritance_edges(graph, module)

    return graph


def _add_module_nodes(graph: nx.MultiDiGraph, module: ParsedModule) -> None:
    """Add a module's own node, plus all class/function nodes it contains,
    plus the contains edges linking them."""
    graph.add_node(
        module.relative_path,
        kind="module",
        name=Path(module.relative_path).stem,
        relative_path=module.relative_path,
    )

    for parsed_class in module.classes:
        _add_class_node(graph, parsed_class)
        graph.add_edge(module.relative_path, parsed_class.id, type="contains")

    for parsed_function in module.functions:
        _add_function_node(graph, parsed_function)
        owner_id = parsed_function.parent_id or module.relative_path
        graph.add_edge(owner_id, parsed_function.id, type="contains")


def _add_class_node(graph: nx.MultiDiGraph, parsed_class: ParsedClass) -> None:
    graph.add_node(
        parsed_class.id,
        kind="class",
        name=parsed_class.name,
        start_line=parsed_class.start_line,
        end_line=parsed_class.end_line,
        base_classes=parsed_class.base_classes,
    )


def _add_function_node(graph: nx.MultiDiGraph, parsed_function: ParsedFunction) -> None:
    graph.add_node(
        parsed_function.id,
        kind="function",
        name=parsed_function.name,
        start_line=parsed_function.start_line,
        end_line=parsed_function.end_line,
        parent_id=parsed_function.parent_id,
        is_method=parsed_function.is_method,
    )


def _add_inheritance_edges(graph: nx.MultiDiGraph, module: ParsedModule) -> None:
    """Add inherits edges for base classes defined in the same module.

    Base class names in the IR are unqualified (e.g. "Base"), so resolving
    them across modules would require import resolution, which Phase 1
    doesn't have. Restricting to same-module lookups guarantees every edge
    created here is unambiguous - a name collision across modules would
    otherwise mean guessing which class was meant, which we don't do.
    """
    classes_by_name = {parsed_class.name: parsed_class.id for parsed_class in module.classes}

    for parsed_class in module.classes:
        for base_name in parsed_class.base_classes:
            base_id = classes_by_name.get(base_name)
            if base_id is not None:
                graph.add_edge(parsed_class.id, base_id, type="inherits")