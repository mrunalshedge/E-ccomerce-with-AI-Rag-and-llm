"""Seed demo sellers, products, buyers, reviews, complaints and an admin.

Idempotent: existing sellers (by email) and products (by seller + title) are skipped.
Usage (from the project root):  npm run seed

Passwords: demo *customers* share the public DEMO_PASSWORD (it's shown on the login page).
Demo *seller and admin* accounts use SEED_STAFF_PASSWORD from backend/.env, which is never
published; re-running the seed rotates existing staff accounts to it.
"""

import asyncio
from decimal import Decimal

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal, engine
from app.models.product import Product, ProductVariant
from app.models.user import UserRole
from app.schemas.product import ProductCreate
from app.schemas.seller import SellerCreate
from app.schemas.user import UserCreate
from app.services import product_service, seller_service, user_service
from app.scripts.catalogue_more import EXTRA_PRODUCTS, EXTRA_SIZES, NEW_SELLERS
from app.scripts.seed_grievances import ADMIN_EMAIL, seed_admin, seed_grievances
from app.scripts.seed_reviews import seed_reviews
from app.services.embedding_service import backfill_embeddings

DEMO_PASSWORD = "DemoPass123!"  # public: demo customers only


def unsplash(photo_id: str) -> str:
    """Demo photos are hot-linked from Unsplash (free to use under the Unsplash License)."""
    return f"https://images.unsplash.com/{photo_id}?w=800&q=80&auto=format&fit=crop"


KHRONOS = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models"


def khronos_3d(name: str, credit: str) -> dict[str, str]:
    """Openly licensed demo 3D models (Khronos glTF Sample Assets), in real-world metres so AR shows
    them at true size. The product photo is the official render of the same model."""
    return {
        "model_url": f"{KHRONOS}/{name}/glTF-Binary/{name}.glb",
        "image_url": f"{KHRONOS}/{name}/screenshot/screenshot.jpg",
        "model_credit": f"3D model: {credit} (Khronos glTF Sample Assets)",
    }

# (seller account email, seller profile, products)
# Clothing sizes: per-size stock (sums to the catalogue stock) and garment measurements in cm.
SIZES: dict[str, dict] = {
    "Handwoven Cotton Kurta": {
        "sizes": [{"size": "S", "stock": 5}, {"size": "M", "stock": 8}, {"size": "L", "stock": 7}, {"size": "XL", "stock": 4}, {"size": "XXL", "stock": 1}],
        "size_chart": [
            {"size": "S", "chest": 96, "waist": 90, "length": 104, "shoulder": 42, "sleeve": 58},
            {"size": "M", "chest": 102, "waist": 96, "length": 106, "shoulder": 44, "sleeve": 59},
            {"size": "L", "chest": 108, "waist": 102, "length": 108, "shoulder": 46, "sleeve": 60},
            {"size": "XL", "chest": 114, "waist": 108, "length": 110, "shoulder": 48, "sleeve": 61},
            {"size": "XXL", "chest": 120, "waist": 114, "length": 112, "shoulder": 50, "sleeve": 62},
        ],
    },
    "Khadi Nehru Jacket": {
        "sizes": [{"size": "S", "stock": 3}, {"size": "M", "stock": 4}, {"size": "L", "stock": 3}, {"size": "XL", "stock": 2}],
        "size_chart": [
            {"size": "S", "chest": 98, "waist": 90, "length": 66, "shoulder": 41},
            {"size": "M", "chest": 104, "waist": 96, "length": 68, "shoulder": 43},
            {"size": "L", "chest": 110, "waist": 102, "length": 70, "shoulder": 45},
            {"size": "XL", "chest": 116, "waist": 108, "length": 72, "shoulder": 47},
        ],
    },
}


def add_sizes(product: Product) -> bool:
    """Give an already-seeded clothing product its sizes (older seeds predate sizes)."""
    spec = SIZES.get(product.title)
    if spec is None or product.variants:
        return False
    product.variants = [ProductVariant(size=s["size"], stock=s["stock"], position=i) for i, s in enumerate(spec["sizes"])]
    product.stock = sum(s["stock"] for s in spec["sizes"])
    product.size_chart = spec["size_chart"]
    return True


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
            {"title": "Minimalist Steel Watch 36 mm", "image_url": unsplash("photo-1616928231359-fc8b7e244c3b"), "description": "Slim 36 mm stainless steel case, clean white dial and a soft black leather strap. Japanese quartz movement, 3 ATM splash resistant. Try it on your wrist with your camera.", "category": "accessories", "base_price": "1799", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 18, "try_on": {"kind": "wrist", "case_mm": 36, "dial_color": "#f4f4f2", "case_color": "#c7cad0", "strap_color": "#16181b"}},
            {"title": "Field Watch with Leather Strap 42 mm", "image_url": unsplash("photo-1580139706250-bf6c93772b48"), "description": "Rugged 42 mm brushed-steel field watch with bold numerals, date window and a tan leather strap. 5 ATM water resistant. Try it on your wrist with your camera.", "category": "accessories", "base_price": "2299", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 10, "try_on": {"kind": "wrist", "case_mm": 42, "dial_color": "#f3f1ec", "case_color": "#b8b2a6", "strap_color": "#8b5a2b"}},
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
            {"title": "Iridescent Glass Table Lamp", **khronos_3d("IridescenceLamp", "© 2022 Wayfair LLC, CC BY 4.0"), "description": "Mouth-blown glass table lamp with an iridescent finish on a brushed-metal base. About 30 cm wide and 48 cm tall: see it on your own table in 3D before you buy.", "category": "home", "base_price": "2499", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 8},
            {"title": "Velvet Accent Chair", **khronos_3d("SheenChair", "Wayfair LLC, CC0 (public domain)"), "description": "Compact velvet slipper chair with a solid wood frame. About 83 cm wide and 69 cm tall: place it in your room in 3D to check the fit.", "category": "home", "base_price": "7999", "delivery_fee": "299", "platform_fee": "25", "gst_percent": "18", "stock": 5},
            {"title": "Velvet 3-Seater Sofa", **khronos_3d("GlamVelvetSofa", "© 2021 Wayfair LLC, CC BY 4.0"), "description": "Plush velvet three-seater sofa with slim arms. About 2.2 m wide and 1 m deep: view it at true size in your living room before ordering.", "category": "home", "base_price": "24999", "delivery_fee": "999", "platform_fee": "49", "gst_percent": "18", "stock": 3},
            {"title": "Wings of Fire (Paperback)", "image_url": unsplash("photo-1591951425600-d09958978584"), "description": "The autobiography of Dr. A.P.J. Abdul Kalam. An inspiring read for students and professionals.", "category": "books", "base_price": "299", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 70},
        ],
    ),
]


# The wider catalogue (≈100 more products and 6 more sellers) lives in catalogue_more.py.
CATALOGUE = [(email, profile, products + EXTRA_PRODUCTS.get(email, [])) for email, profile, products in CATALOGUE]
CATALOGUE += NEW_SELLERS
SIZES.update(EXTRA_SIZES)


async def rotate_passwords(db: AsyncSession, emails: list[str], password: str) -> int:
    """Make sure each existing account uses ``password``; returns how many were changed."""
    changed = 0
    for email in emails:
        user = await user_service.get_user_by_email(db, email)
        if user and not await to_thread.run_sync(verify_password, password, user.hashed_password):
            user.hashed_password = await to_thread.run_sync(hash_password, password)
            changed += 1
    await db.commit()
    return changed


async def seed() -> None:
    secret = get_settings().seed_staff_password
    if secret is None or len(secret.get_secret_value()) < 12:
        raise SystemExit(
            "Set SEED_STAFF_PASSWORD (12+ characters) in backend/.env: the secret password for the demo "
            "seller and admin accounts. It is never shown on the site or committed."
        )
    staff_password = secret.get_secret_value()
    created_sellers = created_products = updated_images = sized = 0
    async with SessionLocal() as db:
        for email, profile, products in CATALOGUE:
            user = await user_service.get_user_by_email(db, email)
            if user is None:
                user = await user_service.create_user(
                    db,
                    UserCreate(name=profile["business_name"], email=email, password=staff_password, role=UserRole.SELLER),
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
                    sized += add_sizes(product)
                    continue
                data = ProductCreate(**{**item, **SIZES.get(item["title"], {}), "base_price": Decimal(item["base_price"])})
                await product_service.create_product(db, seller, data)
                created_products += 1
        await db.commit()
        embedded = await backfill_embeddings(db)
        reviews, flagged = await seed_reviews(db, DEMO_PASSWORD)
        admin_created = await seed_admin(db, staff_password)
        staff_emails = [email for email, _, _ in CATALOGUE] + [ADMIN_EMAIL]
        rotated = await rotate_passwords(db, staff_emails, staff_password)
        complaints = await seed_grievances(db)
    await engine.dispose()

    print(f"Embedded {embedded} products for semantic search.")

    print(f"Added photos to {updated_images} existing products and sizes to {sized}.")
    print(f"Seeded {created_sellers} new sellers and {created_products} new products.")
    print(f"Demo seller logins: {', '.join(email for email, _, _ in CATALOGUE)}")
    print(f"Seeded {reviews} verified reviews ({flagged} flagged as possibly fake for the admin queue).")
    print(f"Seeded {complaints} demo complaints.")
    print(f"Admin login: {ADMIN_EMAIL}" + (" (created)" if admin_created else ""))
    print(f"Demo customer password (public): {DEMO_PASSWORD}")
    print(f"Seller/admin accounts use SEED_STAFF_PASSWORD from backend/.env ({rotated} rotated to it).")


if __name__ == "__main__":
    asyncio.run(seed())
