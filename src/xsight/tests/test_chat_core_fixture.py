"""Fixture test for xsight.chat.core.answer_question -- verifies the
no-results path and the successful path, without any real Ollama/Qdrant/
Gemini services."""

from pathlib import Path
from unittest.mock import patch

from xsight.chat.core import NoResultsError, answer_question
from xsight.chat.models import ChatTurn
from xsight.tests.chat_core_fixture import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    make_graph_with_one_function,
)
from xsight.vectorstore.models import SearchResult

FAKE_REPO_PATH = Path(__file__).parent  # unused once search_hybrid is patched


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

    # Successful path: patch chat.core's search_hybrid to avoid needing a
    # real vectorstore provider or real graph/disk access for the
    # symbolic-match half of hybrid retrieval.
    with patch("xsight.chat.core.search_hybrid", return_value=[fake_hit]):
        answer = answer_question(
            query="what does f do?",
            repo_id=1,
            graph=graph,
            repo_path=FAKE_REPO_PATH,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,  # unused once search_hybrid is patched
            llm_provider=llm_provider,
        )
    assert answer == "the answer", f"expected 'the answer', got {answer}"
    assert llm_provider.last_prompt is not None, "expected a prompt to be built and sent"
    assert "what does f do?" in llm_provider.last_prompt, "prompt should include the query"

    # No-results path
    with patch("xsight.chat.core.search_hybrid", return_value=[]):
        try:
            answer_question(
                query="nothing matches",
                repo_id=1,
                graph=graph,
                repo_path=FAKE_REPO_PATH,
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

    with patch("xsight.chat.core.search_hybrid", return_value=[fake_hit]):
        answer_question(
            query="Current question",
            repo_id=1,
            graph=graph,
            repo_path=FAKE_REPO_PATH,
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