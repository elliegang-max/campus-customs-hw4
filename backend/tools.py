"""Tools the agent can call, plus the product-loading helpers they share.

The product loaders are the same logic the REST endpoints use. Keeping one
implementation means the cards the agent talks about and the cards the Products
page shows can never describe the catalogue differently.

Every function here reads the database through the read-only connection. Nothing
the agent can reach opens a writable connection, and nothing selects the
`password_hash` column — the agent has no path to it by construction.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from db import get_conn
from models import (
    InventoryItem,
    Product,
    ProductCard,
    ProductDetails,
    SizeAvailability,
)

MEDIA_PREFIX = "/media/products"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


# --- Shared parsing --------------------------------------------------------


def _parse_json_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _size_key(size: str) -> tuple[int, str]:
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
        image_url=f"{MEDIA_PREFIX}/{Path(row['image_file_path']).name}",
        price=row["price"],
        inventory=inventory,
        total_stock=sum(item.quantity for item in inventory),
    )


# --- Product loading (shared with the REST layer) --------------------------

# The catalogue and inventory are read on every search, detail lookup and stock
# check — several times per chat turn. They do not change while the app runs
# (only users and chat_messages are written), so the full product list is built
# once and cached. This turns "a few DB round-trips and 102 JSON-array parses per
# turn" into "zero DB work after the first call", which is the cheap-and-fast win.
# A short TTL bounds staleness in case the data is edited behind the app.
_CACHE_TTL_SECONDS = 300.0
_cache: dict[str, object] = {"at": 0.0, "products": None}


def _load_all_from_db() -> list[Product]:
    """The two-query load: catalogue and inventory, grouped in Python."""
    with get_conn() as conn:
        catalogue = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock = conn.execute("SELECT * FROM inventory").fetchall()

    by_product: dict[str, list[sqlite3.Row]] = {}
    for row in stock:
        by_product.setdefault(row["product_id"], []).append(row)

    return [
        _to_product(row, by_product.get(row["product_id"], [])) for row in catalogue
    ]


def _all_products() -> list[Product]:
    """Every product, from cache when fresh, rebuilt from the DB when stale."""
    import time

    now = time.monotonic()
    cached = _cache["products"]
    if cached is None or now - float(_cache["at"]) > _CACHE_TTL_SECONDS:
        cached = _load_all_from_db()
        _cache["products"] = cached
        _cache["at"] = now
    return cached  # type: ignore[return-value]


def clear_cache() -> None:
    """Drop the cached catalogue (used by tests and after any data edit)."""
    _cache["products"] = None
    _cache["at"] = 0.0


def load_products(product_id: str | None = None) -> list[Product]:
    """All products, or a one-element list for a given id. Served from cache."""
    products = _all_products()
    if product_id is None:
        return products
    return [p for p in products if p.product_id == product_id]


def get_product(product_id: str) -> Product | None:
    return next((p for p in _all_products() if p.product_id == product_id), None)


# --- Retrieval -------------------------------------------------------------


def _card(product: Product) -> ProductCard:
    return ProductCard(
        product_id=product.product_id,
        name=product.name,
        garment_type=product.garment_type,
        description=product.description,
        colors=product.colors,
        price=product.price,
        sizes_in_stock=[i.size for i in product.inventory if i.quantity > 0],
        total_stock=product.total_stock,
    )


def _score(product: Product, terms: list[str]) -> int:
    """Count how many query terms appear anywhere in the product's text.

    Deliberately simple weighted overlap: a hit in the name or tags counts for
    more than one in the long description. Good enough to shortlist 102 products;
    the model does the final judging from the cards it gets back.
    """
    name = product.name.lower()
    gtype = product.garment_type.lower()
    desc = product.description.lower()
    tags = " ".join(product.search_tags).lower()
    colors = " ".join(product.colors).lower()

    score = 0
    for term in terms:
        if term in name:
            score += 5
        if term in gtype:
            score += 4
        if term in tags:
            score += 3
        if term in colors:
            score += 3
        if term in desc:
            score += 1
    return score


def search_catalogue(query: str, limit: int = 8) -> list[ProductCard]:
    """Return the products best matching a free-text query, best first.

    An empty or whitespace query returns the first `limit` products rather than
    nothing, so "what do you have?" still gets an answer.
    """
    products = load_products()
    terms = [t for t in query.lower().split() if len(t) > 1]

    if not terms:
        return [_card(p) for p in products[:limit]]

    scored = ((p, _score(p, terms)) for p in products)
    ranked = sorted(
        (pair for pair in scored if pair[1] > 0),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [_card(p) for p, _ in ranked[:limit]]


def filter_products(
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_size: str | None = None,
    limit: int = 12,
) -> list[ProductCard]:
    """Exact structured filter over the catalogue, for constrained queries.

    Where `search_catalogue` ranks by fuzzy text overlap, this applies precise
    predicates and is the right tool for "hoodies under $60 available in L":
    price and size are numeric/stock facts that text scoring handles badly.

    - `garment_type` / `color`: case-insensitive substring, so "hoodie" matches
      "pullover hoodie" and "navy" matches "navy blue".
    - `max_price` / `min_price`: inclusive bounds in dollars.
    - `in_stock_size`: keep only products with quantity > 0 in that exact size.

    Results are sorted by price ascending — the useful order for a budget query.
    """
    results = _all_products()

    if garment_type:
        needle = garment_type.strip().lower()
        results = [p for p in results if needle in p.garment_type.lower()]
    if color:
        needle = color.strip().lower()
        results = [p for p in results if any(needle in c.lower() for c in p.colors)]
    if max_price is not None:
        results = [p for p in results if p.price <= max_price]
    if min_price is not None:
        results = [p for p in results if p.price >= min_price]
    if in_stock_size:
        want = in_stock_size.strip().upper()
        results = [
            p
            for p in results
            if any(i.size.upper() == want and i.quantity > 0 for i in p.inventory)
        ]

    results = sorted(results, key=lambda p: p.price)
    return [_card(p) for p in results[:limit]]


def get_product_details(product_id: str) -> ProductDetails | None:
    """Authoritative description, price and per-size stock for one product.

    Reads `catalogue` and `inventory` directly. Returns None if the id is
    unknown, so the caller can tell "no such product" from a real answer rather
    than guessing.
    """
    product = get_product(product_id)
    if product is None:
        return None

    sizes = [
        SizeAvailability(size=i.size, quantity=i.quantity, in_stock=i.quantity > 0)
        for i in product.inventory
    ]
    return ProductDetails(
        product_id=product.product_id,
        name=product.name,
        garment_type=product.garment_type,
        description=product.description,
        colors=product.colors,
        price=product.price,
        sizes=sizes,
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_out_of_stock=[s.size for s in sizes if not s.in_stock],
        total_stock=product.total_stock,
    )


def check_stock(
    product_id: str, size: str | None = None
) -> list[SizeAvailability] | None:
    """Per-size availability for one product, each marked in_stock or not.

    With `size` given, returns just that size (empty list if the product has no
    such size). Returns None only when the product id itself is unknown, so the
    caller can distinguish "no such product" from "that size is out of stock".
    """
    details = get_product_details(product_id)
    if details is None:
        return None
    if size is None:
        return details.sizes

    wanted = size.strip().upper()
    return [s for s in details.sizes if s.size.upper() == wanted]
