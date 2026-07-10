from dataclasses import dataclass

from xsight.vectorstore.models import SearchResult


@dataclass
class RelatedSymbol:
    name: str
    kind: str
    start_line: int
    end_line: int


@dataclass
class ExpandedResult:
    hit: SearchResult
    parent: RelatedSymbol | None
    siblings: list[RelatedSymbol]
    base_class: RelatedSymbol | None
    calls: list[RelatedSymbol]
    called_by: list[RelatedSymbol]
