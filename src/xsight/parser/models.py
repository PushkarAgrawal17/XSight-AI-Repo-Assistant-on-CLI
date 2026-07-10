from dataclasses import dataclass


@dataclass
class ParsedClass:
    id: str
    name: str
    start_line: int
    end_line: int
    base_classes: list[str]


@dataclass
class ParsedCall:
    callee_name: str
    receiver: str | None
    line: int


@dataclass
class ParsedFunction:
    id: str
    name: str
    start_line: int
    end_line: int
    parent_id: str | None
    is_method: bool
    calls: list["ParsedCall"]


@dataclass
class ImportedName:
    name: str
    alias: str | None


@dataclass
class ParsedImport:
    module: str | None
    level: int
    imported_names: list[ImportedName]
    line: int


@dataclass
class ParsedModule:
    relative_path: str
    classes: list[ParsedClass]
    functions: list[ParsedFunction]
    imports: list[ParsedImport]