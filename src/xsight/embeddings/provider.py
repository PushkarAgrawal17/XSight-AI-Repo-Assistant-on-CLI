from typing import Protocol

import requests

_DEFAULT_TIMEOUT_SECONDS = None


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text, in the same order as `texts`."""
        ...

class OllamaEmbeddingProvider:
    """Embedding provider backed by a local Ollama instance."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": texts},
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    @property
    def dimension(self) -> int:
        return 768