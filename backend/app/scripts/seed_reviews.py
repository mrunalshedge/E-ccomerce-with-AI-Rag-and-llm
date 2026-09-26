"""Demo verified reviews: real (seeded) delivered orders + reviews spread over the past weeks,
including two planted fakes so the detection and moderation queue have something to show.

Idempotent: a buyer who already reviewed a product is skipped. Called from ``seed_demo``.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import utcnow
from app.models.order import Order, OrderEvent, OrderItem, OrderStatus, PaymentMethod, PaymentStatus
from app.models.product import Product
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import ReviewCreate
from app.schemas.user import UserCreate
from app.services import review_service, user_service
from app.services.pricing import line_total, summarise_lines
from app.services.product_service import price_of

BUYERS = [
    ("Priya Sharma", "priya.sharma@shopsense.dev"),
    ("Rahul Verma", "rahul.verma@shopsense.dev"),
    ("Sneha Patil", "sneha.patil@shopsense.dev"),
    ("Amit Joshi", "amit.joshi@shopsense.dev"),
    ("Kavya Iyer", "kavya.iyer@shopsense.dev"),
    ("Rohan Deshmukh", "rohan.deshmukh@shopsense.dev"),
    ("Farhan Khan", "farhan.khan@shopsense.dev"),
]

# product title -> [(buyer index, rating, title, body, days ago)]
REVIEWS: dict[str, list[tuple[int, int, str | None, str, float]]] = {
    "Handwoven Cotton Kurta": [
        (0, 5, "Perfect for Pune summers", "Very breathable cotton, I wore it all day in 38°C without feeling sticky. Stitching is neat.", 21),
        (1, 4, "Good fit", "Fits true to size. Colour is a shade lighter than the photo but still looks nice.", 17),
        (2, 5, None, "कपड़ा बहुत मुलायम है और धुलने के बाद भी सिकुड़ा नहीं। दाम के हिसाब से बढ़िया।", 12),
        (3, 3, "Okay quality", "Comfortable, but one button was loose on arrival. Had to stitch it myself.", 9),
        (4, 4, None, "Kapda accha hai, garmi mein aaram deta hai. Delivery thodi late thi par packing sahi thi.", 4),
    ],
    "Wireless Earbuds with ENC": [
        (0, 4, "Great battery", "Battery easily lasts a week of commuting. Call quality is clear thanks to ENC.", 25),
        (2, 5, None, "Bass is punchy for this price and pairing with my phone was instant.", 15),
        (3, 2, "Left bud disconnects", "The left earbud keeps disconnecting every few minutes. Support asked me to reset, didn't help.", 10),
        (5, 4, None, "Sound acchi hai, gym mein use karta hoon. Case thoda bada hai pocket ke liye.", 6),
    ],
    "Organic Jaggery Powder 1kg": [
        (1, 5, "Tastes like home", "Authentic taste, no chemical smell. Great in chai and for making laddoos.", 19),
        (4, 5, None, "चहासाठी उत्तम. गोडवा नैसर्गिक आहे आणि पॅकिंग व्यवस्थित होते.", 11),
        (5, 4, None, "Good quality jaggery, slightly lumpy but breaks easily.", 3),
    ],
    "Kanjivaram Pure Silk Saree": [
        (0, 5, "Worth every rupee", "Beautiful zari work and the Silk Mark tag was included. Wore it to my sister's wedding.", 30),
        (4, 4, None, "Rich colour and heavy silk. Blouse piece was slightly shorter than expected.", 16),
        (2, 5, None, "असली कांजीवरम सिल्क है, ज़री की चमक शानदार है। पैकिंग भी बहुत अच्छी थी।", 8),
    ],
    "Blue Pottery Coffee Mugs (Set of 2)": [
        (1, 4, None, "Lovely hand-painted design, looks even better in person. Handle is a bit small.", 14),
        (3, 3, None, "One mug had a tiny chip near the base. Seller replaced it quickly though.", 9),
        (6, 5, "Great gift", "Gifted these to my parents, they loved the Jaipur blue pottery look.", 2),
    ],
    "20000mAh Power Bank": [
        (1, 4, None, "Charges my phone about four times. Gets slightly warm with fast charging.", 13),
        (3, 4, None, "Solid build and the USB-C port works with my laptop too.", 7),
        # Planted fakes: identical text from two accounts minutes apart (the 2nd gets flagged).
        (5, 5, None, "Best product ever!!! 100% original must buy, super fast charging, five stars", 0.03),
        (6, 5, None, "Best product ever!!! 100% original must buy, super fast charging, five stars", 0.02),
    ],
    "Brass Diya Set of 4": [
        # Planted spam: short 5★ review pushing an outside link (flagged).
        (2, 5, None, "cheap at www.deals4u.in", 0.5),
    ],
}


async def _buyer(db: AsyncSession, name: str, email: str, password: str) -> User:
    user = await user_service.get_user_by_email(db, email)
    if user is None:
        user = await user_service.create_user(
            db, UserCreate(name=name, email=email, password=password, role=UserRole.CUSTOMER)
        )
    return user


async def _delivered_order(db: AsyncSession, user: User, product: Product, delivered_days_ago: float) -> None:
    """A past, delivered, prepaid order for one unit (the demo stock isn't touched)."""
    unit = price_of(product)
    totals = summarise_lines([(unit, 1)])
    delivered_at = utcnow() - timedelta(days=delivered_days_ago)
    placed_at = delivered_at - timedelta(days=3)
    order = Order(
        user_id=user.id,
        seller_id=product.seller_id,
        status=OrderStatus.DELIVERED,
        payment_method=PaymentMethod.UPI,
        payment_status=PaymentStatus.PAID,
        shipping_address="Demo address, Shivajinagar, Pune, Maharashtra 411005",
        total_base=totals.total_base,
        total_delivery=totals.total_delivery,
        total_platform_fee=totals.total_platform_fee,
        total_gst=totals.total_gst,
        grand_total=totals.grand_total,
        created_at=placed_at,
        delivered_at=delivered_at,
    )
    order.items = [
        OrderItem(
            product_id=product.id,
            title=product.title,
            quantity=1,
            unit_base_price=unit.base_price,
            unit_delivery_fee=unit.delivery_fee,
            unit_platform_fee=unit.platform_fee,
            gst_percent=unit.gst_percent,
            unit_gst_amount=unit.gst_amount,
            unit_final_price=unit.final_price,
            line_total=line_total(unit, 1),
            is_returnable=product.is_returnable,
        )
    ]
    order.events = [
        OrderEvent(status=OrderStatus.PLACED, note="Order placed (demo).", created_at=placed_at),
        OrderEvent(status=OrderStatus.SHIPPED, note="Shipped by seller.", created_at=placed_at + timedelta(days=1)),
        OrderEvent(status=OrderStatus.DELIVERED, note="Delivered.", created_at=delivered_at),
    ]
    db.add(order)
    await db.commit()


async def seed_reviews(db: AsyncSession, password: str) -> tuple[int, int]:
    """Returns (reviews created, of which flagged)."""
    buyers = [await _buyer(db, name, email, password) for name, email in BUYERS]
    created = flagged = 0
    for title, entries in REVIEWS.items():
        product = (await db.execute(select(Product).where(Product.title == title))).scalar_one_or_none()
        if product is None:
            continue
        # Oldest first, so duplicate/burst detection sees reviews in the order they were written.
        for buyer_index, rating, review_title, body, days_ago in sorted(entries, key=lambda e: -e[4]):
            buyer = buyers[buyer_index]
            already = await db.execute(
                select(Review.id).where(Review.user_id == buyer.id, Review.product_id == product.id)
            )
            if already.first() is not None:
                continue
            await _delivered_order(db, buyer, product, delivered_days_ago=days_ago + 1)
            review = await review_service.create_review(
                db,
                buyer,
                product.id,
                ReviewCreate(rating=rating, title=review_title, body=body),
                now=utcnow() - timedelta(days=days_ago),
            )
            created += 1
            flagged += review.status.value == "flagged"
    return created, flagged
