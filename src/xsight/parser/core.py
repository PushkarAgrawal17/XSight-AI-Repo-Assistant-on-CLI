from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from xsight.parser.models import (
    ImportedName,
    ParsedClass,
    ParsedCall,
    ParsedFunction,
    ParsedImport,
    ParsedModule,
)

_PY_LANGUAGE = Language(tspython.language())

_FUNCTION_NODE_TYPES = ("function_definition", "async_function_definition")


def build_symbol_id(relative_path: str, name: str, parent_name: str | None = None) -> str:
    qualified = f"{parent_name}.{name}" if parent_name else name
    return f"{relative_path}::{qualified}"


def parse(file_path: Path, relative_path: str) -> ParsedModule:
    source = file_path.read_bytes()

    parser = Parser(_PY_LANGUAGE)
    tree = parser.parse(source)

    classes: list[ParsedClass] = []
    functions: list[ParsedFunction] = []
    imports: list[ParsedImport] = []

    for raw_node in tree.root_node.named_children:
        node = _unwrap_decorated(raw_node)

        if node.type == "class_definition":
            parsed_class = _parse_class(node, source, relative_path)
            classes.append(parsed_class)
            functions.extend(_parse_methods(node, source, relative_path, parsed_class))
        elif node.type in _FUNCTION_NODE_TYPES:
            functions.append(_parse_function(node, source, relative_path, parent=None))
        elif node.type in ("import_statement", "import_from_statement"):
            imports.extend(_parse_import(node, source))

    return ParsedModule(
        relative_path=relative_path,
        classes=classes,
        functions=functions,
        imports=imports,
    )


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8")


def _unwrap_decorated(node: Node) -> Node:
    """Decorated defs wrap the real class/function node one level deep.
    We don't capture decorator metadata (out of scope) but must not skip
    the symbol underneath."""
    if node.type == "decorated_definition":
        inner = node.child_by_field_name("definition")
        assert inner is not None
        return inner
    return node


def _parse_class(node: Node, source: bytes, relative_path: str) -> ParsedClass:
    name_node = node.child_by_field_name("name")
    name = _text(name_node, source)

    base_classes: list[str] = []
    superclasses_node = node.child_by_field_name("superclasses")
    if superclasses_node is not None:
        for arg in superclasses_node.named_children:
            base_classes.append(_text(arg, source))

    return ParsedClass(
        id=build_symbol_id(relative_path, name),
        name=name,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        base_classes=base_classes,
    )


def _parse_methods(
    class_node: Node, source: bytes, relative_path: str, parsed_class: ParsedClass
) -> list[ParsedFunction]:
    methods: list[ParsedFunction] = []
    body_node = class_node.child_by_field_name("body")
    if body_node is None:
        return methods

    for raw_child in body_node.named_children:
        child = _unwrap_decorated(raw_child)
        if child.type in _FUNCTION_NODE_TYPES:
            methods.append(
                _parse_function(child, source, relative_path, parent=parsed_class)
            )
    return methods


def _parse_function(
    node: Node, source: bytes, relative_path: str, parent: ParsedClass | None
) -> ParsedFunction:
    name_node = node.child_by_field_name("name")
    name = _text(name_node, source)

    if parent is not None:
        symbol_id = build_symbol_id(relative_path, name, parent_name=parent.name)
    else:
        symbol_id = build_symbol_id(relative_path, name)

    body_node = node.child_by_field_name("body")
    calls = _parse_calls(body_node, source) if body_node is not None else []

    return ParsedFunction(
        id=symbol_id,
        name=name,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        parent_id=parent.id if parent is not None else None,
        is_method=parent is not None,
        calls=calls,
    )

def _parse_import(node: Node, source: bytes) -> list[ParsedImport]:
    line = node.start_point[0] + 1

    if node.type == "import_statement":
        # import x
        # import x.y
        # import x as y   (module alias — not represented in current IR, dropped)
        # import x, y
        results: list[ParsedImport] = []
        for child in node.named_children:
            if child.type in ("dotted_name", "identifier"):
                results.append(
                    ParsedImport(
                        module=_text(child, source),
                        level=0,
                        imported_names=[],
                        line=line,
                    )
                )
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                results.append(
                    ParsedImport(
                        module=_text(name_node, source),
                        level=0,
                        imported_names=[],
                        line=line,
                    )
                )
        return results

    # from x import y
    # from x import y as z, w
    # from . import y
    # from .pkg import y
    module_node = node.child_by_field_name("module_name")

    if module_node is None:
        module = None
        level = 1
    else:
        raw_module = _text(module_node, source)

        level = len(raw_module) - len(raw_module.lstrip("."))
        module = raw_module.lstrip(".")

        if module == "":
            module = None

    imported_names: list[ImportedName] = []
    for child in node.named_children:
        if child.type == "dotted_name" and child != module_node:
            imported_names.append(ImportedName(name=_text(child, source), alias=None))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            imported_names.append(
                ImportedName(name=_text(name_node, source), alias=_text(alias_node, source))
            )
        elif child.type == "wildcard_import":
            imported_names.append(ImportedName(name="*", alias=None))

    return [ParsedImport(
                module=module,
                level=level,
                imported_names=imported_names,
                line=line,
    )]

def _parse_calls(node: Node, source: bytes) -> list[ParsedCall]:
    """Recursively find every call expression within a function/method body.

    Unlike the top-level symbol walk, this must descend arbitrarily deep
    (calls can appear inside if/for/try/etc.), so it walks all descendants
    rather than just named_children.
    """
    calls: list[ParsedCall] = []
    for child in node.named_children:
        if child.type == "call":
            parsed_call = _parse_call(child, source)
            if parsed_call is not None:
                calls.append(parsed_call)
        calls.extend(_parse_calls(child, source))
    return calls


def _parse_call(node: Node, source: bytes) -> ParsedCall | None:
    function_node = node.child_by_field_name("function")
    line = node.start_point[0] + 1

    if function_node.type == "identifier":
        return ParsedCall(callee_name=_text(function_node, source), receiver=None, line=line)

    if function_node.type == "attribute":
        object_node = function_node.child_by_field_name("object")
        attribute_node = function_node.child_by_field_name("attribute")
        return ParsedCall(
            callee_name=_text(attribute_node, source),
            receiver=_text(object_node, source),
            line=line,
        )

    # function/subscript/etc. as the callee (e.g. foo()(), obj[0]()) - skip,
    # not a name or attribute we can meaningfully resolve later.
    return None