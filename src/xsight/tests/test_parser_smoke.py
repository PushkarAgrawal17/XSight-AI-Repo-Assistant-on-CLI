"""
Smoke test: run the parser against a real repository.

Not a correctness test (we don't know expected values in advance) —
just verifies the parser doesn't crash on real code and reports
plausible aggregate counts to eyeball.
"""

import sys
from pathlib import Path

from xsight.parser.core import parse
from xsight.scanner.core import scan


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m xsight.tests.test_parser_smoke <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)

    python_files = [f for f in result.snapshot.files if f.language == "python"]
    print(f"Found {len(python_files)} Python files under {repo_path}\n")

    total_classes = 0
    total_functions = 0
    total_imports = 0
    failures: list[tuple[str, Exception]] = []

    for scanned_file in python_files:
        absolute_path = repo_path / scanned_file.relative_path
        try:
            module = parse(absolute_path, scanned_file.relative_path)
        except Exception as e:
            failures.append((scanned_file.relative_path, e))
            continue

        total_classes += len(module.classes)
        total_functions += len(module.functions)
        total_imports += len(module.imports)

        print(
            f"{scanned_file.relative_path}: "
            f"{len(module.classes)} classes, "
            f"{len(module.functions)} functions, "
            f"{len(module.imports)} imports"
        )

    print("\n--- Summary ---")
    print(f"Files parsed successfully: {len(python_files) - len(failures)}/{len(python_files)}")
    print(f"Total classes:   {total_classes}")
    print(f"Total functions: {total_functions}")
    print(f"Total imports:   {total_imports}")

    if failures:
        print(f"\n--- Failures ({len(failures)}) ---")
        for path, err in failures:
            print(f"{path}: {type(err).__name__}: {err}")


if __name__ == "__main__":
    main()