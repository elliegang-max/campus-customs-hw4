# Campus Customs — Usability Improvements

Four improvements: two on the front end (how the site looks and feels) and two on
the agent/backend (how good, accurate, and cheap the assistant is). For each: what
was added, and why it helps a Campus Customs shopper or the business.

Where to see each one in the running app is noted so it can be checked quickly.

---

## Front end

### 1. Search, sort, and in-stock filtering on the Products page

**What was added.** The Products page now has a controls bar above the grid:

- a **search box** that filters as you type, across product name, description,
  garment type, search tags, and colors;
- a **sort** dropdown — Name (A–Z), Price (low to high), Price (high to low);
- an **In stock only** toggle;
- a live **result count** ("12 of 102 products") and a clear "nothing matches"
  message when a search comes up empty;
- a **"Sold out" badge** on the image of any product with no stock in any size.

Filtering and sorting happen instantly in the browser over the already-loaded
catalogue, so there is no spinner and no extra network request per keystroke.

**Why it helps.** With 102 products, a plain grid makes a shopper scroll and hunt.
Search lets someone who wants "Saybrook" or "a navy quarter-zip" get there in a
second; sorting by price helps a budget shopper; the in-stock filter and sold-out
badge stop shoppers from falling for something they can't actually buy. For the
business, that is less bounce and fewer "why can't I check out?" dead ends.

**Where to see it.** Products page → the controls bar above the grid. Type
"hoodie", switch sort to Price (low to high), tick "In stock only".

### 2. Properly formatted (markdown) chat replies

**What was added.** The shop assistant writes in markdown — bold prices, bulleted
product lists. The chat panel used to show that as raw text, so a reply looked
like `We have these hoodies, all **$68**: - Basic Hoodie...`. Assistant messages
now render markdown: bold shows as bold, lists as real bullet points, paragraphs
with proper spacing. (User messages stay plain text, and the renderer emits no raw
HTML, so there is nothing a message could inject.)

**Why it helps.** A readable answer is a usable answer. When the assistant lists
six hoodies with prices, bullet points and bold prices make it scannable instead
of a wall of text with stray asterisks. It makes the assistant feel finished and
trustworthy rather than broken — which matters for whether shoppers use it at all.

**Where to see it.** Open the chat (bottom-right), ask "what hoodies do you
have?" — the reply is a bulleted list with bold prices, and product cards below.

---

## Agent / backend

### 3. A `filter_products` tool for exact, constrained queries (more accurate)

**What was added.** A new agent tool that filters the catalogue by hard criteria —
garment type, color, a price range, and a size that must be in stock — and returns
results cheapest-first. The older search tool ranks by fuzzy word overlap, which
is poor at numbers and stock: it can't really tell "under $60" from "$68", because
price isn't a word in the description. The agent is told to prefer the new tool
when a shopper gives firm constraints.

**Why it helps.** Shoppers ask constrained questions: "crewnecks under $60 that
come in large," "anything navy under $50." With the filter, those get **correct**
answers — only items that truly meet every condition. Crucially it also gets the
negative right: "do you have any hoodies under $60?" now answers "no" (hoodies are
$68) instead of cheerfully listing hoodies and ignoring the budget. For the
business, accurate answers build trust and avoid the frustration (and support
load) of a shopper being pointed at something that doesn't fit their ask.

**Where to see it.** In the chat, ask "show me crewnecks under $60 available in
large" (returns only $58 crewnecks with L in stock) and "do you have any hoodies
under $60?" (correctly: none).

### 4. In-memory catalogue cache (faster and cheaper)

**What was added.** The catalogue and inventory were read from the database and
re-parsed on every tool call — several times per chat turn — even though that data
doesn't change while the app runs. The product list is now built once and served
from an in-memory cache (300-second refresh). Every tool — search, filter, detail
lookup, stock check — reads from it.

**Why it helps.** It makes the assistant snappier: a measured catalogue load
dropped from ~9ms to ~0.002ms once cached (about 4500× faster), so the time a
shopper waits for a reply is spent on the model, not on repeated database work.
For the business it means the backend does far less work per conversation, so it
costs less to run and holds up better under many shoppers at once.

**Where to see it.** Not visible as a widget — it shows up as quicker replies. It
is verifiable in `output/harness.md` §13.3 (the measured 9ms → 0.002ms) and by the
assistant answering with no per-call database latency.

---

## All four are live

Run the backend (`cd backend && uvicorn main:app --reload --port 8000`) and the
front end (`cd frontend && npm run dev`), open the site, and each feature above is
present at the location noted. Section 13 of `output/harness.md` records the
implementation detail and the verification for each.
