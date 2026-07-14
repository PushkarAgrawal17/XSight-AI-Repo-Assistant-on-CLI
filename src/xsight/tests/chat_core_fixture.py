"""Fixture fakes for testing xsight.chat.core.answer_question."""

import networkx as nx

from xsight.vectorstore.models import SearchResult


class FakeEmbeddingProvider:
    dimension = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStoreProvider:
    """Not used directly -- xsight.retrieval.core.search calls
    vectorstore.core.search(query_vector, repo_id, k, provider), so we
    fake at the level retrieval actually calls."""


class FakeLLMProvider:
    def __init__(self, response: str = "fake answer"):
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def make_graph_with_one_function() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    g.add_node("mod.py", kind="module", name="mod", relative_path="mod.py")
    g.add_node(
        "mod.py::f",
        kind="function",
        name="f",
        start_line=1,
        end_line=2,
        parent_id=None,
        is_method=False,
    )
    g.add_edge("mod.py", "mod.py::f", type="contains")
    return g