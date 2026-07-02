"""
Deterministic parser regression test.

Run against parser_fixture.py, which intentionally exercises every
construct the Phase 1 Python parser supports. Not a test of Python —
a test that parse() produces the exact IR we've designed.
"""

from pathlib import Path

from xsight.parser.core import parse

FIXTURE_PATH = Path(__file__).parent / "parser_fixture.py"
RELATIVE_PATH = "parser_fixture.py"


def main() -> None:
    module = parse(FIXTURE_PATH, RELATIVE_PATH)

    # ---- counts ----
    assert len(module.classes) == 3, f"expected 3 classes, got {len(module.classes)}"
    assert len(module.functions) == 4, f"expected 4 functions, got {len(module.functions)}"
    assert len(module.imports) == 7, f"expected 7 imports, got {len(module.imports)}"

    # ---- classes ----
    by_name = {c.name: c for c in module.classes}
    assert set(by_name) == {"Base", "Derived", "DecoratedClass"}

    base = by_name["Base"]
    assert base.id == "parser_fixture.py::Base"
    assert base.base_classes == []
    assert base.start_line == 18 and base.end_line == 19

    derived = by_name["Derived"]
    assert derived.id == "parser_fixture.py::Derived"
    assert derived.base_classes == ["Base"], "inheritance not extracted correctly"
    assert derived.start_line == 22 and derived.end_line == 28

    decorated_class = by_name["DecoratedClass"]
    assert decorated_class.id == "parser_fixture.py::DecoratedClass"
    assert decorated_class.base_classes == []
    # decorated_definition wraps the class node; start_line should be the
    # class itself (line 32), not the decorator (line 31) — we don't
    # capture decorator metadata, so the unwrapped node's own span is used.
    assert decorated_class.start_line == 32 and decorated_class.end_line == 33

    # ---- functions ----
    by_id = {f.id: f for f in module.functions}

    top_fn = by_id["parser_fixture.py::top_level_function"]
    assert top_fn.name == "top_level_function"
    assert top_fn.parent_id is None
    assert top_fn.is_method is False
    assert top_fn.start_line == 10 and top_fn.end_line == 11

    async_fn = by_id["parser_fixture.py::top_level_async_function"]
    assert async_fn.name == "top_level_async_function"
    assert async_fn.parent_id is None
    assert async_fn.is_method is False
    assert async_fn.start_line == 14 and async_fn.end_line == 15

    normal_method = by_id["parser_fixture.py::Derived.normal_method"]
    assert normal_method.name == "normal_method"
    assert normal_method.parent_id == "parser_fixture.py::Derived"
    assert normal_method.is_method is True
    assert normal_method.start_line == 23 and normal_method.end_line == 24

    decorated_method = by_id["parser_fixture.py::Derived.decorated_method"]
    assert decorated_method.name == "decorated_method"
    assert decorated_method.parent_id == "parser_fixture.py::Derived"
    assert decorated_method.is_method is True
    # same reasoning as decorated_class: span is the function itself (27-28),
    # decorator line (26) is not included since we don't capture it.
    assert decorated_method.start_line == 27 and decorated_method.end_line == 28

    # ---- imports ----
    imports_by_module = {imp.module: imp for imp in module.imports}
    assert set(imports_by_module) == {
        "os", "numpy", "collections", "typing", "..parser.tests", ".pkg", "mymodule",
    }

    # import os
    os_import = imports_by_module["os"]
    assert os_import.imported_names == []
    assert os_import.line == 1

    # import numpy as np  -> module aliasing dropped (known Phase 1 gap)
    numpy_import = imports_by_module["numpy"]
    assert numpy_import.imported_names == []
    assert numpy_import.line == 2

    # from collections import OrderedDict
    collections_import = imports_by_module["collections"]
    assert len(collections_import.imported_names) == 1
    assert collections_import.imported_names[0].name == "OrderedDict"
    assert collections_import.imported_names[0].alias is None
    assert collections_import.line == 3

    # from typing import List, Dict as D  (mixed aliased/non-aliased names)
    typing_import = imports_by_module["typing"]
    typing_names = {n.name: n.alias for n in typing_import.imported_names}
    assert typing_names == {"List": None, "Dict": "D"}
    assert typing_import.line == 4

    # from ..parser.tests import sibling
    relative_import = imports_by_module["..parser.tests"]
    assert len(relative_import.imported_names) == 1
    assert relative_import.imported_names[0].name == "sibling"
    assert relative_import.imported_names[0].alias is None
    assert relative_import.line == 5

    # from .pkg import helper
    pkg_import = imports_by_module[".pkg"]
    assert len(pkg_import.imported_names) == 1
    assert pkg_import.imported_names[0].name == "helper"
    assert pkg_import.line == 6

    # from mymodule import *
    wildcard_import = imports_by_module["mymodule"]
    assert len(wildcard_import.imported_names) == 1
    assert wildcard_import.imported_names[0].name == "*"
    assert wildcard_import.imported_names[0].alias is None
    assert wildcard_import.line == 7

    print("All assertions passed.")
    print(f"  classes:   {len(module.classes)}")
    print(f"  functions: {len(module.functions)}")
    print(f"  imports:   {len(module.imports)}")


if __name__ == "__main__":
    main()