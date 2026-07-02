from dataclasses import dataclass


@dataclass
class Chunk:
    id: str
    kind: str
    content: str
    relative_path: str
    start_line: int
    end_line: int