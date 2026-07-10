"""Fixture ParsedModule objects for deterministic import-resolution testing.

Represents a small repo tree exercising every resolver behavior:

    pkg/__init__.py     -- self-referential import (must be filtered)
    pkg/util.py          -- plain module, no imports
    pkg/mod.py            -- duplicate + package + module resolution
    pkg/sub/__init__.py   -- relative import ascending two levels
    nspkg/mod.py           -- package missing __init__.py (namespace package)
    other/importer.py       -- namespace-package + external unresolved imports
    other/ambiguous_importer.py -- import ambiguous across two roots
    shared.py, src/shared.py     -- same dotted name under both candidate roots
"""

from xsight.parser.models import ImportedName, ParsedImport, ParsedModule

pkg_init = ParsedModule(
    relative_path="pkg/__init__.py",
    classes=[],
    functions=[],
    imports=[
        # from . import something -- resolves to pkg/__init__.py itself (self-loop)
        ParsedImport(
            module=None,
            level=1,
            imported_names=[ImportedName(name="something", alias=None)],
            line=1,
        ),
    ],
)

pkg_util = ParsedModule(
    relative_path="pkg/util.py",
    classes=[],
    functions=[],
    imports=[],
)

pkg_mod = ParsedModule(
    relative_path="pkg/mod.py",
    classes=[],
    functions=[],
    imports=[
        # from . import util  -- resolves to pkg/__init__.py (package resolution)
        ParsedImport(
            module=None,
            level=1,
            imported_names=[ImportedName(name="util", alias=None)],
            line=1,
        ),
        # duplicate of the above (different line, same resolution) -- must collapse
        ParsedImport(
            module=None,
            level=1,
            imported_names=[ImportedName(name="util", alias=None)],
            line=5,
        ),
        # from .util import something -- resolves to pkg/util.py (module resolution)
        ParsedImport(
            module="util",
            level=1,
            imported_names=[ImportedName(name="something", alias=None)],
            line=6,
        ),
    ],
)

pkg_sub_init = ParsedModule(
    relative_path="pkg/sub/__init__.py",
    classes=[],
    functions=[],
    imports=[
        # from .. import util -- level=2, ascends past pkg.sub to pkg -> pkg/__init__.py
        ParsedImport(
            module=None,
            level=2,
            imported_names=[ImportedName(name="util", alias=None)],
            line=1,
        ),
    ],
)

nspkg_mod = ParsedModule(
    relative_path="nspkg/mod.py",
    classes=[],
    functions=[],
    imports=[],
)

importer = ParsedModule(
    relative_path="other/importer.py",
    classes=[],
    functions=[],
    imports=[
        # import nspkg.mod -- nspkg has no __init__.py -> namespace package, must skip
        ParsedImport(module="nspkg.mod", level=0, imported_names=[], line=1),
        # import numpy -- not part of the repo at all -> external, must skip
        ParsedImport(module="numpy", level=0, imported_names=[], line=2),
    ],
)

ambiguous_importer = ParsedModule(
    relative_path="other/ambiguous_importer.py",
    classes=[],
    functions=[],
    imports=[
        # import shared -- matches both shared.py and src/shared.py -> ambiguous, must skip
        ParsedImport(module="shared", level=0, imported_names=[], line=1),
    ],
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

# Order is significant: test_imports_fixture.py asserts the exact ordered
# output of resolve_imports() against this ordering.
FIXTURE_MODULES = [
    pkg_init,
    pkg_util,
    pkg_mod,
    pkg_sub_init,
    nspkg_mod,
    importer,
    ambiguous_importer,
    shared_root,
    shared_src,
]