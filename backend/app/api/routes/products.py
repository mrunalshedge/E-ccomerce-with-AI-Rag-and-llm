from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentSeller, DbSession
from app.schemas.product import ProductCreate, ProductListResponse, ProductRead
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    db: DbSession,
    category: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductListResponse:
    """Public catalogue. Every item carries its all-inclusive price breakdown and seller card."""
    products, total = await product_service.list_products(
        db, category=category, page=page, page_size=page_size
    )
    return ProductListResponse(
        items=[product_service.to_product_read(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: DbSession) -> ProductRead:
    product = await product_service.get_product(db, product_id)
    return product_service.to_product_read(product)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, seller: CurrentSeller, db: DbSession) -> ProductRead:
    """List a new product. Requires the seller role and a seller profile."""
    product = await product_service.create_product(db, seller, data)
    return product_service.to_product_read(product)
