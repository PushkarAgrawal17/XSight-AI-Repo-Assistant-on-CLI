from typing import Protocol

from google import genai


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a response for the given prompt."""
        ...


class GeminiLLMProvider:
    def __init__(self, model: str, api_key: str):
        self._model = model
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text