from xsight.embeddings.provider import EmbeddingProvider
from xsight.vectorstore import core as vectorstore
from xsight.vectorstore.models import SearchResult
from xsight.vectorstore.provider import VectorStoreProvider


def search(
    query: str,
    repo_id: int,
    k: int,
    embedding_provider: EmbeddingProvider,
    vectorstore_provider: VectorStoreProvider,
) -> list[SearchResult]:
    """
    Perform semantic retrieval for a natural-language query.

    Embeds the query and delegates ranking/filtering entirely to
    vectorstore.core.search(). This function performs semantic retrieval
    only -- it does not perform graph expansion, reranking, prompt
    construction, or LLM interaction. Graph expansion from retrieved
    chunks is intentionally deferred to xsight chat, which will call
    this function as its first step.
    """
    query_vector = embedding_provider.embed([query])[0]
    return vectorstore.search(query_vector, repo_id, k, vectorstore_provider)