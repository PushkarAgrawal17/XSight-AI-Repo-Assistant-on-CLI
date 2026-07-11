"""Fixture for verifying the changed-chunk filter used in `xsight init`."""

from xsight.chunker.models import Chunk


def make_chunk(relative_path: str, chunk_id: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        kind="function",
        content=f"Function: {chunk_id}\nModule: {relative_path}\ndef f(): pass",
        relative_path=relative_path,
        start_line=1,
        end_line=1,
    )