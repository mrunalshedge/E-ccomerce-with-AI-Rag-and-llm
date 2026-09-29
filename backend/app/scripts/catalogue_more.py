"""Extra demo catalogue (107 products, 6 more sellers) so the store feels real.

Photos are hot-linked from Unsplash (free to use under the Unsplash License); each was checked to
match its product. Sellers are fictional. Merged into ``seed_demo.CATALOGUE`` and ``seed_demo.SIZES``.
"""

from typing import Any


def _with_photo(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``image`` (an Unsplash photo id) becomes the full ``image_url``."""
    return [
        {**{k: v for k, v in item.items() if k != "image"}, "image_url": f"https://images.unsplash.com/{item['image']}?w=800&q=80&auto=format&fit=crop"}
        for item in items
    ]


# Extra products for sellers that already exist in seed_demo.CATALOGUE (by account email).
EXTRA_PRODUCTS: dict[str, list[dict[str, Any]]] = {
    "demo.seller@shopsense.dev": _with_photo(
        [
            {"title": "Men's Linen Casual Shirt", "description": "Pure linen shirt with roll-up sleeves, a relaxed fit and coconut-shell buttons. Breathes well in humid weather.", "category": "clothing", "base_price": "1199", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 30, "image": "photo-1740711152088-88a009e877bb"},
            {"title": "Organic Cotton Crew T-Shirt", "description": "Soft 180 GSM organic cotton tee, pre-shrunk, with a ribbed crew neck. Dyed with low-impact dyes.", "category": "clothing", "base_price": "499", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "5", "stock": 60, "image": "photo-1581655353564-df123a1eb820"},
            {"title": "Women's Chikankari Kurti", "description": "Lucknowi chikankari hand embroidery on soft cotton. Straight cut, three-quarter sleeves, knee length.", "category": "clothing", "base_price": "1499", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 24, "image": "photo-1745313452052-0e4e341f326c"},
            {"title": "Stretch Denim Jeans (Slim)", "description": "Mid-rise slim-fit jeans in 2% stretch denim for easy movement. Five pockets, zip fly.", "category": "clothing", "base_price": "1599", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 28, "image": "photo-1637069585336-827b298fe84a"},
            {"title": "Hooded Cotton Sweatshirt", "description": "Brushed fleece-lined hoodie with a kangaroo pocket and drawstring hood. Warm without being heavy.", "category": "clothing", "base_price": "1299", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 20, "image": "photo-1556821840-3a63f95609a7"},
            {"title": "Cotton Pyjama Set", "description": "Two-piece cotton night suit with a button-down top and elastic-waist pyjama. Soft after every wash.", "category": "clothing", "base_price": "899", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "5", "stock": 25, "image": "photo-1766056278842-b754f1e093c0"},
            {"title": "Khadi Cotton Dhoti", "description": "Handwoven khadi dhoti with a thin zari border, 4 metres. Ready for pooja, weddings and festivals.", "category": "clothing", "base_price": "699", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "5", "stock": 35, "image": "photo-1706192048397-71ce1148d24f"},
            {"title": "Woollen Kashmiri Shawl", "description": "Soft woollen shawl with traditional paisley embroidery, 200 × 100 cm. Warm and light for winter evenings.", "category": "clothing", "base_price": "2199", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 12, "image": "photo-1784382358933-aade4a2b9f1b"},
            {"title": "Men's Cotton Formal Trousers", "description": "Flat-front cotton-blend trousers with a crease-resistant finish. Ideal for office wear.", "category": "clothing", "base_price": "1099", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 22, "image": "photo-1609259886986-a642e7e1dbf9"},
        ]
    ),
    "kanchi.silks@shopsense.dev": _with_photo(
        [
            {"title": "Banarasi Silk Dupatta", "description": "Woven Banarasi silk dupatta with zari motifs and tassels. Pairs with plain kurtas for festive looks.", "category": "clothing", "base_price": "1799", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 14, "image": "photo-1717585679395-bbe39b5fb6bc"},
            {"title": "Cotton Printed Saree", "description": "Everyday soft cotton saree with a block-printed border and running blouse piece. 5.5 m + 0.8 m.", "category": "clothing", "base_price": "1299", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "5", "stock": 18, "image": "photo-1610030468706-9a6dbad49b0a"},
            {"title": "Paithani Silk Saree", "description": "Handwoven Yeola Paithani with peacock pallu and pure zari border. A Maharashtrian heirloom.", "category": "clothing", "base_price": "12999", "delivery_fee": "0", "platform_fee": "49", "gst_percent": "5", "stock": 3, "image": "photo-1727430228383-aa1fb59db8bf"},
            {"title": "Girls' Silk Pavadai Set", "description": "Traditional South Indian pattu pavadai with a contrast border, for festivals and functions.", "category": "clothing", "base_price": "1899", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 10, "image": "photo-1562438995-20c8bc11d4a9"},
            {"title": "Men's Silk Kurta", "description": "Art-silk kurta with a mandarin collar and subtle self-weave. Comfortable for long ceremonies.", "category": "clothing", "base_price": "1999", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 16, "image": "photo-1727835523545-70ee992b5763"},
        ]
    ),
    "techbazaar@shopsense.dev": _with_photo(
        [
            {"title": "Polarised Aviator Sunglasses", "description": "UV400 polarised lenses in a lightweight metal frame. Comes with a hard case.", "category": "accessories", "base_price": "999", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 40, "image": "photo-1567473810954-507d59716c25"},
            {"title": "Bluetooth Neckband Earphones", "description": "Magnetic earbuds, 30-hour battery, IPX5 sweat resistance and fast charging.", "category": "electronics", "base_price": "999", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 45, "image": "photo-1632247541401-3d4a8d516595"},
            {"title": "Portable Bluetooth Speaker 10 W", "description": "Waterproof (IPX7) speaker with deep bass and 12-hour playback.", "category": "electronics", "base_price": "1799", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 30, "image": "photo-1582978571763-2d039e56f0c3"},
            {"title": "USB-C Fast Charger 33 W", "description": "GaN charger with USB-C PD and QC 3.0. Charges most phones to 50% in 30 minutes. BIS certified.", "category": "electronics", "base_price": "899", "delivery_fee": "0", "platform_fee": "8", "gst_percent": "18", "stock": 60, "image": "photo-1586254116951-5263e2cdb44c"},
            {"title": "Wireless Mouse", "description": "Silent-click 2.4 GHz mouse with adjustable DPI and a 12-month battery life.", "category": "electronics", "base_price": "499", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 70, "image": "photo-1527864550417-7fd91fc51a46"},
            {"title": "Mechanical Keyboard (Blue Switches)", "description": "Tenkeyless mechanical keyboard with RGB backlight and detachable USB-C cable.", "category": "electronics", "base_price": "2499", "delivery_fee": "0", "platform_fee": "20", "gst_percent": "18", "stock": 18, "image": "photo-1618384887929-16ec33fab9ef"},
            {"title": "Full HD Webcam with Mic", "description": "1080p webcam with auto light correction and dual noise-reducing mics. Plug and play.", "category": "electronics", "base_price": "1499", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 25, "image": "photo-1588196749597-9ff075ee6b5b"},
            {"title": "Smart Fitness Band", "description": "Heart-rate, SpO2 and sleep tracking band with a 1.1\" AMOLED screen and 14-day battery.", "category": "electronics", "base_price": "1999", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 35, "image": "photo-1576243345690-4e4b79b63288"},
            {"title": "Laptop Stand (Aluminium)", "description": "Foldable aluminium stand with 6 height levels. Raises the screen to eye level.", "category": "electronics", "base_price": "1199", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 28, "image": "photo-1623251606108-512c7c4a3507"},
            {"title": "32 GB USB 3.0 Pen Drive", "description": "Metal-body USB 3.0 flash drive with read speeds up to 100 MB/s.", "category": "electronics", "base_price": "449", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 80, "image": "photo-1551818014-7c8ace9c1b5c"},
            {"title": "Over-ear Wireless Headphones", "description": "Foldable headphones with 40 mm drivers, 40-hour battery and a built-in mic.", "category": "electronics", "base_price": "2799", "delivery_fee": "0", "platform_fee": "20", "gst_percent": "18", "stock": 22, "image": "photo-1505740420928-5e560c06d30e"},
            {"title": "LED Desk Lamp with USB Port", "description": "Eye-care LED lamp with 3 colour modes, stepless dimming and a USB charging port.", "category": "electronics", "base_price": "1099", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 26, "image": "photo-1519219788971-8d9797e0928e"},
            {"title": "Phone Tripod with Bluetooth Remote", "description": "Extendable 1.5 m aluminium tripod with a phone clamp and Bluetooth shutter remote. Great for video calls and reels.", "category": "electronics", "base_price": "899", "delivery_fee": "40", "platform_fee": "8", "gst_percent": "18", "stock": 40, "image": "photo-1576299090369-9067e4adca28"},
        ]
    ),
    "jaipur.decor@shopsense.dev": _with_photo(
        [
            {"title": "Oxidised Silver Jhumka Earrings", "description": "Handcrafted oxidised jhumkas with ghungroo detailing. Nickel-free and lightweight.", "category": "accessories", "base_price": "349", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "3", "stock": 55, "image": "photo-1714733831162-0a6e849141be"},
            {"title": "Handwoven Cotton Dhurrie Rug", "description": "Flat-woven cotton dhurrie, 4 × 6 ft, in earthy stripes. Reversible and machine-washable.", "category": "home", "base_price": "1499", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 14, "image": "photo-1594040226829-7f251ab46d80"},
            {"title": "Macramé Wall Hanging", "description": "Hand-knotted cotton macramé on a driftwood rod, 60 cm wide. Boho accent for any wall.", "category": "home", "base_price": "699", "delivery_fee": "49", "platform_fee": "8", "gst_percent": "12", "stock": 20, "image": "photo-1619808799783-db68de98fbe0"},
            {"title": "Terracotta Planter Set of 3", "description": "Unglazed terracotta pots with drainage holes and saucers (4\", 6\", 8\").", "category": "home", "base_price": "599", "delivery_fee": "79", "platform_fee": "8", "gst_percent": "12", "stock": 25, "image": "photo-1468531390554-9f62f9767a87"},
            {"title": "Scented Soy Candle (Mogra)", "description": "Hand-poured soy wax candle with mogra fragrance, 40-hour burn in a reusable glass jar.", "category": "home", "base_price": "449", "delivery_fee": "49", "platform_fee": "5", "gst_percent": "18", "stock": 40, "image": "photo-1643122966676-29e8597257f7"},
            {"title": "Cotton Cushion Covers Set of 5", "description": "Hand block-printed cushion covers, 16 × 16 in, with hidden zips.", "category": "home", "base_price": "899", "delivery_fee": "0", "platform_fee": "8", "gst_percent": "12", "stock": 30, "image": "photo-1696774276390-6ce82111140f"},
            {"title": "Brass Ganesha Idol", "description": "Solid brass Ganesha, 6 inches, with a hand-polished antique finish. For home mandir or gifting.", "category": "home", "base_price": "1299", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 18, "image": "photo-1760857067352-5fb8d6e9245f"},
            {"title": "Wall Clock with Wooden Frame", "description": "Silent-sweep 12\" wall clock in a sheesham wood frame. Runs on one AA cell.", "category": "home", "base_price": "999", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 22, "image": "photo-1590587754330-6fc06e3a9bb7"},
            {"title": "Blackout Curtains (Pair)", "description": "Thermal blackout curtains, 7 ft, with eyelets. Block 90% light and keep rooms cool.", "category": "home", "base_price": "1399", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 16, "image": "photo-1509644851169-2acc08aa25b5"},
            {"title": "Cotton Bath Towel Set", "description": "Two 600 GSM combed-cotton bath towels. Highly absorbent and quick-drying.", "category": "home", "base_price": "799", "delivery_fee": "0", "platform_fee": "8", "gst_percent": "12", "stock": 35, "image": "photo-1523471826770-c437b4636fe6"},
            {"title": "Indoor Snake Plant with Pot", "description": "Low-maintenance air-purifying snake plant (Sansevieria) in a 6\" ceramic pot.", "category": "home", "base_price": "549", "delivery_fee": "79", "platform_fee": "5", "gst_percent": "5", "stock": 20, "is_returnable": False, "image": "photo-1687552212914-03a30c82053c"},
        ]
    ),
    "nashik.organics@shopsense.dev": _with_photo(
        [
            {"title": "Basmati Rice 5 kg", "description": "Aged long-grain basmati from the Himalayan foothills. Fluffy, fragrant, non-sticky.", "category": "grocery", "base_price": "749", "delivery_fee": "0", "platform_fee": "5", "gst_percent": "5", "stock": 50, "is_returnable": False, "image": "photo-1586201375761-83865001e31c"},
            {"title": "Toor Dal 1 kg", "description": "Unpolished, sortex-cleaned toor dal. Cooks soft and creamy.", "category": "grocery", "base_price": "179", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "0", "stock": 80, "is_returnable": False, "image": "photo-1701166175567-2f55dd40e662"},
            {"title": "Organic Turmeric Powder 200 g", "description": "High-curcumin Lakadong turmeric, stone-ground in small batches.", "category": "grocery", "base_price": "149", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 70, "is_returnable": False, "image": "photo-1702041295331-840d4d9aa7c9"},
            {"title": "Assam CTC Tea 500 g", "description": "Strong, malty Assam CTC tea for kadak masala chai.", "category": "grocery", "base_price": "299", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 60, "is_returnable": False, "image": "photo-1433891248364-3ce993ff0e92"},
            {"title": "A2 Desi Cow Ghee 500 ml", "description": "Bilona-method ghee from grass-fed Gir cows. Rich aroma, granular texture.", "category": "grocery", "base_price": "899", "delivery_fee": "30", "platform_fee": "8", "gst_percent": "12", "stock": 30, "is_returnable": False, "image": "photo-1573812461383-e5f8b759d12e"},
            {"title": "Raw Forest Honey 500 g", "description": "Unprocessed multi-flora honey from the Western Ghats. No added sugar.", "category": "grocery", "base_price": "399", "delivery_fee": "30", "platform_fee": "5", "gst_percent": "0", "stock": 40, "is_returnable": False, "image": "photo-1587049352851-8d4e89133924"},
            {"title": "Garam Masala 100 g", "description": "Hand-roasted whole spices ground fresh: cardamom, clove, cinnamon, pepper and more.", "category": "grocery", "base_price": "129", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 65, "is_returnable": False, "image": "photo-1716816211590-c15a328a5ff0"},
            {"title": "Roasted Makhana 200 g", "description": "Lightly roasted fox nuts with Himalayan pink salt. Crunchy, high-protein snack.", "category": "grocery", "base_price": "249", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 55, "is_returnable": False, "image": "photo-1710421576768-ff985fa63b60"},
            {"title": "California Almonds 500 g", "description": "Crunchy premium almonds, naturally sweet. Rich in vitamin E.", "category": "grocery", "base_price": "549", "delivery_fee": "30", "platform_fee": "5", "gst_percent": "12", "stock": 45, "is_returnable": False, "image": "photo-1608797178974-15b35a64ede9"},
            {"title": "Filter Coffee Powder 500 g", "description": "South Indian filter coffee blend: 80% coffee, 20% chicory. Strong decoction.", "category": "grocery", "base_price": "349", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 40, "is_returnable": False, "image": "photo-1447933601403-0c6688de566e"},
            {"title": "Whole Wheat Atta 5 kg", "description": "Chakki-ground whole wheat flour for soft rotis. No maida added.", "category": "grocery", "base_price": "299", "delivery_fee": "0", "platform_fee": "3", "gst_percent": "0", "stock": 60, "is_returnable": False, "image": "photo-1627485937980-221c88ac04f9"},
            {"title": "Kolhapuri Kanda Lasun Masala 200 g", "description": "Fiery Kolhapuri onion-garlic masala for misal, usal and curries.", "category": "grocery", "base_price": "159", "delivery_fee": "30", "platform_fee": "3", "gst_percent": "5", "stock": 50, "is_returnable": False, "image": "photo-1702041295471-01b73fd39907"},
        ]
    ),
}

# (seller account email, seller profile, products): the same shape as seed_demo.CATALOGUE.
NEW_SELLERS: list[tuple[str, dict[str, str], list[dict[str, Any]]]] = [
    (
        "kolhapur.leather@shopsense.dev",
        {
            "business_name": "Kolhapur Leather Works",
            "contact_email": "care@kolhapurleather.in",
            "phone": "+919823012345",
            "address": "45 Shivaji Peth, Kolhapur, Maharashtra 416012",
            "gstin": "27AAKFK4521L1Z8",
            "grievance_officer_name": "S. Patil",
            "grievance_officer_email": "grievance@kolhapurleather.in",
        },
        _with_photo(
            [
                {"title": "Kolhapuri Leather Chappals", "description": "Handcrafted genuine-leather Kolhapuris with a toe loop and braided straps. Softens with wear.", "category": "footwear", "base_price": "899", "delivery_fee": "60", "platform_fee": "8", "gst_percent": "12", "stock": 30, "image": "photo-1765961999112-7aea89449b62"},
                {"title": "Men's Leather Oxford Shoes", "description": "Full-grain leather Oxfords with a cushioned insole and stitched rubber sole. Office-ready.", "category": "footwear", "base_price": "2999", "delivery_fee": "0", "platform_fee": "20", "gst_percent": "18", "stock": 15, "image": "photo-1614253429340-98120bd6d753"},
                {"title": "Women's Embroidered Juttis", "description": "Punjabi juttis with thread embroidery and a padded footbed. Comfortable all day.", "category": "footwear", "base_price": "799", "delivery_fee": "60", "platform_fee": "8", "gst_percent": "12", "stock": 26, "image": "photo-1777980722937-f3f87cd0e226"},
                {"title": "Canvas Sneakers", "description": "Low-top canvas sneakers with a vulcanised rubber sole and cotton laces. Washable.", "category": "footwear", "base_price": "1199", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 40, "image": "photo-1787691220334-cda7d4f90c31"},
                {"title": "Running Shoes with Mesh Upper", "description": "Lightweight running shoes with a breathable mesh upper and EVA cushioning.", "category": "footwear", "base_price": "1899", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 32, "image": "photo-1597892657493-6847b9640bac"},
                {"title": "Leather Flip-flops", "description": "Soft leather thong sandals with an anti-slip rubber sole. Everyday comfort.", "category": "footwear", "base_price": "599", "delivery_fee": "60", "platform_fee": "5", "gst_percent": "12", "stock": 38, "image": "photo-1585120824848-8a5cd41493d2"},
                {"title": "Kids' School Shoes (Black)", "description": "Polished black school shoes with a velcro strap and non-marking sole.", "category": "footwear", "base_price": "749", "delivery_fee": "60", "platform_fee": "8", "gst_percent": "12", "stock": 30, "image": "photo-1668069226492-508742b03147"},
                {"title": "Rubber Monsoon Clogs", "description": "Waterproof, quick-dry clogs with drainage holes. Made for Mumbai rains.", "category": "footwear", "base_price": "499", "delivery_fee": "60", "platform_fee": "5", "gst_percent": "12", "stock": 45, "image": "photo-1775049525224-431e016396eb"},
                {"title": "Men's Leather Wallet", "description": "Bi-fold genuine leather wallet with 6 card slots, a coin pocket and RFID blocking.", "category": "accessories", "base_price": "699", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 50, "image": "photo-1627123424574-724758594e93"},
                {"title": "Reversible Leather Belt", "description": "Black/brown reversible belt with a rotating buckle. Cut-to-fit, 35 mm wide.", "category": "accessories", "base_price": "799", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 35, "image": "photo-1664286074176-5206ee5dc878"},
                {"title": "Leather Laptop Messenger Bag", "description": "Full-grain leather messenger bag with a padded 15.6\" laptop sleeve and brass fittings.", "category": "accessories", "base_price": "3499", "delivery_fee": "0", "platform_fee": "25", "gst_percent": "18", "stock": 10, "image": "photo-1473188588951-666fce8e7c68"},
                {"title": "Canvas Tote Bag", "description": "Sturdy 12 oz cotton canvas tote with an inside zip pocket. Replaces plastic bags.", "category": "accessories", "base_price": "449", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 60, "image": "photo-1574365569389-a10d488ca3fb"},
            ]
        ),
    ),
    (
        "annapurna.kitchen@shopsense.dev",
        {
            "business_name": "Annapurna Kitchenware",
            "contact_email": "hello@annapurnakitchen.in",
            "phone": "+919845067890",
            "address": "Shop 12, Chickpet Main Road, Bengaluru, Karnataka 560053",
            "gstin": "29AAFCA3398K1Z4",
            "grievance_officer_name": "M. Rao",
            "grievance_officer_email": "grievance@annapurnakitchen.in",
        },
        _with_photo(
            [
                {"title": "Cast Iron Tawa 12 inch", "description": "Pre-seasoned cast iron dosa tawa. Naturally non-stick with use and adds iron to food.", "category": "kitchen", "base_price": "1099", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 25, "image": "photo-1579805625996-db7b60587362"},
                {"title": "Stainless Steel Pressure Cooker 5 L", "description": "Tri-ply base stainless steel pressure cooker, induction compatible, with a safety valve. ISI marked.", "category": "kitchen", "base_price": "2499", "delivery_fee": "0", "platform_fee": "20", "gst_percent": "18", "stock": 18, "image": "photo-1722684766454-a70335b2d651"},
                {"title": "Copper Water Bottle 1 L", "description": "Pure copper, leak-proof bottle with a lacquered finish. Traditionally used for storing drinking water.", "category": "kitchen", "base_price": "899", "delivery_fee": "40", "platform_fee": "8", "gst_percent": "18", "stock": 40, "image": "photo-1739484440756-03afc18ca096"},
                {"title": "Brass Kadhai with Handles", "description": "Tin-lined brass kadhai, 2.5 L, for slow cooking and deep frying.", "category": "kitchen", "base_price": "2199", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "12", "stock": 12, "image": "photo-1652960018678-1f19799996c5"},
                {"title": "Steel Masala Dabba", "description": "Stainless steel spice box with 7 bowls, a spoon and a see-through lid.", "category": "kitchen", "base_price": "649", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 45, "image": "photo-1592457711340-2412dc07b733"},
                {"title": "Glass Food Containers Set of 4", "description": "Borosilicate glass containers with airtight lids. Microwave, oven and freezer safe.", "category": "kitchen", "base_price": "1199", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 30, "image": "photo-1777380104555-1f47491729a6"},
                {"title": "Wooden Chopping Board", "description": "Thick acacia wood chopping board with a juice groove, 38 × 25 cm.", "category": "kitchen", "base_price": "599", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 35, "image": "photo-1666013942797-9daa4b8b3b4f"},
                {"title": "Stainless Steel Dinner Set 24 pcs", "description": "Mirror-finish steel dinner set for 4: plates, bowls, glasses and spoons.", "category": "kitchen", "base_price": "1999", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 15, "image": "photo-1742281258189-3b933879867a"},
                {"title": "Electric Kettle 1.5 L", "description": "Stainless steel kettle with auto shut-off and boil-dry protection. 1500 W.", "category": "kitchen", "base_price": "1299", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "18", "stock": 28, "image": "photo-1738520420652-0c47cea3922b"},
                {"title": "Clay Cooking Pot (Handi)", "description": "Handmade unglazed clay handi for slow-cooked biryani and dal. 2 L with lid.", "category": "kitchen", "base_price": "699", "delivery_fee": "79", "platform_fee": "5", "gst_percent": "5", "stock": 16, "image": "photo-1671167051711-1fcc8ddd7d40"},
            ]
        ),
    ),
    (
        "pustak.kendra@shopsense.dev",
        {
            "business_name": "Pustak Kendra",
            "contact_email": "orders@pustakkendra.in",
            "phone": "+919811023456",
            "address": "27 Daryaganj, New Delhi, Delhi 110002",
            "gstin": "07AAGFP6612M1Z1",
            "grievance_officer_name": "A. Gupta",
            "grievance_officer_email": "grievance@pustakkendra.in",
        },
        _with_photo(
            [
                {"title": "Godaan (Hindi) – Munshi Premchand", "description": "Premchand's classic novel of rural India and the farmer Hori's struggle. Paperback, Hindi.", "category": "books", "base_price": "199", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 40, "image": "photo-1534289855405-ab820a118fc1"},
                {"title": "Gitanjali – Rabindranath Tagore", "description": "The Nobel Prize-winning collection of song offerings, in English. Paperback.", "category": "books", "base_price": "149", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 45, "image": "photo-1543002588-bfa74002ed7e"},
                {"title": "Malgudi Days – R. K. Narayan", "description": "Timeless short stories set in the fictional town of Malgudi. Paperback.", "category": "books", "base_price": "250", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 50, "image": "photo-1506880018603-83d5b814b5a6"},
                {"title": "Shyamchi Aai (Marathi) – Sane Guruji", "description": "The much-loved Marathi memoir of a mother's lessons in values. Paperback.", "category": "books", "base_price": "180", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 35, "image": "photo-1610116306796-6fea9f4fae38"},
                {"title": "The Discovery of India – Jawaharlal Nehru", "description": "Nehru's sweeping history of India, written in prison in 1944. Paperback.", "category": "books", "base_price": "399", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 25, "image": "photo-1521587760476-6c12a4b040da"},
                {"title": "Panchatantra Stories for Children", "description": "Illustrated collection of 50 Panchatantra fables in English. Hardcover.", "category": "books", "base_price": "299", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 40, "image": "photo-1605627082049-2e77d4d16716"},
                {"title": "Ignited Minds – A. P. J. Abdul Kalam", "description": "Dr. Kalam's call to young Indians to unleash their potential. Paperback.", "category": "books", "base_price": "225", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 45, "image": "photo-1542372147193-a7aca54189cd"},
                {"title": "Mrityunjay (Marathi) – Shivaji Sawant", "description": "The epic Marathi novel retelling the Mahabharata through Karna's eyes. Paperback.", "category": "books", "base_price": "499", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 20, "image": "photo-1688918811212-1ff5821e49fa"},
                {"title": "Class 10 Mathematics Practice Workbook", "description": "Chapter-wise practice questions, solved examples and sample papers for board exams.", "category": "books", "base_price": "349", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 60, "image": "photo-1676302447092-14a103558511"},
                {"title": "Indian Vegetarian Cookbook", "description": "120 home-style recipes from every region of India, with step-by-step photos.", "category": "books", "base_price": "599", "delivery_fee": "40", "platform_fee": "0", "gst_percent": "0", "stock": 22, "image": "photo-1542010589005-d1eacc3918f2"},
            ]
        ),
    ),
    (
        "ayur.naturals@shopsense.dev",
        {
            "business_name": "Ayur Naturals",
            "contact_email": "support@ayurnaturals.in",
            "phone": "+919847034567",
            "address": "TC 9/1123, Sasthamangalam, Thiruvananthapuram, Kerala 695010",
            "gstin": "32AAHCA7745N1Z6",
            "grievance_officer_name": "L. Nair",
            "grievance_officer_email": "grievance@ayurnaturals.in",
        },
        _with_photo(
            [
                {"title": "Kumkumadi Face Oil 30 ml", "description": "Ayurvedic saffron face oil for glowing skin. Cold-pressed oils, no mineral oil.", "category": "beauty", "base_price": "699", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 35, "is_returnable": False, "image": "photo-1706419972358-028e2c713133"},
                {"title": "Neem & Tulsi Face Wash 100 ml", "description": "Gentle soap-free face wash with neem and tulsi for oily, acne-prone skin.", "category": "beauty", "base_price": "249", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 55, "is_returnable": False, "image": "photo-1616750819456-5cdee9b85d22"},
                {"title": "Handmade Sandalwood Soap (Pack of 3)", "description": "Cold-process soap with sandalwood oil and turmeric. No SLS, no parabens.", "category": "beauty", "base_price": "299", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 60, "is_returnable": False, "image": "photo-1600857544200-b2f666a9a2ec"},
                {"title": "Bhringraj Hair Oil 200 ml", "description": "Traditional herbal hair oil with bhringraj, amla and coconut oil to reduce hair fall.", "category": "beauty", "base_price": "349", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 45, "is_returnable": False, "image": "photo-1671493229066-f36e86b35841"},
                {"title": "Aloe Vera Gel 150 g", "description": "99% pure aloe vera gel for skin and hair. Soothes sunburn.", "category": "beauty", "base_price": "199", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 70, "is_returnable": False, "image": "photo-1570295835271-04c05b4ed943"},
                {"title": "Rose Water Toner 200 ml", "description": "Steam-distilled Kannauj rose water. Tones and refreshes skin.", "category": "beauty", "base_price": "179", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 65, "is_returnable": False, "image": "photo-1632243575963-3143700087ed"},
                {"title": "Herbal Kajal", "description": "Smudge-proof kajal made with almond oil and camphor. Ophthalmologically tested.", "category": "beauty", "base_price": "149", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 80, "is_returnable": False, "image": "photo-1709477542149-f4e0e21d590b"},
                {"title": "Natural Lip Balm (Beetroot)", "description": "Tinted lip balm with beetroot, shea butter and beeswax. Petroleum-free.", "category": "beauty", "base_price": "129", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "18", "stock": 90, "is_returnable": False, "image": "photo-1773452451137-acc5fd1c0dfd"},
                {"title": "Bamboo Toothbrush (Pack of 4)", "description": "Biodegradable bamboo handles with soft charcoal-infused bristles.", "category": "beauty", "base_price": "199", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "12", "stock": 75, "is_returnable": False, "image": "photo-1589365252845-092198ba5334"},
            ]
        ),
    ),
    (
        "khel.sports@shopsense.dev",
        {
            "business_name": "Khel Sports",
            "contact_email": "team@khelsports.in",
            "phone": "+919815045678",
            "address": "Basti Sheikh Road, Jalandhar, Punjab 144002",
            "gstin": "03AAJFK2289P1Z3",
            "grievance_officer_name": "H. Singh",
            "grievance_officer_email": "grievance@khelsports.in",
        },
        _with_photo(
            [
                {"title": "Travel Backpack 30 L", "description": "Water-resistant 30 L backpack with a laptop compartment, bottle pockets and padded straps.", "category": "accessories", "base_price": "1599", "delivery_fee": "0", "platform_fee": "15", "gst_percent": "18", "stock": 25, "image": "photo-1509762774605-f07235a08f1f"},
                {"title": "English Willow Cricket Bat", "description": "Grade 2 English willow bat, full size, pre-knocked and ready to play.", "category": "sports", "base_price": "5999", "delivery_fee": "0", "platform_fee": "40", "gst_percent": "12", "stock": 8, "image": "photo-1595210382266-2d0077c1f541"},
                {"title": "Leather Cricket Ball (Pack of 2)", "description": "Four-piece alum-tanned leather balls for club matches.", "category": "sports", "base_price": "899", "delivery_fee": "40", "platform_fee": "8", "gst_percent": "12", "stock": 30, "image": "photo-1531415074968-036ba1b575da"},
                {"title": "Yoga Mat 6 mm", "description": "Anti-slip TPE yoga mat with alignment lines and a carry strap.", "category": "sports", "base_price": "999", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 40, "image": "photo-1552196563-55cd4e45efb3"},
                {"title": "Badminton Racquet Set", "description": "Two aluminium racquets with 3 nylon shuttlecocks and a carry cover.", "category": "sports", "base_price": "1099", "delivery_fee": "0", "platform_fee": "10", "gst_percent": "12", "stock": 25, "image": "photo-1708312604109-16c0be9326cd"},
                {"title": "Football Size 5", "description": "Machine-stitched PU football for turf and grass. FIFA size 5.", "category": "sports", "base_price": "799", "delivery_fee": "40", "platform_fee": "8", "gst_percent": "12", "stock": 30, "image": "photo-1574629810360-7efbbe195018"},
                {"title": "Adjustable Dumbbells 10 kg Set", "description": "Pair of adjustable PVC dumbbells with 2.5 kg and 1.25 kg plates.", "category": "sports", "base_price": "1599", "delivery_fee": "99", "platform_fee": "15", "gst_percent": "18", "stock": 15, "image": "photo-1638536532686-d610adfc8e5c"},
                {"title": "Skipping Rope with Counter", "description": "Ball-bearing speed rope with a digital jump counter and foam handles.", "category": "sports", "base_price": "349", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 50, "image": "photo-1516876345887-6dd74f80787a"},
                {"title": "Carrom Board Full Size", "description": "32\" carrom board with a smooth playing surface, coins, striker and powder.", "category": "sports", "base_price": "2499", "delivery_fee": "149", "platform_fee": "20", "gst_percent": "12", "stock": 10, "image": "photo-1617300067484-314ed2cfd9a6"},
            ]
        ),
    ),
    (
        "littlesteps.toys@shopsense.dev",
        {
            "business_name": "Little Steps Toys",
            "contact_email": "hello@littlestepstoys.in",
            "phone": "+919824056789",
            "address": "Plot 88, GIDC Makarpura, Vadodara, Gujarat 390010",
            "gstin": "24AAKFL5534Q1Z9",
            "grievance_officer_name": "N. Shah",
            "grievance_officer_email": "grievance@littlestepstoys.in",
        },
        _with_photo(
            [
                {"title": "Wooden Channapatna Stacking Toy", "description": "Handmade Channapatna rings coloured with natural lacquer. Safe for toddlers.", "category": "toys", "base_price": "499", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 30, "image": "photo-1618842676088-c4d48a6a7c9d"},
                {"title": "Wooden ABC Building Blocks 40 pcs", "description": "Smooth-sanded wooden blocks with letters, numbers and pictures, finished in non-toxic paint. Ages 2+.", "category": "toys", "base_price": "699", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 35, "image": "photo-1535572290543-960a8046f5af"},
                {"title": "Kids' Art Kit 68 pcs", "description": "Crayons, sketch pens, oil pastels and watercolours in a carry case.", "category": "toys", "base_price": "599", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 40, "image": "photo-1558181330-e053fecae838"},
                {"title": "Die-cast Vintage Toy Car", "description": "Pull-back die-cast metal car with opening doors and rubber tyres. Ages 3+.", "category": "toys", "base_price": "399", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "18", "stock": 40, "image": "photo-1581235720704-06d3acfcb36f"},
                {"title": "Soft Teddy Bear 40 cm", "description": "Super-soft plush teddy with stitched eyes. Safe for all ages.", "category": "toys", "base_price": "699", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 30, "image": "photo-1648311203209-da34f7d0d800"},
                {"title": "Jigsaw Puzzle 1000 pcs", "description": "1000-piece jigsaw on thick recycled board with a poster guide. Ages 12+.", "category": "toys", "base_price": "549", "delivery_fee": "40", "platform_fee": "5", "gst_percent": "12", "stock": 30, "image": "photo-1730804518415-75297e8d2a41"},
                {"title": "Traditional Wooden Spinning Top (Lattu)", "description": "Hand-turned wooden lattu with a cotton string. Set of 3.", "category": "toys", "base_price": "199", "delivery_fee": "40", "platform_fee": "3", "gst_percent": "12", "stock": 60, "image": "photo-1700161735948-ae9f18a76110"},
            ]
        ),
    ),
]

# Per-size stock and garment/foot measurements (cm) for the sized products above.
EXTRA_SIZES: dict[str, dict[str, Any]] = {
    "Men's Linen Casual Shirt": {
        "sizes": [{"size": "S", "stock": 4}, {"size": "M", "stock": 8}, {"size": "L", "stock": 8}, {"size": "XL", "stock": 6}, {"size": "XXL", "stock": 4}],
        "size_chart": [
            {"size": "S", "chest": 100, "length": 72, "shoulder": 44, "sleeve": 60},
            {"size": "M", "chest": 106, "length": 74, "shoulder": 46, "sleeve": 61},
            {"size": "L", "chest": 112, "length": 76, "shoulder": 48, "sleeve": 62},
            {"size": "XL", "chest": 118, "length": 78, "shoulder": 50, "sleeve": 63},
            {"size": "XXL", "chest": 124, "length": 80, "shoulder": 52, "sleeve": 64},
        ],
    },
    "Organic Cotton Crew T-Shirt": {
        "sizes": [{"size": "S", "stock": 9}, {"size": "M", "stock": 19}, {"size": "L", "stock": 18}, {"size": "XL", "stock": 14}],
        "size_chart": [
            {"size": "S", "chest": 96, "length": 68, "shoulder": 42, "sleeve": 20},
            {"size": "M", "chest": 102, "length": 70, "shoulder": 44, "sleeve": 21},
            {"size": "L", "chest": 108, "length": 72, "shoulder": 46, "sleeve": 22},
            {"size": "XL", "chest": 114, "length": 74, "shoulder": 48, "sleeve": 23},
        ],
    },
    "Women's Chikankari Kurti": {
        "sizes": [{"size": "S", "stock": 3}, {"size": "M", "stock": 7}, {"size": "L", "stock": 6}, {"size": "XL", "stock": 5}, {"size": "XXL", "stock": 3}],
        "size_chart": [
            {"size": "S", "chest": 86, "waist": 76, "hip": 94, "length": 110, "shoulder": 36, "sleeve": 44},
            {"size": "M", "chest": 91, "waist": 81, "hip": 99, "length": 111, "shoulder": 37, "sleeve": 44},
            {"size": "L", "chest": 96, "waist": 86, "hip": 104, "length": 112, "shoulder": 38, "sleeve": 45},
            {"size": "XL", "chest": 101, "waist": 91, "hip": 109, "length": 113, "shoulder": 39, "sleeve": 45},
            {"size": "XXL", "chest": 106, "waist": 96, "hip": 114, "length": 114, "shoulder": 40, "sleeve": 46},
        ],
    },
    "Stretch Denim Jeans (Slim)": {
        "sizes": [{"size": "28", "stock": 4}, {"size": "30", "stock": 7}, {"size": "32", "stock": 7}, {"size": "34", "stock": 6}, {"size": "36", "stock": 4}],
        "size_chart": [
            {"size": "28", "waist": 72, "hip": 92, "length": 100, "inseam": 76},
            {"size": "30", "waist": 77, "hip": 97, "length": 101, "inseam": 77},
            {"size": "32", "waist": 82, "hip": 102, "length": 102, "inseam": 78},
            {"size": "34", "waist": 87, "hip": 107, "length": 103, "inseam": 78},
            {"size": "36", "waist": 92, "hip": 112, "length": 104, "inseam": 79},
        ],
    },
    "Hooded Cotton Sweatshirt": {
        "sizes": [{"size": "S", "stock": 3}, {"size": "M", "stock": 6}, {"size": "L", "stock": 6}, {"size": "XL", "stock": 5}],
        "size_chart": [
            {"size": "S", "chest": 100, "length": 66, "shoulder": 44, "sleeve": 60},
            {"size": "M", "chest": 106, "length": 68, "shoulder": 46, "sleeve": 61},
            {"size": "L", "chest": 112, "length": 70, "shoulder": 48, "sleeve": 62},
            {"size": "XL", "chest": 118, "length": 72, "shoulder": 50, "sleeve": 63},
        ],
    },
    "Cotton Pyjama Set": {
        "sizes": [{"size": "S", "stock": 4}, {"size": "M", "stock": 8}, {"size": "L", "stock": 7}, {"size": "XL", "stock": 6}],
        "size_chart": [
            {"size": "S", "chest": 100, "length": 66, "shoulder": 44, "sleeve": 60},
            {"size": "M", "chest": 106, "length": 68, "shoulder": 46, "sleeve": 61},
            {"size": "L", "chest": 112, "length": 70, "shoulder": 48, "sleeve": 62},
            {"size": "XL", "chest": 118, "length": 72, "shoulder": 50, "sleeve": 63},
        ],
    },
    "Men's Cotton Formal Trousers": {
        "sizes": [{"size": "28", "stock": 3}, {"size": "30", "stock": 6}, {"size": "32", "stock": 6}, {"size": "34", "stock": 4}, {"size": "36", "stock": 3}],
        "size_chart": [
            {"size": "28", "waist": 72, "hip": 92, "length": 100, "inseam": 76},
            {"size": "30", "waist": 77, "hip": 97, "length": 101, "inseam": 77},
            {"size": "32", "waist": 82, "hip": 102, "length": 102, "inseam": 78},
            {"size": "34", "waist": 87, "hip": 107, "length": 103, "inseam": 78},
            {"size": "36", "waist": 92, "hip": 112, "length": 104, "inseam": 79},
        ],
    },
    "Men's Silk Kurta": {
        "sizes": [{"size": "S", "stock": 2}, {"size": "M", "stock": 5}, {"size": "L", "stock": 4}, {"size": "XL", "stock": 3}, {"size": "XXL", "stock": 2}],
        "size_chart": [
            {"size": "S", "chest": 96, "waist": 90, "length": 104, "shoulder": 42, "sleeve": 58},
            {"size": "M", "chest": 102, "waist": 96, "length": 106, "shoulder": 44, "sleeve": 59},
            {"size": "L", "chest": 108, "waist": 102, "length": 108, "shoulder": 46, "sleeve": 60},
            {"size": "XL", "chest": 114, "waist": 108, "length": 110, "shoulder": 48, "sleeve": 61},
            {"size": "XXL", "chest": 120, "waist": 114, "length": 112, "shoulder": 50, "sleeve": 62},
        ],
    },
    "Kolhapuri Leather Chappals": {
        "sizes": [{"size": "UK 6", "stock": 4}, {"size": "UK 7", "stock": 8}, {"size": "UK 8", "stock": 8}, {"size": "UK 9", "stock": 6}, {"size": "UK 10", "stock": 4}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
    "Men's Leather Oxford Shoes": {
        "sizes": [{"size": "UK 6", "stock": 2}, {"size": "UK 7", "stock": 4}, {"size": "UK 8", "stock": 4}, {"size": "UK 9", "stock": 3}, {"size": "UK 10", "stock": 2}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
    "Women's Embroidered Juttis": {
        "sizes": [{"size": "UK 3", "stock": 4}, {"size": "UK 4", "stock": 7}, {"size": "UK 5", "stock": 7}, {"size": "UK 6", "stock": 5}, {"size": "UK 7", "stock": 3}],
        "size_chart": [
            {"size": "UK 3", "length": 22.0},
            {"size": "UK 4", "length": 22.8},
            {"size": "UK 5", "length": 23.7},
            {"size": "UK 6", "length": 24.5},
            {"size": "UK 7", "length": 25.4},
        ],
    },
    "Canvas Sneakers": {
        "sizes": [{"size": "UK 6", "stock": 5}, {"size": "UK 7", "stock": 11}, {"size": "UK 8", "stock": 11}, {"size": "UK 9", "stock": 8}, {"size": "UK 10", "stock": 5}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
    "Running Shoes with Mesh Upper": {
        "sizes": [{"size": "UK 6", "stock": 4}, {"size": "UK 7", "stock": 9}, {"size": "UK 8", "stock": 9}, {"size": "UK 9", "stock": 6}, {"size": "UK 10", "stock": 4}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
    "Leather Flip-flops": {
        "sizes": [{"size": "UK 6", "stock": 5}, {"size": "UK 7", "stock": 10}, {"size": "UK 8", "stock": 10}, {"size": "UK 9", "stock": 8}, {"size": "UK 10", "stock": 5}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
    "Kids' School Shoes (Black)": {
        "sizes": [{"size": "UK 11K", "stock": 4}, {"size": "UK 12K", "stock": 8}, {"size": "UK 13K", "stock": 8}, {"size": "UK 1", "stock": 6}, {"size": "UK 2", "stock": 4}],
        "size_chart": [
            {"size": "UK 11K", "length": 17.8},
            {"size": "UK 12K", "length": 18.6},
            {"size": "UK 13K", "length": 19.5},
            {"size": "UK 1", "length": 20.3},
            {"size": "UK 2", "length": 21.2},
        ],
    },
    "Rubber Monsoon Clogs": {
        "sizes": [{"size": "UK 6", "stock": 6}, {"size": "UK 7", "stock": 12}, {"size": "UK 8", "stock": 12}, {"size": "UK 9", "stock": 9}, {"size": "UK 10", "stock": 6}],
        "size_chart": [
            {"size": "UK 6", "length": 24.6},
            {"size": "UK 7", "length": 25.4},
            {"size": "UK 8", "length": 26.2},
            {"size": "UK 9", "length": 27.1},
            {"size": "UK 10", "length": 27.9},
        ],
    },
}
