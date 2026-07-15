"""Data contract for in-session conversation history."""

from dataclasses import dataclass


@dataclass
class ChatTurn:
    question: str
    answer: str