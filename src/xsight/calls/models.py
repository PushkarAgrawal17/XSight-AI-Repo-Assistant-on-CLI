from dataclasses import dataclass


@dataclass(frozen=True)
class CallEdge:
    caller_id: str
    callee_id: str