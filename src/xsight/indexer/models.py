"""Data contract for the indexer package."""

from dataclasses import dataclass


@dataclass
class IndexSummary:
    added: int
    updated: int
    removed: int
    unchanged: int
    total_files: int