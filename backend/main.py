"""Campus Customs backend.

For now this only reads the catalogue and serves product images. It is written
so the agent endpoints can be added alongside these in a later problem rather
than replacing them.

Run from the project root:

    .venv/bin/uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import history
from agent import run_chat
from auth import current_user
from auth import router as auth_router
from db import PRODUCTS_DIR, get_conn
from models import ChatMessage, ChatRequest, ChatResponse

# Images are served under this prefix, matching the `image_url` values already
# stored in the chat_messages table.
MEDIA_PREFIX = "/media/products"

# The catalogue stores sizes in no particular order; the shop should always show
# them smallest to largest.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


# --- Models ----------------------------------------------------------------


class InventoryItem(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_file_path: str
    image_url: str
    price: float
    inventory: list[InventoryItem]
    total_stock: int


# --- Database --------------------------------------------------------------


def _parse_json_list(raw: str) -> list[str]:
    """colors and search_tags are JSON arrays stored as TEXT."""
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _size_key(size: str) -> tuple[int, str]:
    """Sort known sizes XS→XXL; anything unexpected goes last, alphabetically."""
    try:
        return (SIZE_ORDER.index(size), "")
    except ValueError:
        return (len(SIZE_ORDER), size)


def _to_product(row: sqlite3.Row, stock_rows: list[sqlite3.Row]) -> Product:
    inventory = sorted(
        (InventoryItem(size=r["size"], quantity=r["quantity"]) for r in stock_rows),
        key=lambda item: _size_key(item.size),
    )
    return Product(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=_parse_json_list(row["colors"]),
        search_tags=_parse_json_list(row["search_tags"]),
        image_file_path=row["image_file_path"],
        # products/foo.jpg -> /media/products/foo.jpg
        image_url=f"{MEDIA_PREFIX}/{Path(row['image_file_path']).name}",
        price=row["price"],
        inventory=inventory,
        total_stock=sum(item.quantity for item in inventory),
    )


def _load_products(
    conn: sqlite3.Connection, product_id: str | None = None
) -> list[Product]:
    """Load products with their stock in two queries, never one query per product."""
    if product_id is None:
        catalogue = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock = conn.execute("SELECT * FROM inventory").fetchall()
    else:
        catalogue = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchall()
        stock = conn.execute(
            "SELECT * FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    by_product: dict[str, list[sqlite3.Row]] = {}
    for row in stock:
        by_product.setdefault(row["product_id"], []).append(row)

    return [_to_product(row, by_product.get(row["product_id"], [])) for row in catalogue]


# --- App -------------------------------------------------------------------

app = FastAPI(title="Campus Customs API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(MEDIA_PREFIX, StaticFiles(directory=PRODUCTS_DIR), name="product-images")

app.include_router(auth_router)


@app.get("/api/health")
def health() -> dict[str, object]:
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM catalogue").fetchone()["n"]
    return {"status": "ok", "products": count}


@app.get("/api/products", response_model=list[Product])
def list_products(
    q: str | None = Query(default=None, description="Free-text filter"),
    limit: int | None = Query(default=None, ge=1, le=200),
) -> list[Product]:
    """Every product, each with its per-size stock.

    `q` is a plain substring match across name, description and tags. It is
    deliberately dumb — real search is the agent's job, and 102 products fit in
    memory comfortably.
    """
    with get_conn() as conn:
        products = _load_products(conn)

    if q:
        needle = q.strip().lower()
        products = [
            p
            for p in products
            if needle in p.name.lower()
            or needle in p.description.lower()
            or needle in p.garment_type.lower()
            or any(needle in tag.lower() for tag in p.search_tags)
            or any(needle in color.lower() for color in p.colors)
        ]

    return products[:limit] if limit else products


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    with get_conn() as conn:
        products = _load_products(conn, product_id=product_id)
    if not products:
        raise HTTPException(status_code=404, detail=f"No product '{product_id}'")
    return products[0]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    campus_customs_session: str | None = Cookie(default=None),
) -> ChatResponse:
    """One chat turn.

    A signed-in shopper's identity (name, email) is read from the session and
    given to the agent, their prior conversation is replayed as context, and both
    this turn's messages are saved. An anonymous shopper gets no identity and no
    persistence. Either way, the current product page (if any) is passed so "this"
    resolves.
    """
    user = current_user(campus_customs_session)

    agent_history = None
    if user is not None:
        agent_history = history.to_model_messages(
            history.load_history(user.id, limit=history.AGENT_HISTORY_LIMIT)
        )

    try:
        reply, products = await run_chat(
            payload.message,
            first_name=(user.first_name or user.name.split()[0]) if user else None,
            full_name=(user.name if user else None),
            email=(user.email if user else None),
            current_product_id=payload.current_product_id,
            message_history=agent_history,
        )
    except Exception:
        # The agent run failed — a tripped loop limit, a model/content-filter
        # error, a network blip. The failure is already in the audit trail; return
        # a calm reply instead of a 500 so the widget stays usable. Nothing is
        # persisted for a failed turn.
        return ChatResponse(
            reply=(
                "Sorry — I couldn't process that just now. Try rephrasing, or ask "
                "me about a product, size, color or price."
            ),
            products=[],
        )

    # Persist the turn only for a logged-in shopper (anonymous has no user_id).
    if user is not None:
        history.save_message(user.id, "user", payload.message)
        history.save_message(user.id, "assistant", reply, products)

    return ChatResponse(reply=reply, products=products)


@app.get("/api/chat/history", response_model=list[ChatMessage])
def chat_history(
    campus_customs_session: str | None = Cookie(default=None),
) -> list[ChatMessage]:
    """The signed-in shopper's saved conversation, for the widget to replay on
    return. Empty list when nobody is signed in — never a 401, since the widget
    calls this on load."""
    user = current_user(campus_customs_session)
    return history.load_history(user.id) if user is not None else []
