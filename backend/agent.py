"""The Campus Customs shop agent: PydanticAI wiring.

The agent is built once at import and reused. Its tools read the catalogue; it
has no tool that writes anything and no tool that can reach the users table, so
there is no path from a chat message to account data.

Model calls go through the Portkey gateway, matching the rest of the course:
`gpt-5.6-luna` by default, key and base URL read from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
import tools
from models import Product, ProductCard, ProductDetails, SizeAvailability

DEFAULT_MODEL = "gpt-5.6-luna"
PROMPT_PATH = Path(__file__).parent / "prompts" / "prompt.md"

# Loop safety: cap how many model requests one chat turn may make. Each tool
# round is one request, so this bounds the agent's tool loop and the cost/latency
# of a single turn. A normal turn is 1–3 requests (search, maybe a detail/stock
# lookup, then the reply); this leaves headroom without letting it spin.
MAX_REQUESTS_PER_TURN = 6


@dataclass
class ChatDeps:
    """Per-request context handed to the tools and the dynamic system prompt.

    Carries who is chatting and what they are looking at, so the agent does not
    need a tool that can read the users table to know the shopper. All of it comes
    from the signed-in session (resolved in `main.py`) or the page the widget is
    on — never from anything the model said.

    - identity: `first_name` / `full_name` / `email` are set only for a logged-in
      shopper; all None for an anonymous one.
    - page context: `current_product` is the product on the detail page the
      shopper is viewing, if any, so "do you have this in pink?" resolves "this".
    """

    first_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    current_product: ProductDetails | None = None


def _load_env_file(path: Path) -> None:
    """Set any KEY=VALUE from a dotenv-style file that isn't already in os.environ."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


def _load_keys_from_file_if_needed() -> None:
    """Populate PORTKEY_* when not already exported.

    Resolution order (first that provides them wins): the process environment,
    then a `.env` at the project root (what `.env.example` documents), then the
    course keys file at `~/.config/ai-keys/keys.env`. So a grader can either
    export the vars or drop a `.env` in place, and our own setup keeps working.
    """
    if os.environ.get("PORTKEY_API_KEY") and os.environ.get("PORTKEY_BASE_URL"):
        return
    _load_env_file(Path(__file__).resolve().parent.parent / ".env")
    if os.environ.get("PORTKEY_API_KEY") and os.environ.get("PORTKEY_BASE_URL"):
        return
    keys_file = Path.home() / ".config" / "ai-keys" / "keys.env"
    if not keys_file.exists():
        return
    for line in keys_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


def _make_client() -> AsyncOpenAI:
    """An OpenAI client pointed at the Portkey gateway."""
    _load_keys_from_file_if_needed()
    key = os.environ.get("PORTKEY_API_KEY")
    base_url = os.environ.get("PORTKEY_BASE_URL")
    if not key or not base_url:
        raise RuntimeError(
            "PORTKEY_API_KEY and PORTKEY_BASE_URL must be set for the agent."
        )
    return AsyncOpenAI(
        base_url=base_url,
        api_key="unused",  # Portkey authenticates with its own header
        default_headers={"x-portkey-api-key": key},
        timeout=120.0,
        max_retries=0,
    )


@lru_cache(maxsize=1)
def build_agent(model_name: str = DEFAULT_MODEL) -> Agent[ChatDeps, str]:
    model = OpenAIChatModel(
        model_name, provider=OpenAIProvider(openai_client=_make_client())
    )
    # The whole prompt is delivered as `instructions`, not `system_prompt`.
    # Instructions are re-evaluated on every run and are not stored in the
    # message history, so a returning shopper (whose turn carries prior
    # `message_history`) still gets the full base prompt plus fresh identity and
    # page context. A plain system_prompt would be skipped once history exists.
    agent: Agent[ChatDeps, str] = Agent(
        model,
        deps_type=ChatDeps,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    )

    @agent.instructions
    def shopper_context(ctx: RunContext[ChatDeps]) -> str:
        """Who is chatting, re-evaluated each turn."""
        if ctx.deps.full_name or ctx.deps.email:
            name = ctx.deps.full_name or ctx.deps.first_name or "the shopper"
            email = f" (email: {ctx.deps.email})" if ctx.deps.email else ""
            return (
                f"The signed-in shopper is {name}{email}. You may greet them by "
                f"first name. This identity comes from their login session, not "
                f"from anything they typed — trust it, but do not read it back in "
                f"full or discuss other accounts."
            )
        return "The shopper is browsing without an account; you do not know their name."

    @agent.instructions
    def page_context(ctx: RunContext[ChatDeps]) -> str:
        """What product page the shopper is on, re-evaluated each turn."""
        product = ctx.deps.current_product
        if product is None:
            return "The shopper is not on a specific product page right now."
        return (
            "The shopper is currently viewing this product page:\n"
            f"- name: {product.name}\n"
            f"- product_id: {product.product_id}\n"
            f"- price: ${product.price}\n"
            f"- colors: {', '.join(product.colors) or 'not listed'}\n"
            "If they say 'this', 'this one', 'it', or ask about color/size/price "
            "without naming a product, they mean this one. You still have its "
            "product_id, so call your tools with it to confirm details before "
            "answering."
        )

    @agent.tool
    def search_catalogue(
        ctx: RunContext[ChatDeps], query: str, limit: int = 8
    ) -> list[ProductCard]:
        """Find products in the Campus Customs catalogue.

        `query` is free text — a garment type, color, team, residential college,
        or any mix ("navy hoodie", "law school quarter zip"). Returns the best
        matches, each with its description, price and in-stock sizes. Use this to
        answer "what do you have" and to get a `product_id` for the lookups
        below. Describe only what it returns.
        """
        return tools.search_catalogue(query, limit=limit)

    @agent.tool
    def filter_products(
        ctx: RunContext[ChatDeps],
        garment_type: str | None = None,
        color: str | None = None,
        max_price: float | None = None,
        min_price: float | None = None,
        in_stock_size: str | None = None,
        limit: int = 12,
    ) -> list[ProductCard]:
        """Filter the catalogue by exact constraints, sorted cheapest first.

        Prefer this over `search_catalogue` when the shopper gives hard criteria —
        a price limit, a specific color, a garment type, or a size that must be in
        stock ("hoodies under $60", "navy crewnecks available in L"). Combine as
        many as apply. `garment_type` and `color` match as substrings ("hoodie"
        matches "pullover hoodie"). Returns the same cards as search.
        """
        return tools.filter_products(
            garment_type=garment_type,
            color=color,
            max_price=max_price,
            min_price=min_price,
            in_stock_size=in_stock_size,
            limit=limit,
        )

    @agent.tool
    def get_product_details(
        ctx: RunContext[ChatDeps], product_id: str
    ) -> ProductDetails | None:
        """Look up the real description, price and per-size stock for ONE product.

        Reads the database directly. Use this whenever a shopper asks about a
        specific product's description, price or availability. Quote the `price`
        and `description` exactly as returned — do not paraphrase numbers. Returns
        null if the `product_id` is unknown (find the id with `search_catalogue`
        first).
        """
        return tools.get_product_details(product_id)

    @agent.tool
    def check_stock(
        ctx: RunContext[ChatDeps], product_id: str, size: str | None = None
    ) -> list[SizeAvailability]:
        """Exact stock for one product, from the database, by size.

        Pass `size` (XS, S, M, L, XL, XXL) when the shopper asks about a specific
        size; omit it for all sizes. Each entry has the real `quantity` and an
        `in_stock` flag. If a size's `in_stock` is false, tell the shopper that
        size is out of stock and offer the sizes that are available. Returns an
        empty list if the product id is unknown or has no such size.
        """
        return tools.check_stock(product_id, size=size) or []

    return agent


# --- Reply-building --------------------------------------------------------

# The website renders a card for every product the turn is "about". We derive
# that set from what the agent actually did — its tool calls and their results —
# not by parsing the prose, so the contract is deterministic and cannot drift
# from the reply's wording.


async def run_chat(
    message: str,
    *,
    first_name: str | None = None,
    full_name: str | None = None,
    email: str | None = None,
    current_product_id: str | None = None,
    message_history: list | None = None,
) -> tuple[str, list[Product]]:
    """Run one turn.

    Identity fields set the agent's knowledge of who is chatting; they come from
    the session, not the message. `current_product_id` is the page the shopper is
    on. `message_history` is the prior conversation replayed for context.

    Returns the reply text and the matching products to display.
    """
    agent = build_agent()
    deps = ChatDeps(
        first_name=first_name,
        full_name=full_name,
        email=email,
        current_product=tools.get_product_details(current_product_id)
        if current_product_id
        else None,
    )

    started = audit.now_iso()
    try:
        result = await agent.run(
            message,
            deps=deps,
            message_history=message_history or [],
            usage_limits=UsageLimits(request_limit=MAX_REQUESTS_PER_TURN),
        )
    except Exception as exc:
        # Record the failed turn (e.g. the loop limit tripped) before re-raising.
        stop_reason = type(exc).__name__
        audit.append_events(
            [
                {
                    "ts": started,
                    "event": "run_end",
                    "user_msg": audit.short(message, 120),
                    "signed_in": bool(email),
                    "stop_reason": stop_reason,
                    "error": audit.short(str(exc), 200),
                }
            ]
        )
        raise

    reply = result.output
    product_ids = _matched_product_ids(result)
    products = [p for pid in product_ids if (p := tools.get_product(pid))]

    _write_audit(result, message, bool(email), started)
    return reply, products


def _write_audit(
    result: object, message: str, signed_in: bool, started: str
) -> None:
    """Append one tool_call record per tool the turn ran, plus a run_end record."""
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
    )

    events: list[dict] = []
    # Pair each tool call with its return by tool_call_id for a clean args→result.
    returns: dict[str, object] = {}
    for msg in getattr(result, "all_messages", lambda: [])():
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    returns[part.tool_call_id] = part.content

    for msg in getattr(result, "all_messages", lambda: [])():
        if not isinstance(msg, ModelResponse):
            continue
        for part in msg.parts:
            if not isinstance(part, ToolCallPart):
                continue
            events.append(
                {
                    "ts": audit.now_iso(),
                    "event": "tool_call",
                    "tool": part.tool_name,
                    "args": audit.short(getattr(part, "args", None)),
                    "result": _summarise_result(returns.get(part.tool_call_id)),
                }
            )

    events.append(
        {
            "ts": audit.now_iso(),
            "event": "run_end",
            "user_msg": audit.short(message, 120),
            "signed_in": signed_in,
            "tool_calls": len(events),
            "stop_reason": "completed",
            "reply_chars": len(getattr(result, "output", "") or ""),
        }
    )
    audit.append_events(events)


def _summarise_result(content: object) -> str:
    """A short, safe summary of a tool's return for the audit log."""
    if content is None:
        return "none"
    if isinstance(content, list):
        return audit.short(f"{len(content)} item(s)")
    return audit.short(content)


def _matched_product_ids(result: object) -> list[str]:
    """The products to show as cards, chosen from the agent's tool activity.

    Two sources, in priority order:

    - **Specific lookups.** Product ids the agent passed to `get_product_details`
      or `check_stock`. Looking a product up by id is a deliberate act of
      interest in *that* product, so when any exist these are the matches.
    - **Search results.** The product ids `search_catalogue` returned. These are
      the answer to a browse/category question ("what hoodies do you have?").

    If the agent made specific lookups, show those; otherwise show the search
    results. Order is preserved and ids are de-duplicated. This never parses the
    reply text, so the cards always reflect what the agent did, not how it
    happened to phrase the answer.
    """
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
    )

    specific: list[str] = []
    searched: list[str] = []

    def add(bucket: list[str], pid: str | None) -> None:
        if pid and pid not in bucket:
            bucket.append(pid)

    for msg in getattr(result, "all_messages", lambda: [])():
        # Tool calls the model made: get_product_details / check_stock name a
        # specific product by id in their arguments.
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if not isinstance(part, ToolCallPart):
                    continue
                if part.tool_name in ("get_product_details", "check_stock"):
                    add(specific, _arg_product_id(part))
        # Tool results coming back: search_catalogue returns a list of cards.
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and isinstance(part.content, list):
                    for item in part.content:
                        add(searched, _extract_id(item))

    return specific or searched


def _arg_product_id(part: object) -> str | None:
    """Pull `product_id` out of a tool call's arguments (dict or JSON string)."""
    import json

    args = getattr(part, "args", None)
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    if isinstance(args, dict):
        value = args.get("product_id")
        return value if isinstance(value, str) else None
    return None


def _extract_id(item: object) -> str | None:
    if isinstance(item, ProductCard):
        return item.product_id
    if isinstance(item, dict):
        return item.get("product_id")
    return getattr(item, "product_id", None)
