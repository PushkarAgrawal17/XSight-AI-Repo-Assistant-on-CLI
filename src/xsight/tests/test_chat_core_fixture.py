"""Fixture test for xsight.chat.core.answer_question -- verifies the
no-results path and the successful path, without any real Ollama/Qdrant/
Gemini services."""

from unittest.mock import patch

from xsight.chat.core import NoResultsError, answer_question
from xsight.chat.models import ChatTurn
from xsight.tests.chat_core_fixture import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    make_graph_with_one_function,
)
from xsight.vectorstore.models import SearchResult


def main() -> None:
    graph = make_graph_with_one_function()
    embedding_provider = FakeEmbeddingProvider()
    llm_provider = FakeLLMProvider(response="the answer")

    fake_hit = SearchResult(
        chunk_id="mod.py::f",
        content="def f(): pass",
        relative_path="mod.py",
        kind="function",
        start_line=1,
        end_line=2,
        score=0.9,
    )

    # Successful path: patch retrieval.core.search (the module-level import
    # used inside chat.core) to avoid needing a real vectorstore provider.
    with patch("xsight.chat.core.search", return_value=[fake_hit]):
        answer = answer_question(
            query="what does f do?",
            repo_id=1,
            graph=graph,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,  # unused once search() is patched
            llm_provider=llm_provider,
        )
    assert answer == "the answer", f"expected 'the answer', got {answer}"
    assert llm_provider.last_prompt is not None, "expected a prompt to be built and sent"
    assert "what does f do?" in llm_provider.last_prompt, "prompt should include the query"

    # No-results path
    with patch("xsight.chat.core.search", return_value=[]):
        try:
            answer_question(
                query="nothing matches",
                repo_id=1,
                graph=graph,
                embedding_provider=embedding_provider,
                vectorstore_provider=None,
                llm_provider=llm_provider,
            )
            assert False, "expected NoResultsError to be raised"
        except NoResultsError:
            pass


    # --------------------------------------------------------------
    history = [
        ChatTurn(
            question="Previous question",
            answer="Previous answer",
        )
    ]

    with patch("xsight.chat.core.search", return_value=[fake_hit]):
        answer_question(
            query="Current question",
            repo_id=1,
            graph=graph,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
            llm_provider=llm_provider,
            history=history,
        )

    assert "Previous question" in llm_provider.last_prompt
    assert "Previous answer" in llm_provider.last_prompt
    assert "Current question" in llm_provider.last_prompt


    print("All chat.core fixture assertions passed.")


if __name__ == "__main__":
    main()