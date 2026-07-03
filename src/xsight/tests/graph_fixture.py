"""Fixture ParsedModule objects for deterministic graph builder testing."""

from xsight.parser.models import ParsedClass, ParsedFunction, ParsedModule

# module_a.py:
#   class Base: pass
#   class Derived(Base): pass
#       def method(self): pass
#   def top_level_function(): pass
module_a = ParsedModule(
    relative_path="module_a.py",
    classes=[
        ParsedClass(
            id="module_a.py::Base",
            name="Base",
            start_line=1,
            end_line=1,
            base_classes=[],
        ),
        ParsedClass(
            id="module_a.py::Derived",
            name="Derived",
            start_line=2,
            end_line=3,
            base_classes=["Base"],
        ),
    ],
    functions=[
        ParsedFunction(
            id="module_a.py::Derived.method",
            name="method",
            start_line=3,
            end_line=3,
            parent_id="module_a.py::Derived",
            is_method=True,
        ),
        ParsedFunction(
            id="module_a.py::top_level_function",
            name="top_level_function",
            start_line=4,
            end_line=4,
            parent_id=None,
            is_method=False,
        ),
        ParsedFunction(
            id="module_a.py::Derived.helper",
            name="helper",
            start_line=10,
            end_line=10,
            parent_id="module_a.py::Derived",
            is_method=True,
        ),
    ],
    imports=[],
)

# module_b.py:
#   class Unrelated: pass  (inherits from "Base", but Base isn't defined here
#   -> must NOT produce an inherits edge, since resolution is same-module only)
module_b = ParsedModule(
    relative_path="module_b.py",
    classes=[
        ParsedClass(
            id="module_b.py::Unrelated",
            name="Unrelated",
            start_line=1,
            end_line=1,
            base_classes=["Base"],
        ),
    ],
    functions=[],
    imports=[],
)

FIXTURE_MODULES = [module_a, module_b]