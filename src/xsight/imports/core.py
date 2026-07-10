"""Import resolution: resolves parsed import statements to concrete module
paths within the repository.

Pure function - no filesystem access, no NetworkX dependency. Consumes the
full ParsedModule list because resolution requires repository-wide context
(package roots, sibling modules) that a single module cannot provide on its
own.

Resolution policy: "skip rather than guess". Unresolved (external / not
found) and ambiguous (matches under multiple candidate roots) imports are
both silently omitted - no edge is ever created without certainty.

Self-loops (a module "importing itself", e.g. `from . import y` inside that
package's own __init__.py) are filtered - they're an artifact of collapsing
symbol-level imports to module-level edges, not a meaningful relationship.
"""

from xsight.imports.models import ImportEdge
from xsight.parser.models import ParsedImport, ParsedModule


def resolve_imports(modules: list[ParsedModule]) -> list[ImportEdge]:
    module_paths = {module.relative_path for module in modules}
    roots = _candidate_roots(module_paths)

    seen: set[ImportEdge] = set()
    ordered: list[ImportEdge] = []

    for module in modules:
        for imp in module.imports:
            target = _resolve_import(module.relative_path, imp, module_paths, roots)
            if target is None or target == module.relative_path:
                continue
            edge = ImportEdge(source_module=module.relative_path, target_module=target)
            if edge not in seen:
                seen.add(edge)
                ordered.append(edge)

    return ordered


def resolve_absolute_module(dotted_path: str, modules: list[ParsedModule]) -> str | None:
    """Resolve an absolute dotted path to a concrete module's relative_path.
    Reuses the same resolution logic as resolve_imports()."""
    module_paths = {m.relative_path for m in modules}
    roots = _candidate_roots(module_paths)
    return _resolve_absolute(dotted_path, module_paths, roots)


def resolve_import_target(
    source_path: str, imp: ParsedImport, modules: list[ParsedModule]
) -> str | None:
    """Resolve a single ParsedImport statement to a concrete module's
    relative_path. Reuses the same resolution logic as resolve_imports()."""
    module_paths = {m.relative_path for m in modules}
    roots = _candidate_roots(module_paths)
    return _resolve_import(source_path, imp, module_paths, roots)


def _candidate_roots(module_paths: set[str]) -> list[str]:
    roots = [""]
    if any(path.startswith("src/") for path in module_paths):
        roots.append("src")
    return roots


def _resolve_import(
    source_path: str,
    imp: ParsedImport,
    module_paths: set[str],
    roots: list[str],
) -> str | None:
    if imp.level == 0:
        if imp.module is None:
            return None
        return _resolve_absolute(imp.module, module_paths, roots)
    return _resolve_relative(source_path, imp, module_paths)



def _resolve_absolute(module: str, module_paths: set[str], roots: list[str]) -> str | None:
    parts = module.split(".")
    matches: set[str] = set()

    for root in roots:
        resolved = _resolve_absolute_under_root(root, parts, module_paths)
        if resolved is not None:
            matches.add(resolved)

    if len(matches) == 1:
        return next(iter(matches))
    return None

def _resolve_absolute_under_root(root: str, parts: list[str], module_paths: set[str]) -> str | None:
    prefix_root = [root] if root else []

    # Namespace-package check applies only to real package segments (the
    # dotted parts), never to the layout root ("" or "src") itself.
    for i in range(1, len(parts)):
        init_path = "/".join(prefix_root + parts[:i]) + "/__init__.py"
        if init_path not in module_paths:
            return None

    prefix = "/".join(p for p in prefix_root + parts if p)

    module_file = prefix + ".py"
    if module_file in module_paths:
        return module_file

    package_init = prefix + "/__init__.py"
    if package_init in module_paths:
        return package_init

    return None

def _resolve_relative(source_path: str, imp: ParsedImport, module_paths: set[str]) -> str | None:
    # Package containing the importing module: dropping the filename gives the
    # enclosing package's path segments, whether the source is a plain module
    # (pkg/sub/mod.py -> pkg/sub) or the package's own __init__.py
    # (pkg/sub/__init__.py -> pkg/sub) - both cases mean the same thing.
    package_parts = source_path.split("/")[:-1]

    up = imp.level - 1
    if up > len(package_parts):
        return None
    base = package_parts[: len(package_parts) - up] if up > 0 else package_parts

    prefix_parts = base + imp.module.split(".") if imp.module else base
    if not prefix_parts:
        return None

    return _resolve_prefix(prefix_parts, module_paths)


def _resolve_prefix(prefix_parts: list[str], module_paths: set[str]) -> str | None:
    """Resolve a fully-split path (root + package segments already combined)
    to a concrete module file, or None if unresolved/namespace-package."""
    # Every intermediate package segment must have an __init__.py - excludes
    # namespace packages, which Phase 2 explicitly does not resolve.
    for i in range(1, len(prefix_parts)):
        init_path = "/".join(prefix_parts[:i]) + "/__init__.py"
        if init_path not in module_paths:
            return None

    prefix = "/".join(p for p in prefix_parts if p)

    module_file = prefix + ".py"
    if module_file in module_paths:
        return module_file

    package_init = prefix + "/__init__.py"
    if package_init in module_paths:
        return package_init

    return None