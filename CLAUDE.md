# ShopSense — project context for Claude

AI-powered e-commerce platform (resume project). Fixes real gaps in Indian e-commerce first
(then global), based on LocalCircles consumer surveys.

## Product goals (each maps to a feature)
1. **Drip pricing** (75% face hidden fees) → all-inclusive final price shown up-front on every
   product. Every product API response includes a server-computed price breakdown.
2. **Wrong/counterfeit products** → guaranteed wrong/fake-item return path + seller trust score.
3. **Hidden seller details** (7 in 10 can't find them) → seller info card on every listing
   (BIS IS 19598:2026 style; also Consumer Protection (E-Commerce) Rules 2020: GSTIN,
   grievance officer, country of origin).
4. **Untrustworthy reviews** → publish all verified reviews + AI review summariser + fake-review detection.
5. **Language barrier (tier-2/3)** → multilingual (en / hi / hinglish / mr) + voice AI shopping assistant.
6. **Poor grievance handling** → complaint tracker with status timeline; AI resolves simple cases,
   escalates the rest.

**No dark patterns:** no auto-added cart items, no silent COD conversion, explicit consent for data.

## Tech stack (do NOT add .NET or other backends)
- Backend: Python 3.11+ (3.12 recommended), FastAPI (async), SQLAlchemy 2.0 async + asyncpg,
  Pydantic v2, pydantic-settings
- Auth: JWT via PyJWT; password hashing via `bcrypt` directly (NOT passlib)
- DB: PostgreSQL 16 + pgvector (Docker image `pgvector/pgvector:pg16`), Redis 7
  (cache / sessions / Celery later)
- AI (later): LangChain, RAG over products + reviews, embeddings in pgvector (`Vector(384)`,
  i.e. all-MiniLM-L6-v2-sized). LLM provider not chosen yet — ask before Phase 3.
- Frontend: React (Vite)
- DSA features (later): trie autocomplete, heap top-K recommendations, LRU cache for recently
  viewed, co-purchase graph for "bought together", sliding-window rate limiter.

## Architecture
Three role-based portals (customer, seller, admin) → FastAPI gateway (JWT + role-based access +
rate limiting) → services (commerce APIs, search & recommendations, AI assistant) → AI layer
(LangChain agent, RAG retriever, LLM) → data (PostgreSQL, pgvector, Redis).

## Layout
```
backend/app/
  api/        deps.py (CurrentUser/CustomerUser/SellerUser/AdminUser/CurrentSeller, require_role),
              router.py, routes/{auth,sellers,products,cart,orders,returns,admin}.py
  core/       config.py (pydantic-settings), security.py (bcrypt + JWT), errors.py,
              policies.py (business rules: max qty, return window, trust penalty)
  db/         base.py, session.py (engine, get_db), types.py (pg_enum, utcnow)
  models/     User, Seller, Product, CartItem, Order/OrderItem/OrderEvent, ReturnRequest
  schemas/    Pydantic request/response models
  services/   business logic — HTTP-agnostic (pricing, user, seller, product, cart, order, return)
  ai/         (Phase 3+) LangChain / RAG
  scripts/    create_admin.py (admins cannot self-register)
backend/migrations/  Alembic (async env; 0001 Phase 1 schema, 0002 cart/orders/returns)
backend/tests/  pytest (pricing + security run anywhere; API tests need the test DB)
frontend/       Vite + React 19 + TypeScript 7 + Tailwind v4 (customer storefront)
  src/lib/        api.ts (fetch wrapper, token), queries.ts (TanStack Query hooks), types.ts, format.ts
  src/i18n/       strings.ts (en/hi/mr UI text), I18nProvider (t(), category())
  src/theme/      ThemeProvider (light/dark/system, class on <html>)
  src/auth/       AuthProvider (JWT in localStorage, /auth/me), RequireCustomer
  src/components/ ui/ primitives (Button, Card, Badge, Field…), PriceBreakdown, SellerDetails,
                  ProductCard, OrderTimeline, ReturnForm, layout/Header
  src/pages/      Home, Product, Cart, Checkout, Orders, OrderDetail, Returns, Login/Register
docker-compose.yml  Postgres+pgvector (host port 5433) and Redis (6379), named volumes
```

## Conventions
- Type hints everywhere; small focused files; docstrings on anything non-obvious.
- Money is always `Decimal` (DB `Numeric(10,2)`), rounded ROUND_HALF_UP to 2 places.
  Never floats. JSON serialises Decimals as strings (e.g. `"1239.00"`).
- Pricing rule: `taxable = base + delivery + platform_fee`; `gst = round(taxable * gst% / 100)`;
  `final = taxable + gst`. Each line is rounded so displayed lines always sum to the final price.
  Only `services/pricing.py` computes prices.
- Services raise `AppError` subclasses (`core/errors.py`); a handler in `main.py` maps them to HTTP.
  Routes stay thin.
- Authorization uses the role stored in the DB, not the JWT claim.
- bcrypt runs in a thread (it's CPU-bound) so it doesn't block the event loop.
- Relationships use `lazy="raise"`; load explicitly with `selectinload` (async-safe).
- Proper HTTP status codes (201 create, 401 bad credentials, 403 wrong role, 404, 409 duplicate, 422 validation).
- Never hard-code secrets; everything comes from `backend/.env` (template: `.env.example`).
- API prefix `/api/v1`. CORS allows `http://localhost:5173`.
- Frontend: design tokens are CSS variables in `index.css` (use `bg-surface`, `text-muted`,
  `bg-brand`, `border-line`… never raw hex); every UI string goes through `t()` with en/hi/mr
  entries; money is formatted with `formatINR` from the API's decimal strings; mobile-first.
  Check with `npm --prefix frontend run typecheck`. Never type passwords into the browser when
  verifying: logged-in flows are for the user to click through (API tests cover them).
- **Schema changes go through Alembic**: edit models → `alembic revision --autogenerate -m "..."`
  (from backend/) → review it (autogenerate duplicates shared PG enums and forgets to drop enum
  types on downgrade: create enums explicitly with `create_type=False`) → verify on the test DB with
  `alembic -x db=test upgrade head` + `alembic -x db=test check`. The app no longer creates tables at startup.
- Orders: checkout creates one order per seller; prices are snapshotted on OrderItem and never
  recomputed; checkout requires `expected_total` == server total (409 otherwise); products are
  locked `FOR UPDATE` in id order. Fees are per unit, so totals = Σ unit final price × qty.
- Tests share one pooled engine per run (session event loop) and TRUNCATE between tests;
  `BCRYPT_ROUNDS=4` in tests. Full suite ≈ 2.5 min against Neon (network-bound).

## Local environment notes
- Run like the user's Next.js portals: `npm run setup` (once), `npm run dev` (API + web together
  via concurrently), `npm test`. Root `package.json` + `scripts/*.mjs` wrap the venv at `backend/.venv`.
- The dev machine also runs a native PostgreSQL 18 on 5432 (no pgvector), so the Docker
  Postgres is exposed on **5433**.
- Docker is on hold (WSL2 not installed yet). Current dev DB: **Neon** cloud Postgres with
  `POSTGRES_SSL=require` (direct host, not `-pooler`, because asyncpg prepared statements break
  behind PgBouncer). Test DB is a second Neon database `shopsense_test`. Redis unused until later.
- Tables are managed by Alembic migrations (`npm run migrate`, also run automatically by `npm run dev`).

## Phases
- **Phase 1 (done):** config, DB, models (User/Seller/Product), pricing service, auth (register/login/me),
  role dependency, seller profile, product list/get/create with price breakdown + seller card, tests.
- **Phase 2 (done, 67 tests passing against Neon):** cart + orders (no auto-added items, explicit payment method, no silent COD conversion),
  order price snapshot + status timeline, expected_total check, stock locking, wrong/fake-item returns with trust-score penalty, Alembic migrations.
- **Phase 3:** AI search & assistant — embeddings in pgvector, RAG over products + reviews,
  LangChain agent, multilingual + voice.
- **Phase 4:** reviews (verified only, summariser, fake-review detection), seller trust score.
- **Phase 5:** grievance tracker with status timeline + AI triage; DSA features; Redis rate limiter;
  three portal UIs.
