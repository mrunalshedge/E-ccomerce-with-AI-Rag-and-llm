"""Business rules in one place, so they're easy to find, explain and change."""

from decimal import Decimal

# Cart
MAX_QUANTITY_PER_ITEM = 10

# Returns: wrong or counterfeit items can ALWAYS be returned within the window, even if the
# product is marked non-returnable. Other reasons follow the product's is_returnable flag.
RETURN_WINDOW_DAYS = 7

# Seller trust score (0–100) drops when a wrong/counterfeit return is approved.
TRUST_PENALTY_WRONG_OR_FAKE = 5.0

ZERO = Decimal("0.00")
