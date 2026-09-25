"""Shared request payloads for tests."""

SELLER_PROFILE = {
    "business_name": "Pune Handlooms Pvt Ltd",
    "contact_email": "support@punehandlooms.in",
    "phone": "+919876543210",
    "address": "12 FC Road, Shivajinagar, Pune, Maharashtra 411005",
    "gstin": "27abcde1234f1z5",
    "grievance_officer_name": "R. Kulkarni",
    "grievance_officer_email": "grievance@punehandlooms.in",
}

# base 1000 + delivery 40 + platform 10 = 1050; GST 18% = 189; final 1239.00 per unit.
PRODUCT = {
    "title": "Cotton Kurta",
    "description": "Handwoven cotton kurta",
    "category": "  Clothing ",
    "base_price": "1000",
    "delivery_fee": "40",
    "platform_fee": "10",
    "stock": 5,
}

ADDRESS = "Flat 4, Sai Residency, Kothrud, Pune, Maharashtra 411038"
