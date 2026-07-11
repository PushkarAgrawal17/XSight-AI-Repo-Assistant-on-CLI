"""Data contract for the indexer package."""

from dataclasses import dataclass


@dataclass
class IndexSummary:
    added: int
    updated: int
    removed: int
    unchanged: int
    total_files: int
    added_files: list[str]
    updated_files: list[str]
    removed_files: list[str]
