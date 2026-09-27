"""Seed demo sellers and products for local development and demos.

Idempotent: existing sellers (by email) and products (by seller + title) are skipped.
Usage (from the project root):  npm run seed
All demo accounts use the password printed at the end. Never run this against production.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models.product import Product
from app.models.user import UserRole
from app.schemas.product import ProductCreate
from app.schemas.seller import SellerCreate
from app.schemas.user import UserCreate
from app.services import product_service, seller_service, user_service
from app.scripts.seed_grievances import ADMIN_EMAIL, seed_admin, seed_grievances
from app.scripts.seed_reviews import seed_reviews
from app.services.embedding_service import backfill_embeddings

DEMO_PASSWORD = "DemoPass123!"


def unsplash(photo_id: str) -> str:
    """Demo photos are hot-linked from Unsplash (free to use under the Unsplash License)."""
    return f"https://images.unsplash.com/{photo_id}?w=800&q=80&auto=format&fit=crop"

# (seller account email, seller profile, products)
CATALOGUE: list[tuple[str, dict, list[dict]]] = [
    (
        "demo.seller@shopsense.dev",
        {
            "business_name": "Pune Handlooms Pvt Ltd",
            "contact_email": "support@punehandlooms.in",
            "phone": "+919876543210",
            "address": "12 FC Road, Shivajinagar, Pune, Maharashtra 411005",
            "gstin": "27ABCDE1234F1Z5",
            "grievance_officer_name": "R. Kulkarni",
            "grievance_officer_email": "grievance@punehandlooms.in",
        },
        [
            {"title": "Handwoven Cotton Kurta", "image_url": unsplash("photo-1727835523545-70ee992b5763"), "description": "Breathable handwoven cotton kurta from Pune weavers. Soft, airy and perfect for Indian summers.", "category": "clothing", "base_price": "1000", "delivery_fee": "40", "platform_fee": "10", "gst_percent": "18", "stock": 25},
            {"title": "Block-print Cotton Dupatta", "image_url": unsplash("photo-1759840279499-f9de9764b2cf"), "description": "Hand block-printed pure cotton dupatta with natural dyes. Lightweight and colourfast.", "category": "clothing", "base_price": "449", "delivery_fee": "0", "platform_fee": "5", "gst_percent": "5", "stock": 40},
            {"title": "Khadi Nehru Jacket", "image_url": unsplash("photo-1774438029647-d6484285165e"), "description": "Classic khadi Nehru jacket with a mandarin collar. Hand-spun, hand-woven fabric for festive and office wear.", "category": "clothing", "base_price": "1599", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 12},
        ],
    ),
    (
        "kanchi.silks@shopsense.dev",
        {
            "business_name": "Kanchi Silks & Crafts",
            "contact_email": "care@kanchisilks.in",
            "phone": "+919840012345",
            "address": "45 Gandhi Road, Kanchipuram, Tamil Nadu 631501",
            "gstin": "33AAKCK4521M1Z8",
            "grievance_officer_name": "S. Lakshmi",
            "grievance_officer_email": "grievance@kanchisilks.in",
        },
        [
            {"title": "Kanjivaram Pure Silk Saree", "image_url": unsplash("photo-1641699862936-be9f49b1c38d"), "description": "Authentic Kanjivaram silk saree with a zari border, woven by Kanchipuram artisans. Silk Mark certified.", "category": "clothing", "base_price": "8999", "delivery_fee": "0", "platform_fee": "25", "gst_percent": "5", "stock": 4},
            {"title": "Brass Diya Set of 4", "image_url": unsplash("photo-1761295908075-065ac2db0f5c"), "description": "Handcrafted solid brass diyas for pooja and festive decor. Polished finish, easy to clean.", "category": "home", "base_price": "699", "delivery_fee": "49", "platform_fee": "5", "gst_percent": "12", "stock": 30},
        ],
    ),
    (
        "nashik.organics@shopsense.dev",
        {
            "business_name": "Nashik Organics",
            "contact_email": "hello@nashikorganics.in",
            "phone": "+919822098220",
            "address": "Plot 7, MIDC Ambad, Nashik, Maharashtra 422010",
            "gstin": "27AAHFN7788Q1Z2",
            "grievance_officer_name": "P. Deshmukh",
            "grievance_officer_email": "grievance@nashikorganics.in",
        },
        [
            {"title": "Cold-pressed Groundnut Oil 1L", "image_url": unsplash("photo-1621958180509-74e9a29b3758"), "description": "Wood-pressed (lakdi ghani) groundnut oil from Maharashtra farms. No chemicals, no preservatives.", "category": "grocery", "base_price": "329", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 60, "is_returnable": False},
            {"title": "Organic Jaggery Powder 1kg", "image_url": unsplash("photo-1775817590687-f1da5d70d9ad"), "description": "Chemical-free organic jaggery powder. A healthier alternative to refined sugar for chai and sweets.", "category": "grocery", "base_price": "159", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 80, "is_returnable": False},
            {"title": "Alphonso Mango Pulp 850g", "image_url": unsplash("photo-1673010960635-d0d1ad81b90a"), "description": "Sweet Ratnagiri Alphonso mango pulp, ready for aamras, lassi and desserts.", "category": "grocery", "base_price": "249", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "12", "stock": 45, "is_returnable": False},
        ],
    ),
    (
        "techbazaar@shopsense.dev",
        {
            "business_name": "TechBazaar Electronics",
            "contact_email": "support@techbazaar.in",
            "phone": "+918045671234",
            "address": "3rd Floor, SP Road, Bengaluru, Karnataka 560002",
            "gstin": "29AADCT9087P1Z4",
            "grievance_officer_name": "A. Rao",
            "grievance_officer_email": "grievance@techbazaar.in",
        },
        [
            {"title": "Wireless Earbuds with ENC", "image_url": unsplash("photo-1606220588913-b3aacb4d2f46"), "description": "Bluetooth 5.3 earbuds with environmental noise cancellation, 40-hour battery and fast charging.", "category": "electronics", "base_price": "1299", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 50},
            {"title": "20000mAh Power Bank", "image_url": unsplash("photo-1566554738544-d962991c3fee"), "description": "Slim 20000mAh power bank with 22.5W fast charging and USB-C input/output. BIS certified.", "category": "electronics", "base_price": "1499", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 35},
            {"title": "Smart LED Bulb 9W", "image_url": unsplash("photo-1590845947698-8924d7409b56"), "description": "Wi-Fi smart bulb with 16 million colours. Works with Alexa and Google Assistant; control from your phone.", "category": "electronics", "base_price": "399", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 100},
        ],
    ),
    (
        "jaipur.decor@shopsense.dev",
        {
            "business_name": "Jaipur Home Decor",
            "contact_email": "orders@jaipurdecor.in",
            "phone": "+919414012345",
            "address": "22 Johari Bazaar, Jaipur, Rajasthan 302003",
            "gstin": "08AAJFJ3344K1Z6",
            "grievance_officer_name": "M. Sharma",
            "grievance_officer_email": "grievance@jaipurdecor.in",
        },
        [
            {"title": "Blue Pottery Coffee Mugs (Set of 2)", "image_url": unsplash("photo-1755622832288-99689d254b48"), "description": "Hand-painted Jaipur blue pottery mugs. Microwave-safe glaze, 300 ml each.", "category": "home", "base_price": "799", "delivery_fee": "60", "platform_fee": "8", "gst_percent": "12", "stock": 20},
            {"title": "Hand Block Printed Double Bedsheet", "image_url": unsplash("photo-1693990155103-b349eba41fb5"), "description": "100% cotton Sanganeri block-print double bedsheet with two pillow covers. 144 thread count.", "category": "home", "base_price": "1199", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "5", "stock": 15},
            {"title": "Wings of Fire (Paperback)", "image_url": unsplash("photo-1591951425600-d09958978584"), "description": "The autobiography of Dr. A.P.J. Abdul Kalam. An inspiring read for students and professionals.", "category": "books", "base_price": "299", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 70},
        ],
    ),
]


async def seed() -> None:
    created_sellers = created_products = updated_images = 0
    async with SessionLocal() as db:
        for email, profile, products in CATALOGUE:
            user = await user_service.get_user_by_email(db, email)
            if user is None:
                user = await user_service.create_user(
                    db,
                    UserCreate(name=profile["business_name"], email=email, password=DEMO_PASSWORD, role=UserRole.SELLER),
                )
            seller = await seller_service.get_seller_by_user_id(db, user.id)
            if seller is None:
                seller = await seller_service.create_seller_profile(db, user, SellerCreate(**profile))
                created_sellers += 1

            existing = {
                p.title: p for p in (await db.execute(select(Product).where(Product.seller_id == seller.id))).scalars()
            }
            for item in products:
                if item["title"] in existing:
                    product = existing[item["title"]]
                    if product.image_url is None and item.get("image_url"):
                        product.image_url = item["image_url"]
                        updated_images += 1
                    continue
                data = ProductCreate(**{**item, "base_price": Decimal(item["base_price"])})
                await product_service.create_product(db, seller, data)
                created_products += 1
        await db.commit()
        embedded = await backfill_embeddings(db)
        reviews, flagged = await seed_reviews(db, DEMO_PASSWORD)
        admin_created = await seed_admin(db, DEMO_PASSWORD)
        complaints = await seed_grievances(db)
    await engine.dispose()

    print(f"Embedded {embedded} products for semantic search.")

    print(f"Added photos to {updated_images} existing products.")
    print(f"Seeded {created_sellers} new sellers and {created_products} new products.")
    print(f"Demo seller logins: {', '.join(email for email, _, _ in CATALOGUE)}")
    print(f"Seeded {reviews} verified reviews ({flagged} flagged as possibly fake for the admin queue).")
    print(f"Seeded {complaints} demo complaints.")
    print(f"Admin login: {ADMIN_EMAIL}" + (" (created)" if admin_created else ""))
    print(f"Password for all demo accounts: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
