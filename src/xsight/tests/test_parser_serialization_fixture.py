"""Fixture test: ParsedModule <-> JSON round-trip via parser.core.to_json/from_json."""

from xsight.parser.core import from_json, to_json
from xsight.parser.models import (
    ImportedName, ParsedCall, ParsedClass, ParsedFunction, ParsedImport, ParsedModule,
)


def main() -> None:
    module = ParsedModule(
        relative_path="pkg/mod.py",
        classes=[ParsedClass(id="pkg/mod.py::Foo", name="Foo", start_line=1, end_line=5, base_classes=["Base"])],
        functions=[
            ParsedFunction(
                id="pkg/mod.py::Foo.bar", name="bar", start_line=2, end_line=4,
                parent_id="pkg/mod.py::Foo", is_method=True,
                calls=[ParsedCall(callee_name="helper", receiver="self", line=3)],
            )
        ],
        imports=[
            ParsedImport(
                module="os", level=0,
                imported_names=[ImportedName(name="path", alias="p")], line=1,
            )
        ],
    )

    restored = from_json(to_json(module))
    assert restored == module, f"round-trip mismatch:\n{restored}\nvs\n{module}"
    print("OK: ParsedModule JSON round-trip")


if __name__ == "__main__":
    main()