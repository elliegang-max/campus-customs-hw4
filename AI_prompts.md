# AI Prompt Log — hw4

A log of the prompts I typed into Claude while working on this assignment, in my
own words, organised by problem.

**Convention:** one section per problem, 13 in all. Each section records the
problem number and title, at least one prompt I typed, and — where the first
prompt did not get me what I needed — the follow-up prompt, with a one-line note
on what was lacking. A short note on what Claude did follows each prompt.
Sections are filled in as the assignment progresses; nothing is rewritten after
the fact.

**Standing instruction given early on, applying to every problem:**

> just know that we'll keep growing this harness file in later problems (models,
> tools, safety, specs).

Written into the top of `output/harness.md` as the convention: one numbered
section per problem, appended in order, earlier sections left as written.

---

## Problem 1 — Project and data setup

**Prompt** — 2026-10-07

> now work in hw4 folder

**What Claude did.** Moved the working directory to `AI Foundation/hw4`. The
folder was empty and no hw4 brief existed anywhere under `AI Foundation/`, so it
asked for the assignment rather than guessing at a scaffold.

**Follow-up prompt** _(the first prompt only said where to work, not what to do —
the data still had to be unpacked)_ _(with `~/Desktop/data-2.zip` attached)_

> unzip this file so that i have: `data/campus_customs.db` — SQLite database with
> tables `catalogue`, `inventory`, and `users` (one test user is already there)
> `data/products/` — product images; paths match the `catalogue` table

**What Claude did.** The archive's root was `data-2/`, not `data/`, and carried
macOS `__MACOSX/` resource forks. Extracted with those excluded, renamed to
`data/`, deleted the leftover `._*` files, and verified:

- `data/campus_customs.db` — `catalogue` (102 rows), `inventory` (612),
  `users` (3), plus a table the brief did not mention, `chat_messages`.
- `data/products/` — 102 JPEGs, matching `catalogue.image_file_path` values of
  the form `products/<slug>.jpg` (relative to `data/`).

**Also in this section — setting up the log itself:**

> Create AI_prompts.md at the start of the assignment and keep it updated as you
> work.

Created the file and backfilled the prompts above.

> This is the log file of what i typed into you, got it? We have 13 problems in
> this assignment, so put one section for each problem. Each section must
> include: the problem number and title; at least one prompt you typed, in your
> own words as much as possible; one follow-up prompt if you needed it (and one
> sentence on what was lacking after the first).

Restructured the flat chronological log into the 13 problem sections used here.

---

## Problem 2 — Understand the database

**Prompt** — 2026-10-07

> Look at the database data/campus_customs.db and understand the fields of each
> table. At a minimum you should understand catalogue, inventory, and users.

**What Claude did.** Queried the data, not just `.schema`: value distributions,
ranges, JSON shapes, and referential integrity. Found the undocumented
`chat_messages` table, whose stored assistant turns reveal the reply format the
shop is expected to produce (catalogue fields + `image_url` + joined `inventory`
+ `total_stock`). Flagged three traps — `garment_type` is free text with 22
variants so equality filters miss most matches, the colour vocabulary is
inconsistent (`navy` vs `navy blue`), and stock is per-size so no product is ever
simply "out of stock". Verified all 102 image paths exist on disk with no extras.

One command was stopped by a safety filter because it printed from the
`password_hash` column; that column is not needed to understand the schema and
was not queried again.

**Follow-up prompt** _(the first pass was explained in chat only — nothing was
written down for the assignment)_

> Start the file output/harness.md. Write down each table and its fields, and one
> short line on why each field matters for the shop

**What Claude did.** Created `output/harness.md` section 1: a table per database
table giving every field, its type, and a one-line justification in terms of the
shop, followed by the data-quality traps (1.5) and the integrity checks that
passed (1.6).

---

## Problem 3 — React front end scaffold

**Prompt** — 2026-10-07

> Scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav
> bar at the top that links to the main pages: Home, Products, About Us, Log in,
> Create account. Note: use Customs-style wording from yalebulldogblue.com for
> Home and About Us, but write these pages in your own voice (do not copy the
> original site text).

**What Claude did.** Scaffolded `frontend/` with Vite's `react-ts` template
(React 19, Vite 8, TypeScript 6) and added `react-router-dom` for routing. Built
a sticky navy nav bar with the five links, using `NavLink` so the current page
underlines itself, and five page components behind routes `/`, `/products`,
`/about`, `/login`, `/signup`, plus a catch-all 404.

For the copy, read `yalebulldogblue.com` only for its **structure and
terminology** — how it divides the shop into residential colleges, varsity
sports, graduate and professional schools, and relatives — and confirmed those
same four groupings exist in our own `catalogue`. The Home and About Us prose is
written from scratch against our data; no sentence is taken from the site. Added
a line on About Us noting Campus Customs is a fictional class project, not
affiliated with Yale or any real retailer.

Verified `npm run build` passes (`tsc -b` clean) and the dev server serves on
`:5173`. Products, Log in and Create account are deliberately inert scaffolds —
the forms hold local state and do not submit, since there is no backend yet.

---

**Follow-up prompt** _(the scaffold had a nav bar and pages but no real
content — Products was an empty placeholder and there was no chat surface)_

> On the Products page, show product images from the catalogue (use the image
> paths in the database) with basic product info (name, price, short
> description). Make each product open a single-item page (large image on one
> side, full product text on the other: description, price, sizes/stock when you
> have them). Clicking a card on Products should take the shopper there. Add a
> chat interface in the bottom right of the site (a floating chat panel is fine).
> It does not need to talk to an agent yet. A stub that will call your backend
> later is enough for this problem. You will need a small API soon to read the
> database. It is fine to start a simple FastAPI app in backend/main.py just to
> serve products and images, then grow it into the agent backend in Problem 5.

**What Claude did.** Built all three parts.

*Backend* — `backend/main.py`, FastAPI with `/api/health`, `/api/products`,
`/api/products/{id}`, and `data/products/` mounted at `/media/products`. The
response shape was copied from the `products_json` payloads already sitting in
`chat_messages` (catalogue row + `image_url` + joined `inventory` +
`total_stock`), so the chat endpoint in Problem 5 can reuse the same model. The
database is opened read-only; listing costs two queries rather than N+1.

*Products page* — responsive card grid, whole card links to the detail page,
photos `object-fit: contain` so chest graphics are not cropped away. Loading and
error states are real; there are no mock products, so a broken API looks broken.

*Detail page* — `/products/:productId`, sticky large image on one side, full text
on the other. All six sizes are always shown, zero-stock ones disabled and struck
through, and stock is reported per size because that is how the table is keyed.

*Chat panel* — floating bottom-right, opens to a working message thread with a
typing indicator, but every model call is behind one `sendToAgent` function that
currently returns a canned "not connected yet" reply. The header says the same
thing, so the stub is visible without reading the source.

Vite proxies `/api` and `/media` to `:8000` so everything is same-origin in dev.
Verified the build and type-check pass, the API returns 102 products with correct
inventory, and images serve through both the API and the proxy. The rendered
appearance was not checked by eye — the in-app preview is pinned to a different
project directory in this session.

---

## Problem 4 — Create account and log in

**Prompt** — 2026-10-07

> Build a normal create-account / login flow. Create account: first name, last
> name, email, password (confirm password is a nice touch). Log in: email and
> password. New accounts go into the users table. Make sure to store passwords
> securely so hackers (human or AI) cannot access them.

**What Claude did.** Added `backend/security.py` (all password handling in one
auditable place), `backend/auth.py` (signup, login, logout, me), and
`frontend/src/auth.tsx` (session state), and split `backend/db.py` out of
`main.py` so the read-only catalogue connection and the read-write signup
connection are visibly separate.

Passwords are stored as PBKDF2-HMAC-SHA256 at 600,000 iterations with a fresh
16-byte salt each, in a self-describing `pbkdf2_sha256$iterations$salt$hash`
string so the cost can be raised later without invalidating existing passwords.
Verification uses `hmac.compare_digest` so timing does not leak how much of a
guess matched.

On "so hackers cannot access them": the hash never leaves the database. Every
query against `users` names its columns and nothing in the project does
`SELECT *` on that table, so the column cannot leak through a response model
that gains a field later — which also keeps it out of reach when the agent gets
database access in Problem 5.

Sessions are an HttpOnly, SameSite=Lax cookie holding a signed `user_id|expiry`,
so page JavaScript cannot read it and editing the id invalidates the signature.
Login returns one identical `401` for an unknown email and a wrong password, so
the form cannot be used to find out who has an account.

Verified the whole flow against the running API and through the Vite proxy —
signup, duplicate-email `409`, correct and incorrect login, case-insensitive
email, the short-password `422`, a tampered cookie resolving to `null`, and
logout. Test accounts were deleted afterwards, leaving `users` at its original
three rows.

---

## Problem 5 — Build the shop agent (plus voice, safety, run-from-backend)

**Prompt** — 2026-10-07

> The seed database already has a test user. We can use it while building —
> email test@campuscustoms.yale.edu, password "password". Confirm you can log in
> as that user, and that a brand-new account you create also works. Update
> output/harness.md with how auth works (what you store for a user and how
> passwords are protected).

**What Claude did.** The seed user would not log in at first: my verifier assumed
the legacy (count-less) hashes were made at 260,000 iterations, but deriving the
known password against the stored salt showed the seed used **120,000**. Fixed
that one constant — without ever printing the hash — and then confirmed both
cases: the seed user logs in (200, wrong password still 401), and a brand-new
account signs up and logs back in, its hash written in the 4-part self-describing
format at 600,000 iterations. Test accounts were deleted afterwards. Section 4 of
the harness already documented what is stored and how passwords are protected.

**Follow-up prompt** _(login was now confirmed; the actual Problem 5 build — the
agent — came next)_

> Now problem 5: build the shop chatbot as a PydanticAI agent behind FastAPI,
> plugged into the front-end chat widget. Keep the agent as four files next to
> main.py — prompts/prompt.md, agent.py, tools.py, models.py — and expose a chat
> route in main.py so a message from the website returns a reply from the agent.

**What Claude did.** Built the four files and a `POST /api/chat` route. The agent
(PydanticAI, `gpt-5.6-luna` via Portkey) has two read-only tools —
`search_catalogue` and `check_stock` — that touch only the catalogue and
inventory tables, so it has no path to account data by construction, not just by
instruction. The route passes a signed-in shopper's first name to the agent and
nothing else. Replies come back with enriched product objects so the widget
renders cards; those are matched to the reply by the ids the tools surfaced,
with punctuation-normalised name matching. Replaced the Problem-3 `sendToAgent`
stub with the real call. Verified grounded answers, grounded refusals (bad
color, unstocked category), name personalization (anonymous vs signed-in), and a
prompt-injection attempt to exfiltrate user data, which the agent both refuses
and has no tool to satisfy.

**Follow-up prompt** _(the agent worked, but the voice/safety still lived only in
a first-draft prompt, the backend did not yet run the way the course expects, and
none of it was written up)_

> Put Campus Customs voice and safety basics into prompts/prompt.md (you'll
> expand tools and safety later). Start or update types in models.py for chat
> replies / product cards as needed. In output/harness.md, note how the front end
> talks to FastAPI and how the agent is loaded (prompt file + model). Make sure
> the backend runs from the backend/ folder like this:
> uvicorn main:app --reload --port 8000.

**What Claude did.** Expanded `prompts/prompt.md` into Voice / Grounding / Safety
basics (noted in the file as basics, to be expanded later). Refined `models.py`
— `ChatRequest`/`ChatResponse` and the trimmed `ProductCard`, removed the unused
`ProductSearchResult`. Made the backend run from `backend/` as
`uvicorn main:app` by converting the package-relative imports to plain module
imports and removing `backend/__init__.py` (the DB and prompt paths already
resolve from `__file__`). Added harness section 6: the prompt structure, the
chat/card types, the front-end↔FastAPI contract (relative paths, Vite proxy,
`credentials: 'include'`), and how the agent is loaded (prompt file + model,
built once and cached).

---

## Problem 6 — Database-backed lookup tools (description, price, stock)

**Prompt** — 2026-10-07

> Give the agent tools that look up real information from campus_customs.db:
> product description, price, and how many are in stock (by size when the
> customer asks). The agent must use the database and must not invent prices or
> quantities. If a size is out of stock, say so clearly.

**What Claude did.** The Problem-5 agent already read the DB, but made the three
facts first-class. Added a `get_product_details(product_id)` tool returning the
real description, price and a per-size breakdown, and upgraded `check_stock` to
take an optional `size` and return structured `SizeAvailability` entries — each
carrying the real `quantity` and an `in_stock` flag computed in the tool, so
"out of stock" is a fact in the result rather than something the model infers.
`ProductDetails` also returns `sizes_in_stock` / `sizes_out_of_stock` lists so
the model can offer alternatives without reasoning over raw numbers.

New Pydantic types in `models.py`: `SizeAvailability` and `ProductDetails`. The
tool docstrings tell the model to quote price and description exactly and to
state a size as out of stock when `in_stock` is false. Unknown product returns
`None` (distinct from a known product whose size is `[]`), so "no such product"
never reads as "out of stock".

Verified against a product with known zero sizes (Baseball Left Chest Crewneck,
XS and XL at 0): description and $58 quoted exactly, medium reported as 5 in
stock, XL reported out of stock with the real available sizes (S, M, L, XXL)
offered. Unit-checked the tools directly — exact quantities, case-insensitive
size lookup, and the unknown-product vs unknown-size distinction.

**Follow-up prompt** _(the tools existed, but the prompt still described them
only generically and nothing documented why the result types carry the fields
they do)_

> Expand prompts/prompt.md so the agent knows to call these tools for price and
> stock questions. Add or update return types in models.py. In
> output/harness.md, list each tool and explain which model fields you chose for
> lookup results and why.

**What Claude did.** Rewrote the grounding section of the prompt to name all
three tools and say when to use each, with an explicit rule to call a tool for
any price or stock question rather than answering from a search snippet or
memory. Updated the three lookup result types in `models.py` with per-field
`Field(description=...)` so each field's purpose is explicit in code. Added
harness section 8 listing every tool and justifying each field on its return type
— what was included, what was deliberately left off, and the through-line that
every result carries both the raw fact (`quantity`, `sizes`) and the derived
decision (`in_stock`, `sizes_in_stock`/`sizes_out_of_stock`) so the model reports
availability rather than inferring it. Verified a bare "how much is X" still
quotes the real price ($68).

---

## Problem 7 — Dynamic product cards (agent → front-end contract)

**Prompt** — 2026-10-07

> Add a feature: when a customer asks about a type of item ("what hoodies do you
> have?"), the agent should search the catalogue and the website should
> dynamically show the matching items as product cards (image, name, price, short
> info). This is an API contract — the agent returns structured product matches
> and the front end renders them.

**What Claude did.** The chat response already carried structured products and the
widget already rendered cards (from Problem 5), so the work was to make the
contract robust and finish the card UI.

Replaced the fragile match-selection logic — which parsed the reply prose for
product names and broke on things like "1/4 Zip" vs the catalogue's "1 4 Zip" —
with a deterministic rule that reads the agent's **tool activity**: ids passed to
`get_product_details` / `check_stock` are "specific lookups" and win when present;
otherwise the `search_catalogue` results are the matches. No string matching, and
the cards can never drift from what the agent actually retrieved. This gives the
two behaviours for free: a category question ("what hoodies") shows all search
matches, a specific question ("how much is X") shows just that one.

Finished the card on the front end: each card now shows image, name, price, and a
two-line short-info line (the catalogue description), and links to the detail
page. Documented the full request/response contract in harness section 9.

Verified: "what hoodies" → 8 cards with all four fields; "how much is the Basic
Hoodie Big Yale" → exactly 1 card despite the search surfacing several hoodies;
"baseball crewneck in XL" → 1 card with the out-of-stock answer; "yo" → 0 cards.

---

## Problem 8 — Chat cards open the single-item page

**Prompt** — 2026-10-07

> After the dynamic product cards are loaded by the new feature, make sure the
> same single-item page still works: each product card, including the ones the
> chat just put on the page, should still open that detail view (large image +
> full info) when clicked. Update prompts/prompt.md and output/harness.md so it is
> clear how search results reach the page.

**What Claude did.** Confirmed the chat cards use the same mechanism as the grid
cards — a react-router `<Link to="/products/{product_id}">` into the one detail
route `/products/:productId`, which renders `ProductDetail` and fetches
`GET /api/products/{id}`. Nothing is special about a chat-created card: it carries
a real catalogue `product_id`, so it resolves through the identical route and
endpoint, and it closes the chat panel on click so the detail page is in view.

Verified with live data: asked "what hoodies do you have?", took the 8
`product_id`s the chat surfaced, and confirmed every one returns 200 from both the
single-item endpoint (what the detail page fetches) and the SPA deep link (so a
click and a refresh both work), through the same Vite proxy the browser uses.

Updated `prompts/prompt.md` to explain how results reach the page — the site adds
a clickable card for every product the agent looks up with a tool, so the agent
answers in words and "puts a product on the page" by looking it up, not by naming
it. Added harness section 10 tracing the full path (search → match ids → response
products → Link card → detail route → single-item endpoint) and why chat cards and
grid cards open the same view.

---

## Problem 9 — Chat history, shopper identity, page context

**Prompt** — 2026-10-07

> When a shopper is logged in, save their chat history in the database and reload
> it when they return. The agent should know who is chatting (name, email) — put
> that in agent deps (or an equivalent pattern) and/or tools. Also pass enough
> page context that if someone is on a product page and asks "do you have this in
> pink?", the agent knows which item they mean. You can put code into the agent
> context.

**What Claude did.** Used the existing `chat_messages` table (no migration).
Added `backend/history.py` to save and load turns and to convert stored turns into
pydantic-ai message history for context. `POST /api/chat` now loads a logged-in
shopper's prior turns, replays them to the agent, and saves this turn; anonymous
sessions are neither loaded nor persisted. Added `GET /api/chat/history` for the
widget to replay on return.

Put identity in `ChatDeps` (`first_name`, `full_name`, `email`), filled from the
**session** not the message, so the agent knows who it is talking to without any
tool that can read the users table — the account-data firewall stays intact. Page
context also goes in deps: the widget sends `current_product_id` when on a product
page, the backend loads that product into deps, and an instruction tells the agent
that "this"/"it" means that product.

Found and fixed a real bug while testing: the dynamic context was written as
`system_prompt`, which pydantic-ai does **not** re-apply when `message_history` is
passed — so returning shoppers lost the base prompt and page context ("this"
became "which item?"). Moved the whole prompt to `instructions`, which are
re-evaluated every run and not stored in history, fixing it.

Frontend: `ChatWidget` reloads saved history on login/return (resets on logout)
and sends the current product id with each message. Verified identity greeting,
"do you have this in pink?" → navy/white not pink with a correct "in large?"
follow-up, DB persistence, reload across a fresh login, and that anonymous
sessions persist nothing. Throwaway accounts deleted; seed data confirmed intact.

**Follow-up prompt** _(the behaviour was right, but guest chat needed an explicit
check and the three mechanisms needed a clear write-up)_

> Guests can still chat, but history only needs to remain for logged-in users.
> Document in output/harness.md: how user chat history is stored, what customer
> fields the agent sees, and how page context is passed.

**What Claude did.** Confirmed guest chat already works and persists nothing — a
cookie-less chat returns a normal reply with product cards and leaves the message
count unchanged (no code change needed; persistence was already gated on a
resolved session). Added harness section 12 as a focused reference: a guest-vs-
logged-in table, exactly how history is stored (the `chat_messages` columns, one
row per turn, enriched `products_json`, per-user scoping, the two read paths), the
precise set of customer fields the agent sees (`first_name` / `full_name` /
`email` from the session — never the hash, id, or order data, and no tool to reach
them), and the four-step path by which page context travels from the route through
`current_product_id` into deps and the instruction.

---

## Problem 10 — Usability improvements (2 front end, 2 backend)

**Prompt** — 2026-10-07

> Now that the core shop works, improve usability. Choose and implement 2
> front-end usability improvements and 2 agent/backend usability improvements
> (make the agent output better, more accurate, safer, faster, or cheaper — could
> be new tools).

**What Claude did.** Picked four that fix real gaps.

Front end:
1. **Products page search + sort + in-stock filter** — the page listed all 102
   items with no way to narrow. Added a client-side search (name, description,
   type, tags, colors), a sort (name / price asc / price desc), an in-stock-only
   toggle, a live result count, an empty state, and a "Sold out" badge. Instant,
   no extra requests.
2. **Markdown-rendered chat replies** — the agent emits markdown (bold prices,
   bullet lists) that was showing as raw `**` and `-`. Assistant bubbles now
   render via `react-markdown` (no raw HTML, so no injection surface); user
   messages stay plain.

Backend:
3. **In-memory catalogue cache** — the catalogue/inventory were re-queried and
   re-parsed on every tool call though they never change at runtime. Cached the
   product list with a 300s TTL; measured first load 9.2ms → cached 0.002ms
   (~4500× faster), zero DB work for the rest of a turn. `clear_cache()` for tests
   / future writes.
4. **`filter_products` tool** — exact structured filtering (garment type, color,
   price range, in-stock size), sorted cheapest first, for constrained queries
   that fuzzy text search handles badly. Now "crewnecks under $60 in large"
   returns only $58 crewnecks with L in stock, and "hoodies under $60" correctly
   returns none (hoodies are $68) instead of ignoring the price.

Verified the build, the cache speedup, the filter correctness (including excluding
the XL=0 baseball crewneck from an "XL in stock" filter), and that the agent
reaches for the filter tool on constrained queries.

**Follow-up prompt** _(the improvements worked but were only documented inside the
harness; graders need a dedicated write-up and proof the features are live)_

> Write output/usability.md before or as you build. For each improvement say what
> you added and why it helps a Campus Customs shopper or the business, then make
> sure all improvements actually show up in the running app.

**What Claude did.** Wrote `output/usability.md` — one entry per improvement with
"what was added" and "why it helps the shopper or the business", plus where to see
each in the app.

Then tried to view the running app to confirm the features render. Both browser
tools were unavailable this session: the in-app preview is pinned to the hw3
project root, which the sandbox blocks processes from running in (`getcwd` EPERM),
and the Claude-in-Chrome extension is not connected. So visual confirmation by
screenshot was not possible, and that limit is stated plainly rather than papered
over. Instead verified the strongest way available without a browser: confirmed the
running Vite dev server is serving the new feature code (the live
`Products.tsx`/`ChatWidget.tsx` modules contain the controls bar, sold-out badge,
and markdown renderer, and `react-markdown` resolves with 200), the build and
type-check pass, `/api/products` returns the data the client filter needs, and the
agent answers constrained queries through the new filter tool. The app is running
on `:5173` (frontend) and `:8000` (backend) for a grader to open directly.

---

## Problem 11 — Storefront redesign (front end only)

**Prompt** — 2026-10-07

> Give the site a real storefront feel. Redesign with a creative original look:
> a Yale-inspired palette (deep blue + bold accent) and a distinctive font
> pairing; strong hero, clear section headings, spacing; subtle motion (card
> hover, fade-ins on scroll, smooth page transitions); polished product cards and
> a more premium single-item page (image zoom/gallery, price + stock badges); a
> branded chat panel with a nice header, styled bubbles, a typing animation, and
> quick-reply chips. Keep it working and readable on mobile. Don't change the back
> end.

**What Claude did.** A full front-end redesign, backend untouched.

- **Palette + type:** deep Yale navy with a bold gold accent, as `:root` tokens;
  Fraunces (display serif) + Inter (body) from Google Fonts.
- **Hierarchy:** a strong hero (oversized headline, gold accent line, eyebrow,
  dual CTAs, a stats row) and clear eyebrow-led section heads with more spacing.
- **Motion:** scroll-reveal via one IntersectionObserver (`useReveal`, re-scans on
  route change), route fade transitions, card/image/nav hover effects, a drifting
  hero glow — all behind `prefers-reduced-motion`.
- **Products:** polished hover-lift cards with image zoom-on-hover, garment-type
  eyebrow, Fraunces price, and Sold out / Low stock badges; the detail page got a
  sticky media column with cursor-tracked magnification, a badge, and tactile size
  buttons.
- **Chat:** branded header (gold CC avatar, title, pulsing "online" dot), navy/white
  gradient bubbles, a three-dot typing animation, one-tap quick-reply chips, and a
  gold "Ask us" launcher that pops the panel in.
- **Mobile + a11y:** nav/grids/hero/detail/chat all reflow for small screens;
  reduced-motion honoured; gold focus rings; real buttons with labels.

Verified the build and type-check pass and the running server serves all the new
code (fonts, tokens, component markers), and confirmed the backend is unchanged
(`/api/health` still 102, chat still returns cards). Could not check rendered
pixels by eye — neither browser tool was available this session (in-app preview
pinned to a sandbox-blocked dir; Chrome extension not connected) — so verification
was by build + served-code inspection, stated plainly. Documented in harness
section 14.

**Follow-up prompt**

> Write output/design.md: what you changed and why it should help customers stick
> around and buy. Keep it concrete and short.

**What Claude did.** Wrote `output/design.md` — a short, concrete write-up grouped
by surface (look/feel, Home, Products, product page, chat, motion, mobile), each
change paired with a one-line "why" tied to shopper retention or conversion
(trust, faster path to relevant products, confidence to add to cart, low-stock
nudge, mobile traffic).

---

## Problem 12 — Live app check page with screenshots

**Prompt** — 2026-10-07

> Test the live site and document it in output/app_check.html (double-click
> openable). Include clear screenshots + short captions for: (1) chat checking an
> item's inventory (honest stock/price from the DB), (2) the dynamic search-result
> cards after a category question, (3) one usability feature from Problem 9. Put
> images in output/app_check_images/ and link them with relative paths.

**What Claude did.** Captured real screenshots of the running app. Both in-session
browser tools were unavailable (in-app preview sandbox-pinned to hw3; Chrome
extension not connected), so used Playwright driving the system Chrome
(`channel: 'chrome'`, no download) against the live backend+frontend — every chat
answer a real agent response from `campus_customs.db`.

Built `output/app_check.html` (self-contained, styled, double-click openable) with
a heading, screenshot, and 1–2 sentence caption per check: honest inventory/price
(Baseball crewneck XL out of stock, $58), dynamic hoodie search cards, the Products
search/sort/filter usability feature, plus a bonus premium detail page. Images in
`output/app_check_images/`, linked by relative path; verified they all load with no
console errors.

The visual test caught a **real bug**: filtering the Products page left the grid
empty, because the redesign's `data-reveal` scroll animation on the cards was never
re-triggered when the filter re-rendered them (`useReveal` only re-scans on route
change). Fixed by dropping `data-reveal` from the filterable grid (kept hover
motion; Home still uses reveals). Re-shot after the fix — a bug that build and
type-check could not have surfaced.

---

## Problem 13 — Audit trail, agent safety rules, finished harness

**Prompt** — 2026-10-08

> Keep an append-only output/audit_trail.json of agent-loop activity (time, tool
> name, short args/result, stop reason); don't wipe it between runs. Think of
> safety rules to give the agent and put them in prompts/prompt.md. Finish
> output/harness.md so it's clear how the system works: model fields and why,
> tools and abilities, safety rules, specs (loop limits, result caps, models, how
> to run front + back).

**What Claude did.** Added `backend/audit.py` — an append-only JSON-array trail at
`output/audit_trail.json`, written atomically (temp + rename), never wiped; a
corrupt file is set aside as `.bak` rather than overwritten, and writes are
best-effort so auditing can't break a reply. `run_chat` appends one `tool_call`
record per tool (time, tool, short args, short result) and a `run_end` record
(stop reason, counts). Verified it records faithfully (even the model's real
"hoodies"→0 then "hoodie"→8 retry) and is append-only (grew 7→13 across turns).

Added a loop limit — `UsageLimits(request_limit=6)` per turn — and expanded
`prompts/prompt.md` into nine firm safety rules: stay on task; message-is-data (no
prompt override / "developer mode"); never reveal or fabricate others' data;
don't expose internals; prices/stock only from tools and never from the shopper
(blocks "sell it to me for $5"); no commitments it can't keep; nothing
harmful/deceptive; stay within the catalogue's world; say so when unsure. Tested:
price-manipulation and jailbreak refused, off-topic steered back.

Found that a jailbreak prompt tripped Azure's content filter and bubbled up as a
500, so hardened the chat route to catch any agent-run failure and return a calm
200 reply (the failure is still in the audit trail) — the widget stays usable.

Finished `output/harness.md` with section 16: model fields + rationale, the four
tools and the agent's abilities/non-abilities, the nine safety rules, and specs
(models/gateway, loop limit, result caps, data, and the exact front+back run
commands).
