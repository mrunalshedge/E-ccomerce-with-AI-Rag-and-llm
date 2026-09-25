from fastapi import APIRouter

from app.api.routes import auth, products, sellers

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sellers.router)
api_router.include_router(products.router)
