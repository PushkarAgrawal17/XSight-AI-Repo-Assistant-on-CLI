from dataclasses import dataclass

from xsight.chunker.models import Chunk


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float]