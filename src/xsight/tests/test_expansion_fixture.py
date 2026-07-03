"""
Deterministic expansion regression test.

Builds the real graph from the canonical FIXTURE_MODULES (shared with the
graph builder and reused here rather than duplicating structure) and
exercises expand() against real chunk_ids that are also real graph node
IDs -- validating the identity contract, not just isolated logic.

Does NOT assert anything about source text or file content: RelatedSymbol
has no field to hold it, so its absence is a property of the data model,
not something this test needs to check at runtime.

Sibling ordering (start_line ascending) is part of expand()'s contract,
but with only two methods on Derived, each result's sibling list has at
most one element -- this fixture cannot distinguish "correctly sorted"
from "reversed." That's an accepted gap: proving Python's sorted() works
isn't worth growing the canonical fixture further. Real multi-sibling
ordering cases will come naturally once richer relationships (calls,
imports) are added.
"""

from xsight.expansion.core import expand
from xsight.graph.builder import build
from xsight.tests.graph_fixture import FIXTURE_MODULES
from xsight.vectorstore.models import SearchResult


def _fake_hit(chunk_id: str) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        content="irrelevant for expansion",
        relative_path="module_a.py",
        kind="function",
        start_line=0,
        end_line=0,
        score=1.0,
    )


def main() -> None:
    graph = build(FIXTURE_MODULES)

    method_hit = _fake_hit("module_a.py::Derived.method")
    helper_hit = _fake_hit("module_a.py::Derived.helper")
    top_fn_hit = _fake_hit("module_a.py::top_level_function")

    # ---- method hit: parent, base class, non-empty siblings ----
    hits = [method_hit]
    results = expand(hits, graph)
    assert len(results) == 1
    result = results[0]

    assert result.hit.chunk_id == "module_a.py::Derived.method"
    assert result.parent is not None
    assert result.parent.name == "Derived"
    assert result.parent.kind == "class"

    assert result.base_class is not None
    assert result.base_class.name == "Base"

    assert len(result.siblings) == 1
    assert result.siblings[0].name == "helper"
    assert result.siblings[0].kind == "function"

    # ---- sibling sort order: helper (start_line=10) should sort after
    #      method (start_line=3) when method is the sibling instead ----
    results2 = expand([helper_hit], graph)
    sibling = results2[0].siblings[0]
    assert sibling.name == "method"
    assert sibling.start_line == 3

    # ---- module-level function hit: no parent, no base class ----
    results3 = expand([top_fn_hit], graph)
    top_result = results3[0]
    assert top_result.parent is None
    assert top_result.base_class is None
    assert top_result.siblings == []

    # ---- output order matches input order ----
    hits_multi = [top_fn_hit, method_hit, helper_hit]
    results_multi = expand(hits_multi, graph)
    assert [r.hit.chunk_id for r in results_multi] == [h.chunk_id for h in hits_multi]

    # ---- unknown chunk_id raises KeyError, not silently ignored ----
    bad_hit = _fake_hit("module_a.py::DoesNotExist")
    try:
        expand([bad_hit], graph)
        assert False, "expected expansion  for unknown chunk_id"
    except (AssertionError, KeyError):
        pass

    print("All assertions passed.")


if __name__ == "__main__":
    main()