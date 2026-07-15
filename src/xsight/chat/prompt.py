from xsight.expansion.models import ExpandedResult, RelatedSymbol
from xsight.chat.models import ChatTurn
from xsight.expansion.models import ExpandedResult, RelatedSymbol

_INSTRUCTIONS = (
    "You are XSight, an AI repository assistant.\n\n"
    "Answer the user's question using only the repository context below.\n"
    "If the context is insufficient, say so instead of guessing.\n"
    "When you reference a retrieved symbol, cite it using the exact "
    "\"Source: path:start-end\" tag shown above that symbol's block."
)


def format_hit(result: ExpandedResult) -> str:
    return result.hit.content


def format_parent(parent: RelatedSymbol | None) -> str:
    if parent is None:
        return ""
    return f"Parent class:\n{parent.name} (lines {parent.start_line}-{parent.end_line})"


def format_base_class(base_class: RelatedSymbol | None) -> str:
    if base_class is None:
        return ""
    return f"Base class:\n{base_class.name} (lines {base_class.start_line}-{base_class.end_line})"


def format_siblings(siblings: list[RelatedSymbol]) -> str:
    if not siblings:
        return ""
    lines = [f"- {s.name} (lines {s.start_line}-{s.end_line})" for s in siblings]
    return "Sibling methods:\n" + "\n".join(lines)

def format_calls(calls: list[RelatedSymbol]) -> str:
    if not calls:
        return ""
    lines = [f"- {c.name} (lines {c.start_line}-{c.end_line})" for c in calls]
    return "Calls:\n" + "\n".join(lines)


def format_called_by(called_by: list[RelatedSymbol]) -> str:
    if not called_by:
        return ""
    lines = [f"- {c.name} (lines {c.start_line}-{c.end_line})" for c in called_by]
    return "Called by:\n" + "\n".join(lines)


def format_citation(result: ExpandedResult) -> str:
    hit = result.hit
    return f"Source: {hit.relative_path}:{hit.start_line}-{hit.end_line}"


def _format_symbol_block(index: int, result: ExpandedResult) -> str:
    sections = [
        section
        for section in (
            format_citation(result),
            format_hit(result),
            format_parent(result.parent),
            format_base_class(result.base_class),
            format_siblings(result.siblings),
            format_calls(result.calls),
            format_called_by(result.called_by),
        )
        if section
    ]
    body = "\n\n".join(sections)
    return f"=== Retrieved Symbol {index} ===\n\n{body}"

def format_history(history: list[ChatTurn]) -> str:
    if not history:
        return ""
    lines = [f"User:\n{turn.question}\n\nAssistant:\n{turn.answer}" for turn in history]
    return "=== Conversation History ===\n\n" + "\n\n".join(lines)

def build_prompt(
    query: str,
    expanded: list[ExpandedResult],
    history: list[ChatTurn] | None = None,
) -> str:
    """
    Build the complete LLM prompt from a user query and expanded retrieval
    results. Purely mechanical formatting -- no policy decisions (e.g.
    whether an empty `expanded` list should skip the LLM call is the
    caller's responsibility, not this function's).

    Layout: fixed instructions, then the user question, then one block per
    hit in retrieval order. Never mentions retrieval scores, vector search,
    Qdrant, or embeddings -- the LLM sees repository structure only.
    """
    blocks = [_INSTRUCTIONS]
    history_block = format_history(history or [])
    if history_block:
        blocks.append(history_block)
    blocks.append(f"User question:\n{query}")
    blocks.extend(
        _format_symbol_block(i, result) for i, result in enumerate(expanded, start=1)
    )
    return "\n\n".join(blocks)