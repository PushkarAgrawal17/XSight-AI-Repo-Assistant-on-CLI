from dataclasses import dataclass


@dataclass(frozen=True)
class ImportEdge:
    source_module: str
    target_module: str