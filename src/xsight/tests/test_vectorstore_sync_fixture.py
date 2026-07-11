"""Fixture test for stale-vector diffing (Milestone 4)."""

from xsight.vectorstore.core import build_point_id
from xsight.tests.vectorstore_sync_fixture import expected_point_ids

REPO_ID = 1


def main() -> None:
    # Simulate: repo used to have 3 chunks, one was removed (c.py::f3)
    old_chunk_ids = ["a.py::f1", "b.py::f2", "c.py::f3"]
    existing_ids = {build_point_id(REPO_ID, cid) for cid in old_chunk_ids}

    # Current repository state: c.py::f3 no longer exists
    current_chunk_ids = ["a.py::f1", "b.py::f2"]
    expected_ids = expected_point_ids(REPO_ID, current_chunk_ids)

    stale = existing_ids - expected_ids
    assert stale == {build_point_id(REPO_ID, "c.py::f3")}, f"expected only c.py::f3 stale, got {stale}"

    # No removals -> no stale ids
    expected_all = expected_point_ids(REPO_ID, old_chunk_ids)
    assert existing_ids - expected_all == set(), "expected no stale ids when nothing removed"

    # Different repo_id must not collide (deterministic namespacing check)
    other_repo_ids = {build_point_id(2, cid) for cid in old_chunk_ids}
    assert existing_ids.isdisjoint(other_repo_ids), "point IDs must not collide across repos"

    print("All vectorstore-sync fixture assertions passed.")


if __name__ == "__main__":
    main()