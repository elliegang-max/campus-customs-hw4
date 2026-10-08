"""Chat history persistence, backed by the `chat_messages` table.

A logged-in shopper's conversation is saved turn by turn and reloaded when they
return. Three jobs live here:

- `load_history` — stored turns as `ChatMessage`s, for the widget to replay.
- `save_message` — append one turn.
- `to_model_messages` — convert stored turns into the message-history format the
  agent replays as context, so a returning shopper's agent remembers the thread.

Only logged-in shoppers are persisted; an anonymous session has no `user_id` to
key history on, so nothing is written for it.
"""

from __future__ import annotations

import json

from db import get_conn, get_write_conn
from models import ChatMessage, Product

# How many past turns to replay to the agent as context. The full history is
# always returned to the widget; this cap only bounds what the model re-reads.
AGENT_HISTORY_LIMIT = 20


def load_history(user_id: int, limit: int | None = None) -> list[ChatMessage]:
    """Stored turns for one user, oldest first."""
    sql = (
        "SELECT role, content, products_json, created_at "
        "FROM chat_messages WHERE user_id = ? ORDER BY id"
    )
    with get_conn() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()

    messages = [
        ChatMessage(
            role=row["role"],
            content=row["content"],
            products=_parse_products(row["products_json"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return messages[-limit:] if limit else messages


def save_message(
    user_id: int,
    role: str,
    content: str,
    products: list[Product] | None = None,
) -> None:
    """Append one turn. `products` is stored as JSON on assistant turns."""
    products_json = (
        json.dumps([p.model_dump() for p in products]) if products else None
    )
    with get_write_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, content, products_json),
        )


def to_model_messages(history: list[ChatMessage]) -> list:
    """Convert stored turns into pydantic-ai message history.

    Only the text of each turn is replayed — enough for the agent to follow the
    conversation. The stored product cards are for the widget, not the model.
    """
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        TextPart,
        UserPromptPart,
    )

    messages: list = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        elif turn.role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def _parse_products(products_json: str | None) -> list[Product]:
    if not products_json:
        return []
    try:
        raw = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    products: list[Product] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            products.append(Product.model_validate(item))
        except Exception:
            # A stored row might predate a field; skip rather than fail the load.
            continue
    return products
