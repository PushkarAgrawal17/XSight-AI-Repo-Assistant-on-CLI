"""Fixture for verifying stale-vector identification (Milestone 4)."""

from xsight.vectorstore.core import build_point_id


def expected_point_ids(repo_id: int, chunk_ids: list[str]) -> set[str]:
    """Mirrors the expected-ID computation used in cli/commands/init.py."""
    return {build_point_id(repo_id, cid) for cid in chunk_ids}