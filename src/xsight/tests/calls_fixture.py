"""Fixture ParsedModule objects for deterministic call-resolution testing.

Represents a small repo tree exercising every resolve_calls() behavior:

    main.py       -- module-level calls (same-module, cross-module, unresolved,
                       ambiguous, recursive) + a class exercising self.method()
    helper.py      -- cross-module target for `from helper import do_work`
    pkg/__init__.py + pkg/mod.py -- cross-module target for `import pkg.mod`
    shared.py, src/shared.py      -- same dotted name under both candidate
                                       roots, used for an ambiguous attribute call
"""

from xsight.parser.models import (
    ImportedName,
    ParsedCall,
    ParsedClass,
    ParsedFunction,
    ParsedImport,
    ParsedModule,
)

main = ParsedModule(
    relative_path="main.py",
    classes=[
        ParsedClass(
            id="main.py::MyClass",
            name="MyClass",
            start_line=20,
            end_line=23,
            base_classes=[],
        ),
    ],
    functions=[
        ParsedFunction(
            id="main.py::top_level_function",
            name="top_level_function",
            start_line=5,
            end_line=5,
            parent_id=None,
            is_method=False,
            calls=[
                # same-module bare call, appears twice -> must collapse to one edge
                ParsedCall(callee_name="foo", receiver=None, line=6),
                ParsedCall(callee_name="foo", receiver=None, line=7),
                # cross-module bare call via `from helper import do_work`
                ParsedCall(callee_name="do_work", receiver=None, line=8),
                # cross-module attribute call via `import pkg.mod`
                ParsedCall(callee_name="util", receiver="pkg.mod", line=9),
                # unresolved bare call -- no such name anywhere
                ParsedCall(callee_name="unresolved_bare", receiver=None, line=10),
                # unresolved attribute call -- "obj" is not a resolvable module
                ParsedCall(callee_name="method", receiver="obj", line=11),
                # ambiguous attribute call -- "shared" matches under both roots
                ParsedCall(callee_name="foo", receiver="shared", line=12),
            ],
        ),
        ParsedFunction(
            id="main.py::foo",
            name="foo",
            start_line=15,
            end_line=15,
            parent_id=None,
            is_method=False,
            # recursive call -- foo() calling itself, must produce a self-loop edge
            calls=[ParsedCall(callee_name="foo", receiver=None, line=16)],
        ),
        ParsedFunction(
            id="main.py::MyClass.method_a",
            name="method_a",
            start_line=21,
            end_line=21,
            parent_id="main.py::MyClass",
            is_method=True,
            calls=[ParsedCall(callee_name="method_b", receiver="self", line=22)],
        ),
        ParsedFunction(
            id="main.py::MyClass.method_b",
            name="method_b",
            start_line=23,
            end_line=23,
            parent_id="main.py::MyClass",
            is_method=True,
            calls=[],
        ),
    ],
    imports=[
        ParsedImport(
            module="helper",
            level=0,
            imported_names=[ImportedName(name="do_work", alias=None)],
            line=1,
        ),
        ParsedImport(module="pkg.mod", level=0, imported_names=[], line=2),
        ParsedImport(module="shared", level=0, imported_names=[], line=3),
    ],
)

helper = ParsedModule(
    relative_path="helper.py",
    classes=[],
    functions=[
        ParsedFunction(
            id="helper.py::do_work",
            name="do_work",
            start_line=1,
            end_line=1,
            parent_id=None,
            is_method=False,
            calls=[],
        ),
    ],
    imports=[],
)

pkg_init = ParsedModule(
    relative_path="pkg/__init__.py",
    classes=[],
    functions=[],
    imports=[],
)

pkg_mod = ParsedModule(
    relative_path="pkg/mod.py",
    classes=[],
    functions=[
        ParsedFunction(
            id="pkg/mod.py::util",
            name="util",
            start_line=1,
            end_line=1,
            parent_id=None,
            is_method=False,
            calls=[],
        ),
    ],
    imports=[],
)

shared_root = ParsedModule(
    relative_path="shared.py",
    classes=[],
    functions=[],
    imports=[],
)

shared_src = ParsedModule(
    relative_path="src/shared.py",
    classes=[],
    functions=[],
    imports=[],
)

# Order is significant: test_calls_fixture.py asserts the exact ordered
# output of resolve_calls() against this ordering.
FIXTURE_MODULES = [main, helper, pkg_init, pkg_mod, shared_root, shared_src]
