# ShopSense

AI-powered e-commerce platform that fixes real gaps in Indian online shopping: all-inclusive prices
up-front (no drip pricing), seller details on every listing, verified reviews, multilingual + voice
shopping, and trackable grievances. See [CLAUDE.md](CLAUDE.md) for the full context and roadmap.

**Stack:** FastAPI (async) · SQLAlchemy 2.0 + asyncpg · PostgreSQL 16 + pgvector · Redis 7 · React (Vite)

## Quick start
```bash
npm run setup     # once: Python venv + packages, frontend packages, backend/.env
npm run dev       # every time: applies DB migrations, then API on :8000 + web app on :5173
npm test          # run the backend tests
npm run migrate   # apply database migrations only (Alembic)
npm run seed      # demo sellers, 14 products (photos + embeddings), buyers and 23 verified reviews
npm run embed     # (re)compute product embeddings for smart search
```
Before the first `npm run dev`, put your database details in `backend/.env` (see step 2 below).
API docs: http://localhost:8000/docs · Web app: http://localhost:5173

The detailed manual steps are below.

## Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows: uses WSL2)
- Python 3.11+ (3.12 recommended)
- Node.js 20+ (frontend only)

## Setup

### 1. Configure environment
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env`: set `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`. You can generate a key with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. Start Postgres (pgvector) and Redis

**Option A: Docker (local)**
```bash
docker compose up -d
```
Postgres is exposed on host port **5433**, so it won't clash with a local Postgres on 5432.
On first start the container also creates the `shopsense_test` database.

**Option B: Neon (cloud, no Docker)**
1. Create a free project at [neon.tech](https://neon.tech) (Postgres 16+, pgvector included).
2. In the Neon console → *Databases*, add a second database named `shopsense_test`.
3. Copy the **direct** connection string (not the `-pooler` one) into `backend/.env`:
   `POSTGRES_HOST`, `POSTGRES_PORT=5432`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
   `POSTGRES_DB`, and `POSTGRES_SSL=require`.

Redis isn't used until a later phase.

### 3. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open **http://localhost:8000/docs**. Run `alembic upgrade head` first (from backend/) to create the tables; `npm run dev` does this for you.

### 4. Tests
```bash
cd backend
pytest
```
The pricing and security tests always run. The API tests use the `shopsense_test` database and
are skipped if it isn't reachable.

### 5. Create an admin (optional)
Admins cannot self-register:
```bash
cd backend
python -m app.scripts.create_admin --name "Admin" --email admin@example.com
```

### 6. Frontend (customer storefront)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. `/api` requests are proxied to the backend. Load demo products with `npm run seed`.

The storefront is React + TypeScript + Tailwind: catalogue with categories and search, product pages with the full price breakdown and seller card, cart, checkout (explicit payment choice), order timeline with cancel, guided wrong/fake-item returns, English/हिंदी/मराठी, and light/dark mode.

## Try the API in /docs
1. `POST /api/v1/auth/register` with `"role": "seller"`
2. Click **Authorize** and log in with your email as the username
3. `POST /api/v1/sellers/me` to create your seller profile
4. `POST /api/v1/products` to list a product
5. `GET /api/v1/products` (public): every item includes `price` (base, delivery, platform fee, GST,
   final price) and a `seller` card
6. Register a **customer**, then `POST /api/v1/cart/items` and `GET /api/v1/cart`
7. `POST /api/v1/orders` with `payment_method` (`upi` / `card` / `cod`) and `expected_total` set to
   the cart's `totals.grand_total`
8. As the seller: `PATCH /api/v1/sellers/me/orders/{id}/status` → `shipped` → `delivered`
9. As the customer: `POST /api/v1/returns` (reason `wrong_item` / `counterfeit` / `damaged` / `other`)
10. As an admin (see step 5 of setup): `POST /api/v1/admin/returns/{id}/resolve`

## Consumer protections built in
| Problem | What ShopSense does |
|---|---|
| Drip pricing | Every product, cart line and order shows the all-inclusive price. Checkout refuses to charge anything other than the `expected_total` the customer saw (409 if prices changed). |
| Dark patterns | Cart items are only added by the customer. Payment method is a required, explicit choice; COD is never switched on silently. |
| Overselling | Product rows are locked (`SELECT … FOR UPDATE`) during checkout, so two buyers can't both get the last unit. |
| Wrong / fake items | Wrong-item and counterfeit returns are always accepted within 7 days of delivery, even for "non-returnable" products. Approved ones lower the seller's trust score. |
| Hidden seller details | Seller card (address, GSTIN, grievance officer, trust score) on every listing. |
| Untrustworthy reviews | Only buyers with a delivered order can review. Every honest review is published, good or bad; suspected fakes are held for moderation and the page says how many are being checked. |
| Poor grievance handling | Complaints are acknowledged instantly and tracked on a timeline with a one-month deadline. AI answers pure information questions (with the real order data) and is **never** allowed to close money, fake-item, damage or seller complaints; those go to the grievance team, most urgent first. |
| Order transparency | Every order has a status timeline (placed → shipped → delivered / cancelled) and a price snapshot from the moment of purchase. |

## Pricing rule
`taxable = base + delivery + platform fee` → `GST = taxable × gst%` → `final = taxable + GST`.
Every line is rounded half-up to 2 decimals, so the lines always add up to the final price.

## AI features (all free)
| Feature | How |
|---|---|
| **Smart search** (`GET /api/v1/search`) | Product text is embedded locally with a multilingual model (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d, via fastembed/ONNX) and stored in **pgvector** with an HNSW index. Queries combine cosine similarity with keyword matching, so "something cool to wear in summer" finds a cotton kurta and "कान में लगाने वाला ब्लूटूथ" finds earbuds. |
| **Shopping assistant** (`POST /api/v1/assistant/chat`) | A **LangChain** tool-calling agent on **Google Gemini** (free tier). Tools read live data (RAG): product search, full price breakdown + seller disclosure, return policy, and, for logged-in customers, their orders. Answers in English, हिंदी, मराठी or Hinglish; product cards come from the database, never from the model. Retries, a fallback model, a per-message call limit and a timeout keep it reliable within the free quota. |
| **Voice input** | Browser Web Speech API in en-IN / hi-IN / mr-IN. |
| **AI review summary** (`GET /api/v1/products/{id}/reviews/summary`) | Gemini summarises only published, verified reviews into a verdict + pros/cons in English, हिंदी or मराठी. Cached per language and regenerated only when new reviews arrive. |
| **Fake-review detection** | Explainable signals (no AI quota): near-duplicate text via embeddings (flags both copies), links/phone numbers, same-star bursts, one-seller 5★ patterns, very short extreme ratings, reviews minutes after delivery. Suspicious reviews wait in an admin queue (`/api/v1/admin/reviews`) with their reasons. |

Setup: add a free key from https://aistudio.google.com/apikey as `GEMINI_API_KEY` in `backend/.env`. The first run downloads the ~250 MB embedding model to `~/.cache/shopsense`.

## Credits
Demo product photos are hot-linked from [Unsplash](https://unsplash.com) and used under the [Unsplash License](https://unsplash.com/license).
