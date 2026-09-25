# ShopSense

AI-powered e-commerce platform that fixes real gaps in Indian online shopping: all-inclusive prices
up-front (no drip pricing), seller details on every listing, verified reviews, multilingual + voice
shopping, and trackable grievances. See [CLAUDE.md](CLAUDE.md) for the full context and roadmap.

**Stack:** FastAPI (async) · SQLAlchemy 2.0 + asyncpg · PostgreSQL 16 + pgvector · Redis 7 · React (Vite)

## Quick start
```bash
npm run setup     # once: Python venv + packages, frontend packages, backend/.env
npm run dev       # every time: API on :8000 and web app on :5173 together
npm test          # run the backend tests
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
Open **http://localhost:8000/docs**. On startup the app enables the `vector` extension and creates the tables.

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

### 6. Frontend (optional in Phase 1)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. `/api` requests are proxied to the backend.

## Try the API in /docs
1. `POST /api/v1/auth/register` with `"role": "seller"`
2. Click **Authorize** and log in with your email as the username
3. `POST /api/v1/sellers/me` to create your seller profile
4. `POST /api/v1/products` to list a product
5. `GET /api/v1/products` (public): every item includes `price` (base, delivery, platform fee, GST,
   final price) and a `seller` card

## Pricing rule
`taxable = base + delivery + platform fee` → `GST = taxable × gst%` → `final = taxable + GST`.
Every line is rounded half-up to 2 decimals, so the lines always add up to the final price.
