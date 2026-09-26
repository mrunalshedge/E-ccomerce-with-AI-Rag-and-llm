from fastapi import APIRouter

from app.api.routes import admin, assistant, auth, cart, orders, products, returns, search, sellers

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sellers.router)
api_router.include_router(products.router)
api_router.include_router(search.router)
api_router.include_router(assistant.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(returns.router)
api_router.include_router(admin.router)
