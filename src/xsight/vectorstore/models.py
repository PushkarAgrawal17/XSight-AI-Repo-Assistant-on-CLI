from dataclasses import dataclass

@dataclass
class PointRecord:
    """A single vector + payload ready to be stored or returned from a query."""

    id: str
    vector: list[float]
    payload: dict
    score: float | None = None


@dataclass
class SearchResult:
    chunk_id: str
    content: str
    relative_path: str
    kind: str
    start_line: int
    end_line: int
    score: float