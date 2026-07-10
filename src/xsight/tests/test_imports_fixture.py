"""
Deterministic import resolver regression test.

Runs resolve_imports() against FIXTURE_MODULES (hand-constructed
ParsedModule objects, not run through the real parser) and asserts the
exact ImportEdge list it should produce.
"""

from xsight.imports.core import resolve_imports
from xsight.imports.models import ImportEdge
from xsight.tests.imports_fixture import FIXTURE_MODULES


def main() -> None:
    edges = resolve_imports(FIXTURE_MODULES)

    # ---- exact expected output, in order ----
    expected = [
        ImportEdge(source_module="pkg/mod.py", target_module="pkg/__init__.py"),
        ImportEdge(source_module="pkg/mod.py", target_module="pkg/util.py"),
        ImportEdge(source_module="pkg/sub/__init__.py", target_module="pkg/__init__.py"),
    ]
    assert edges == expected, f"expected {expected}, got {edges}"

    # ---- self-loop filtering ----
    # pkg/__init__.py's own `from . import something` must not appear as an edge
    assert not any(e.source_module == "pkg/__init__.py" for e in edges), (
        "self-loop edge from pkg/__init__.py should have been filtered"
    )

    # ---- duplicate collapsing ----
    # pkg/mod.py had two identical `from . import util` statements -- exactly
    # one edge to pkg/__init__.py, not two
    to_pkg_init = [e for e in edges if e.target_module == "pkg/__init__.py" and e.source_module == "pkg/mod.py"]
    assert len(to_pkg_init) == 1, f"expected duplicate imports to collapse, got {to_pkg_init}"

    # ---- module resolution (foo.py) vs package resolution (__init__.py) ----
    assert ImportEdge("pkg/mod.py", "pkg/util.py") in edges, "module (foo.py) resolution failed"
    assert ImportEdge("pkg/mod.py", "pkg/__init__.py") in edges, "package (__init__.py) resolution failed"

    # ---- relative import ascending two levels ----
    assert ImportEdge("pkg/sub/__init__.py", "pkg/__init__.py") in edges, (
        "relative import with level=2 did not resolve correctly"
    )

    # ---- multiple modules importing the same target ----
    importers_of_pkg_init = {e.source_module for e in edges if e.target_module == "pkg/__init__.py"}
    assert importers_of_pkg_init == {"pkg/mod.py", "pkg/sub/__init__.py"}, importers_of_pkg_init

    # ---- namespace package rejection ----
    assert not any(e.source_module == "other/importer.py" and "nspkg" in e.target_module for e in edges), (
        "namespace package (missing __init__.py) should not resolve"
    )

    # ---- unresolved / external import rejection ----
    assert not any(e.source_module == "other/importer.py" and "numpy" in e.target_module for e in edges), (
        "external import (numpy) should not resolve to anything"
    )
    # other/importer.py has two unresolvable imports and zero resolvable ones
    assert not any(e.source_module == "other/importer.py" for e in edges)

    # ---- ambiguous root rejection ----
    assert not any(e.source_module == "other/ambiguous_importer.py" for e in edges), (
        "import matching both '' and 'src' roots should be skipped as ambiguous"
    )

    # ---- modules with no imports produce no edges ----
    assert not any(e.source_module == "pkg/util.py" for e in edges)
    assert not any(e.source_module == "nspkg/mod.py" for e in edges)
    assert not any(e.source_module in ("shared.py", "src/shared.py") for e in edges)

    # ---- empty input ----
    assert resolve_imports([]) == []

    print("All assertions passed.")
    print(f"  edges resolved: {len(edges)}")
    for e in edges:
        print(f"    {e.source_module} -> {e.target_module}")


if __name__ == "__main__":
    main()