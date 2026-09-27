from fastapi import APIRouter

from app.api.routes import admin, assistant, auth, cart, discovery, grievances, orders, pricing, products, returns, reviews, search, sellers

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sellers.router)
api_router.include_router(products.router)
api_router.include_router(reviews.router)
api_router.include_router(discovery.router)  # before search: /search/suggest
api_router.include_router(search.router)
api_router.include_router(assistant.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(returns.router)
api_router.include_router(grievances.router)
api_router.include_router(admin.router)
api_router.include_router(pricing.router)
