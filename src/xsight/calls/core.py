"""Call resolution: resolves parsed call-site facts to concrete
function/method relationships within the repository.

Phase scope: same-module resolution only, mirroring how `inherits` edges
are resolved. Two call shapes are handled:

  - bare calls (receiver is None)   -> matched against module-level
    functions in the same module.
  - `self.method()` calls inside a method -> matched against sibling
    methods on the same class.

Everything else (attribute calls on arbitrary objects, calls through
variables, cross-module calls) is skipped - "skip rather than guess",
same policy already applied to inherits and imports. Cross-module call
resolution (via import edges) is a deliberate future increment, not
attempted here.

Pure function - no filesystem access, no NetworkX dependency.
"""

from xsight.calls.models import CallEdge
from xsight.imports.core import resolve_absolute_module, resolve_import_target
from xsight.parser.models import ParsedCall, ParsedFunction, ParsedModule


def resolve_calls(modules: list[ParsedModule]) -> list[CallEdge]:
    seen: set[CallEdge] = set()
    ordered: list[CallEdge] = []
    modules_by_path = {m.relative_path: m for m in modules}

    for module in modules:
        module_functions = {
            f.name: f.id for f in module.functions if f.parent_id is None
        }
        methods_by_class: dict[str, dict[str, str]] = {}
        for f in module.functions:
            if f.parent_id is not None:
                methods_by_class.setdefault(f.parent_id, {})[f.name] = f.id

        for function in module.functions:
            for call in function.calls:
                target = _resolve_call(
                    function, call, module_functions, methods_by_class, module, modules, modules_by_path
                )
                if target is None:
                    continue
                edge = CallEdge(caller_id=function.id, callee_id=target)
                if edge not in seen:
                    seen.add(edge)
                    ordered.append(edge)

    return ordered


def _resolve_call(
    function: ParsedFunction,
    call: ParsedCall,
    module_functions: dict[str, str],
    methods_by_class: dict[str, dict[str, str]],
    module: ParsedModule,
    modules: list[ParsedModule],
    modules_by_path: dict[str, ParsedModule],
) -> str | None:
    if call.receiver is None:
        same_module_target = module_functions.get(call.callee_name)
        if same_module_target is not None:
            return same_module_target
        return _resolve_cross_module_bare_call(call, module, modules, modules_by_path)

    if call.receiver == "self" and function.is_method:
        class_methods = methods_by_class.get(function.parent_id, {})
        return class_methods.get(call.callee_name)

    return _resolve_cross_module_attribute_call(call, modules, modules_by_path)



def _resolve_cross_module_bare_call(
    call: ParsedCall, module: ParsedModule, modules: list[ParsedModule], modules_by_path: dict[str, ParsedModule]
) -> str | None:
    matching_import = next(
        (
            imp
            for imp in module.imports
            if any(n.name == call.callee_name for n in imp.imported_names)
        ),
        None,
    )
    if matching_import is None:
        return None

    target_module = resolve_import_target(module.relative_path, matching_import, modules)
    if target_module is None:
        return None

    target = modules_by_path.get(target_module)
    if target is None:
        return None

    for f in target.functions:
        if f.parent_id is None and f.name == call.callee_name:
            return f.id
    return None


def _resolve_cross_module_attribute_call(
    call: ParsedCall, modules: list[ParsedModule], modules_by_path: dict[str, ParsedModule]
) -> str | None:
    target_module = resolve_absolute_module(call.receiver, modules)
    if target_module is None:
        return None

    target = modules_by_path.get(target_module)
    if target is None:
        return None

    for f in target.functions:
        if f.parent_id is None and f.name == call.callee_name:
            return f.id
    return None
