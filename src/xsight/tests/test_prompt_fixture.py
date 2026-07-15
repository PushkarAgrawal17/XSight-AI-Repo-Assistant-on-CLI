"""
Deterministic prompt-builder regression test.

Validates build_prompt()'s formatting contract: instruction-before-question
ordering, retrieval order preservation, per-block section presence/omission,
verbatim hit content, and no leakage of retrieval-implementation details
(scores, Qdrant, embeddings) into the prompt. Purely a string-formatting
stage with no external dependencies, so a fixture alone is sufficient --
no smoke test needed.

Assertions use substrings/structure rather than a full byte-for-byte
prompt comparison, since exact whitespace/wording is expected to evolve
without being a meaningful regression on its own.
"""

from xsight.chat.prompt import build_prompt
from xsight.chat.models import ChatTurn
from xsight.expansion.models import ExpandedResult, RelatedSymbol
from xsight.vectorstore.models import SearchResult

QUERY = "how does repository scanning work"


def _fake_hit(chunk_id: str, content: str) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        content=content,
        relative_path="module_a.py",
        kind="function",
        start_line=1,
        end_line=1,
        score=0.9,
    )


def _symbol_block(prompt: str, index: int) -> str:
    """Isolate a single '=== Retrieved Symbol N ===' block from the prompt."""
    marker = f"=== Retrieved Symbol {index} ==="
    start = prompt.index(marker)
    next_marker = f"=== Retrieved Symbol {index + 1} ==="
    end = prompt.index(next_marker) if next_marker in prompt else len(prompt)
    return prompt[start:end]


def main() -> None:
    hit_content_1 = "Method: Derived.method\nModule: module_a.py\ndef method(self):\n    pass"
    hit_content_2 = "Function: top_level_function\nModule: module_a.py\ndef top_level_function():\n    pass"

    result_1 = ExpandedResult(
        hit=_fake_hit("module_a.py::Derived.method", hit_content_1),
        parent=RelatedSymbol(name="Derived", kind="class", start_line=2, end_line=10),
        base_class=RelatedSymbol(name="Base", kind="class", start_line=1, end_line=1),
        siblings=[RelatedSymbol(name="helper", kind="function", start_line=10, end_line=10)],
        calls=[],
        called_by=[],
    )

    result_2 = ExpandedResult(
        hit=_fake_hit("module_a.py::top_level_function", hit_content_2),
        parent=None,
        base_class=None,
        siblings=[],
        calls=[],
        called_by=[],
    )

    prompt = build_prompt(QUERY, [result_1, result_2])

    # ---- instruction block before user question ----
    assert prompt.index("User question:") > 0
    instruction_end = prompt.index("User question:")
    assert "answer" in prompt[:instruction_end].lower()

    # ---- query appears exactly once ----
    expected_question = f"User question:\n{QUERY}"
    assert prompt.count(expected_question) == 1

    # ---- symbol blocks appear, in order ----
    assert "=== Retrieved Symbol 1 ===" in prompt
    assert "=== Retrieved Symbol 2 ===" in prompt
    assert prompt.index("=== Retrieved Symbol 1 ===") < prompt.index("=== Retrieved Symbol 2 ===")

    # ---- retrieval order preserved (hit content ordering) ----
    assert prompt.index(hit_content_1) < prompt.index(hit_content_2)

    # ---- hit content preserved verbatim ----
    assert hit_content_1 in prompt
    assert hit_content_2 in prompt

    # ---- block 1: all sections present, in order ----
    block_1 = _symbol_block(prompt, 1)
    assert hit_content_1 in block_1
    assert "Parent class:" in block_1
    assert "Base class:" in block_1
    assert "Sibling methods:" in block_1
    assert block_1.index("Parent class:") < block_1.index("Base class:") < block_1.index("Sibling methods:")

    # ---- block 2: all sections omitted ----
    block_2 = _symbol_block(prompt, 2)
    assert hit_content_2 in block_2
    assert "Parent class:" not in block_2
    assert "Base class:" not in block_2
    assert "Sibling methods:" not in block_2

    # ---- no retrieval-implementation details leak into the prompt ----
    lowered = prompt.lower()
    for forbidden in ("score", "qdrant", "embedding"):
        assert forbidden not in lowered, f"'{forbidden}' leaked into prompt"

    # ---- empty expanded list still produces a valid prompt ----
    empty_prompt = build_prompt(QUERY, [])
    assert "User question:" in empty_prompt
    assert QUERY in empty_prompt
    assert "=== Retrieved Symbol" not in empty_prompt


    # --------------------------------------------------------------
    prompt_without_history = build_prompt(
        query="Explain indexing.",
        expanded=[result_1],
    )

    prompt_empty_history = build_prompt(
        query="Explain indexing.",
        expanded=[result_1],
        history=[],
    )

    assert (
        prompt_without_history == prompt_empty_history
    ), "empty history should produce identical prompt"


    # --------------------------------------------------------------
    history = [
        ChatTurn(
            question="What is indexing?",
            answer="Indexing scans the repository.",
        ),
        ChatTurn(
            question="What is Graph RAG?",
            answer="Graph RAG enriches retrieval.",
        ),
    ]

    prompt_history  = build_prompt(
        query="How do updates work?",
        expanded=[result_1],
        history=history,
    )

    assert "=== Conversation History ===" in prompt_history
    assert prompt_history .index("=== Conversation History ===") < prompt_history .index("User question:")

    assert "What is indexing?" in prompt_history
    assert "Indexing scans the repository." in prompt_history
    assert "What is Graph RAG?" in prompt_history
    assert "Graph RAG enriches retrieval." in prompt_history


    # --------------------------------------------------------------
    history = [
        ChatTurn(question=f"Q{i}", answer=f"A{i}")
        for i in range(5)
    ]

    history = history[-4:]

    prompt_window  = build_prompt(
        query="Current question",
        expanded=[result_1],
        history=history,
    )

    assert "Q0" not in prompt_window
    assert "A0" not in prompt_window

    for i in range(1, 5):
        assert f"Q{i}" in prompt_window
        assert f"A{i}" in prompt_window


    print("All assertions passed.")


if __name__ == "__main__":
    main()