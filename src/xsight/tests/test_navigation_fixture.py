"""
Deterministic tests for Code Navigation v1 helpers in chat/core.py.

Uses the real parser/graph pipeline against the existing chunker_fixture.py
file (already used by test_chunker_fixture.py / test_chunk_one_fixture.py)
so class/function facts are checked against real parsed attributes rather
than hardcoded line numbers.
"""

from pathlib import Path
from unittest.mock import patch

from xsight.chat.core import (
    _build_navigation_prompt,
    _class_facts,
    _function_facts,
    _owning_module,
    _resolve_symbol,
    _route,
    _symbol_facts,
    _try_navigation,
    answer_question,
)
from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.tests.chat_core_fixture import FakeEmbeddingProvider, FakeLLMProvider
from xsight.vectorstore.models import SearchResult

FIXTURE_DIR = Path(__file__).parent
FIXTURE_FILE = "chunker_fixture.py"


def _build_graph():
    module = parse(FIXTURE_DIR / FIXTURE_FILE, FIXTURE_FILE)
    return build([module]), module


def main() -> None:
    graph, module = _build_graph()
    class_node = next(c for c in module.classes if c.name == "Greeter")
    function_node = next(f for f in module.functions if not f.is_method)
    method_node = next(f for f in module.functions if f.is_method)

    # ---- _route() ----
    assert _route("Where is sync defined?") == ("definition", "sync")
    assert _route("where is sync defined") == ("definition", "sync")
    assert _route("Where is Greeter.greet defined?") == ("definition", "Greeter.greet")
    assert _route("Show implementation of Greeter.greet") == ("implementation", "Greeter.greet")
    assert _route("Show me the implementation of greet") == ("implementation", "greet")
    assert _route("Where does incremental indexing happen?") is None
    assert _route("who calls sync") is None  # out of scope this milestone

    # ---- _resolve_symbol(): bare name matches both function and method ----
    matches = _resolve_symbol(graph, "greet")
    assert set(matches) == {function_node.id, method_node.id}

    # ---- _resolve_symbol(): qualified name narrows correctly ----
    assert _resolve_symbol(graph, "Greeter.greet") == [method_node.id]

    # ---- _resolve_symbol(): class name ----
    assert _resolve_symbol(graph, "Greeter") == [class_node.id]

    # ---- _resolve_symbol(): no match ----
    assert _resolve_symbol(graph, "does_not_exist") == []

    # ---- _owning_module() ----
    assert _owning_module(graph, class_node.id) == FIXTURE_FILE

    # ---- _class_facts(): location only ----
    facts = _class_facts(graph, FIXTURE_DIR, class_node.id, include_source=False)
    assert "Class:" in facts and "Greeter" in facts
    assert f"{FIXTURE_FILE} lines {class_node.start_line}-{class_node.end_line}" in facts
    assert "Source:" not in facts

    # ---- _class_facts(): with source ----
    facts_src = _class_facts(graph, FIXTURE_DIR, class_node.id, include_source=True)
    assert "Source:" in facts_src
    assert "def greet" in facts_src  # class body includes the method

    # ---- _function_facts(): matches chunk_one() output ----
    facts_fn = _function_facts(graph, FIXTURE_DIR, function_node.id, include_source=True)
    assert "Function:" in facts_fn
    assert f"{FIXTURE_FILE} lines {function_node.start_line}-{function_node.end_line}" in facts_fn
    assert 'return f"Hello, {name}!"' in facts_fn

    facts_method = _function_facts(graph, FIXTURE_DIR, method_node.id, include_source=False)
    assert "Method:" in facts_method
    assert "Source:" not in facts_method

    # ---- _symbol_facts(): multiple matches concatenated, never narrowed ----
    combined = _symbol_facts(graph, FIXTURE_DIR, matches, include_source=False)
    assert "Function:" in combined and "Method:" in combined
    assert "---" in combined

    # ---- _build_navigation_prompt(): fixed, minimal shape ----
    prompt = _build_navigation_prompt("Where is greet defined?", "Function:\ngreet")
    assert "Where is greet defined?" in prompt
    assert "Repository facts:" in prompt
    assert "Function:\ngreet" in prompt
    assert "Do not invent any additional information." in prompt
    lowered = prompt.lower()
    for forbidden in ("score", "qdrant", "embedding"):
        assert forbidden not in lowered

    llm_provider = FakeLLMProvider(response="nav answer")

    # ---- _try_navigation(): unresolved symbol falls through (None) ----
    assert _try_navigation("Where is nonexistent_xyz defined?", graph, FIXTURE_DIR, llm_provider) is None

    # ---- _try_navigation(): non-navigation query falls through (None) ----
    assert _try_navigation("How does scanning work?", graph, FIXTURE_DIR, llm_provider) is None

    # ---- _try_navigation(): successful lookup returns LLM output ----
    result = _try_navigation("Where is Greeter.greet defined?", graph, FIXTURE_DIR, llm_provider)
    assert result == "nav answer"
    assert "greet" in llm_provider.last_prompt

    # ---- end-to-end: navigation short-circuits before hybrid retrieval ----
    embedding_provider = FakeEmbeddingProvider()
    with patch("xsight.chat.core.search_hybrid") as mock_search_hybrid:
        answer = answer_question(
            query="Where is Greeter.greet defined?",
            repo_id=1,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
            llm_provider=llm_provider,
        )
    assert answer == "nav answer"
    mock_search_hybrid.assert_not_called()

    # ---- end-to-end: non-navigation query still reaches hybrid retrieval ----
    fake_hit = SearchResult(
        chunk_id=function_node.id, content="...", relative_path=FIXTURE_FILE,
        kind="function", start_line=1, end_line=2, score=0.9,
    )
    with patch("xsight.chat.core.search_hybrid", return_value=[fake_hit]) as mock_search_hybrid:
        answer_question(
            query="How does greeting work in this repo?",
            repo_id=1,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
            llm_provider=llm_provider,
        )
    mock_search_hybrid.assert_called_once()

    print("All navigation assertions passed.")


if __name__ == "__main__":
    main()