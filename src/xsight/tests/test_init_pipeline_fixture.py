"""Fixture test for the changed-file chunk filter (Milestone 2)."""

from xsight.tests.init_pipeline_fixture import make_chunk


def filter_changed_chunks(chunks, added_files, updated_files):
    """Mirrors the filter expression used in cli/commands/init.py."""
    changed_files = set(added_files) | set(updated_files)
    return [c for c in chunks if c.relative_path in changed_files]


def main() -> None:
    chunks = [
        make_chunk("a.py", "a.py::f1"),
        make_chunk("b.py", "b.py::f2"),
        make_chunk("c.py", "c.py::f3"),
    ]

    result = filter_changed_chunks(chunks, added_files=["c.py"], updated_files=["a.py"])
    result_ids = {c.id for c in result}
    assert result_ids == {"a.py::f1", "c.py::f3"}, f"expected a.py/c.py chunks, got {result_ids}"

    # unchanged file (b.py) excluded
    assert "b.py::f2" not in result_ids, "unchanged file's chunk should be excluded"

    # no changes -> empty result
    result_empty = filter_changed_chunks(chunks, added_files=[], updated_files=[])
    assert result_empty == [], f"expected empty list, got {result_empty}"

    # all changed -> full list preserved, in original order
    result_all = filter_changed_chunks(chunks, added_files=["a.py", "b.py", "c.py"], updated_files=[])
    assert [c.id for c in result_all] == ["a.py::f1", "b.py::f2", "c.py::f3"], (
        f"expected all chunks in original order, got {[c.id for c in result_all]}"
    )

    print("All init-pipeline filter fixture assertions passed.")


if __name__ == "__main__":
    main()