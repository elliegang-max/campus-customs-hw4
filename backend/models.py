"""Structured types for the Campus Customs agent.

Split into three groups:

- The product shapes the API and the agent both return (`InventoryItem`,
  `Product`). These match the enriched `products_json` already stored in the
  `chat_messages` table.
- The tool argument/return shapes the agent passes around internally.
- The chat request/response shapes the website exchanges with `main.py`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Product shapes --------------------------------------------------------


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


# --- Tool shapes -----------------------------------------------------------


class ProductCard(BaseModel):
    """A product trimmed to what a tool hands back to the model.

    The model does not need image paths or the full tag list to reason, so they
    are left off the tool result to keep the context small. `sizes_in_stock` is
    pre-computed here precisely so the model never has to infer availability from
    raw quantities — it sees only the sizes it can actually offer. The full
    `Product` (with images) is looked up again by id when building the reply the
    website renders.
    """

    product_id: str = Field(description="Stable id; pass to the lookup tools.")
    name: str = Field(description="Display name to show the shopper.")
    garment_type: str = Field(description="Category, e.g. 'pullover hoodie'.")
    description: str = Field(description="One-line visual description.")
    colors: list[str] = Field(description="The only colors that may be claimed.")
    price: float = Field(description="USD price; state exactly.")
    sizes_in_stock: list[str] = Field(
        description="Sizes with quantity > 0 — the sizes that can be offered."
    )
    total_stock: int = Field(description="Units across all sizes.")


class SizeAvailability(BaseModel):
    """One size's stock, with availability stated outright.

    `in_stock` is computed here rather than left for the model to derive from
    `quantity`, so "out of stock" is a fact in the tool result, not an inference
    the model might get wrong.
    """

    size: str = Field(description="Size label, e.g. 'M'.")
    quantity: int = Field(description="Exact units of this size; may be 0.")
    in_stock: bool = Field(description="True iff quantity > 0 — the availability fact.")


class ProductDetails(BaseModel):
    """The authoritative, database-backed facts about one product.

    This is what the agent calls to answer description / price / stock questions.
    Everything here comes straight from `catalogue` and `inventory`; the model is
    instructed to quote these values and never substitute its own.
    """

    product_id: str = Field(description="Stable id for this product.")
    name: str = Field(description="Display name.")
    garment_type: str = Field(description="Category.")
    description: str = Field(description="Quote this; do not paraphrase.")
    colors: list[str] = Field(description="The only colors that may be claimed.")
    price: float = Field(description="USD price; quote exactly, do not round.")
    sizes: list[SizeAvailability] = Field(
        description="Every size with its exact quantity and in_stock flag."
    )
    sizes_in_stock: list[str] = Field(
        description="Sizes that can be offered now; use these for alternatives."
    )
    sizes_out_of_stock: list[str] = Field(
        description="Sizes to state as out of stock if the shopper asks for one."
    )
    total_stock: int = Field(description="Units across all sizes.")


# --- Chat shapes -----------------------------------------------------------


class ChatRequest(BaseModel):
    """One message from the website's chat widget.

    `current_product_id` is the page context: when the shopper is on a product
    detail page, the widget sends that product's id so the agent can resolve
    "this" in questions like "do you have this in pink?". None when the shopper is
    anywhere else on the site.
    """

    message: str = Field(min_length=1, max_length=2000)
    current_product_id: str | None = None


class ChatResponse(BaseModel):
    """One reply back to the widget.

    `products` are enriched `Product` objects (with `image_url` and price), so
    the widget can render a card per product beside the text. This is the same
    contract as the `products_json` already stored on assistant rows in the
    `chat_messages` table, so persisted history and live replies share a shape.
    An empty list means the reply referred to no specific product.
    """

    reply: str
    products: list[Product] = []


class ChatMessage(BaseModel):
    """One stored turn, replayed to the widget when a shopper returns.

    Mirrors a `chat_messages` row. `products` is parsed from the row's
    `products_json`, so reloaded history renders the same cards it showed live.
    """

    role: str  # "user" or "assistant"
    content: str
    products: list[Product] = []
    created_at: str
