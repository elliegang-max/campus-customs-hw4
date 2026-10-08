# Campus Customs

A full-stack shop for Yale-themed apparel: a Vite + React + TypeScript storefront,
a FastAPI backend, and a PydanticAI shopping assistant that answers from a real
SQLite catalogue (descriptions, prices, and per-size stock) and renders matching
products as cards in the chat.

> Campus Customs is a fictional shop built for a course assignment. It is not
> affiliated with, endorsed by, or a partner of Yale University or any real
> retailer.

## Features

- **Storefront** — Home, Products (search / sort / in-stock filter), a premium
  single-item page with image zoom, About, and login / create-account.
- **Shop assistant** — a PydanticAI agent behind `POST /api/chat` with read-only
  tools over the catalogue; it never invents prices or stock, states out-of-stock
  sizes clearly, knows the signed-in shopper (name/email, from the session) and the
  product page they're on ("do you have *this* in pink?").
- **Dynamic product cards** — a category question ("what hoodies do you have?")
  renders the matches as clickable cards that open the product page.
- **Accounts** — PBKDF2 password hashing, HttpOnly signed-cookie sessions; the hash
  is never selected into any response and the agent has no tool that can read it.
- **Persistent chat history** for logged-in shoppers; guests can chat but aren't
  persisted.
- **Safety + audit** — nine agent safety rules, a per-turn request limit, graceful
  failure handling, and an append-only `output/audit_trail.json` of tool activity.

## Repository layout

```
hw4/
├── AI_prompts.md          # log of the prompts used to build this
├── requirements.txt       # backend Python deps
├── .env.example           # environment template (copy to .env)
├── .gitignore
├── README.md
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app — run with: uvicorn main:app --reload --port 8000
│   ├── agent.py           # PydanticAI agent wiring
│   ├── models.py          # Pydantic types
│   ├── tools.py           # agent tools + catalogue loading
│   ├── auth.py  db.py  history.py  security.py  audit.py
│   └── prompts/prompt.md  # system prompt (voice, grounding, safety)
└── output/                # harness.md, design.md, usability.md, app_check.html, audit_trail.json
```

## The data pack (not in git)

The SQLite database and product images are **not** committed. Place the provided
data pack at the project root so the layout is:

```
hw4/data/
├── campus_customs.db
└── products/              # product images referenced by the catalogue
```

## Setup

**1. Environment.** Copy the template and fill in your values (or export them):

```bash
cp .env.example .env
# edit .env: PORTKEY_API_KEY, PORTKEY_BASE_URL, CAMPUS_CUSTOMS_SECRET_KEY
```

The backend reads these from the process env, then `./.env`, then
`~/.config/ai-keys/keys.env` — whichever provides them first.

**2. Backend** (Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

**3. Frontend** (Node 18+), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` and `/media` to the
backend on `:8000`, so everything is same-origin in development.

**Seed login:** `test@campuscustoms.yale.edu` / `password`.

## Documentation

- `output/harness.md` — how the whole system works (models, tools, safety, specs).
- `output/design.md` — the storefront redesign and why it should help shoppers.
- `output/usability.md` — the usability improvements and their rationale.
- `output/app_check.html` — screenshots of the live app (double-click to open).
