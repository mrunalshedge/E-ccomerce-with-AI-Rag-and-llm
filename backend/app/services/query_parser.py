"""Understands a shopper's search the way they type it (English, Hinglish, हिंदी, मराठी).

"which is best kurta under 1000" → terms ["kurta", "kurti"], max ₹1000, best-rated first.
"1000 से कम के खिलौने"           → terms ["toy"], category toys, max ₹1000.

Deterministic on purpose: instant, free and testable (no LLM call per keystroke). The multilingual
embedding model still handles meaning; this module handles what it can't: budgets, "best"/"cheap",
filler words, Indian product words the model barely knows ("kurta") and Hindi/Marathi nouns.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

Sort = Literal["relevance", "rating", "price_asc"]

# ---------- vocabulary ----------

# Words that say nothing about the product ("which is the best …", "mujhe … chahiye").
FILLER = frozenset(
    """
    a an the is are was be it this that these those which what who whom where when how i me my we us our you your
    for of in on to at by with from and or as any all some something anything show find search looking look want
    need give get buy please price prices priced cost costing rs rupees rupee inr budget range
    best good great nice top better cheap cheapest cheaper affordable lowest low under below less than within upto
    up above over more max maximum min minimum around about approx between
    pcs pc piece pieces kg kgs gm gms gram grams ml litre litres liter liters pack
    kya hai hain konsa kaunsa kaun koi chahiye chahie mujhe mere mera meri liye ke ka ki ko se kam tak andar
    accha achha acha badhiya sabse sasta saste sasti zyada jyada upar wala wali wale dikhao batao
    क्या है हैं कौन कौनसा कौन-सा कोई चाहिए मुझे मेरे मेरा मेरी लिए के का की को से कम तक अंदर अच्छा अच्छी
    बढ़िया सबसे सस्ता सस्ते सस्ती ज़्यादा ज्यादा ऊपर वाला वाली दिखाओ बताओ रुपये रुपए रु
    काय आहे आहेत कोणता कोणती मला हवे हवा हवी साठी चा ची चे च्या ला पेक्षा कमी आत पर्यंत चांगला चांगली
    स्वस्त जास्त वर दाखवा सांगा
    """.split()
)

BEST_WORDS = frozenset("best top good great nice better badhiya accha achha acha सबसे अच्छा अच्छी बढ़िया चांगला चांगली".split())
CHEAP_WORDS = frozenset("cheap cheapest cheaper affordable lowest sasta saste sasti सस्ता सस्ते सस्ती स्वस्त".split())

# Indian-language or local product words → English catalogue words.
GLOSSARY: dict[str, tuple[str, ...]] = {
    # clothing
    "kurta": ("kurta", "kurti"), "kurti": ("kurti", "kurta"), "कुर्ता": ("kurta", "kurti"), "कुर्ती": ("kurti", "kurta"),
    "साड़ी": ("saree",), "साडी": ("saree",), "sari": ("saree",), "saari": ("saree",),
    "दुपट्टा": ("dupatta",), "ओढणी": ("dupatta",), "शॉल": ("shawl",), "शाल": ("shawl",),
    "कमीज़": ("shirt",), "कमीज": ("shirt",), "शर्ट": ("shirt",), "जीन्स": ("jeans",), "पायजामा": ("pyjama",),
    "pajama": ("pyjama",), "धोती": ("dhoti",), "hoodie": ("hooded", "sweatshirt"), "tshirt": ("t-shirt", "tee"),
    "कपड़े": ("clothing",), "कपडे": ("clothing",), "kapde": ("clothing",), "kapda": ("clothing",),
    # footwear
    "joote": ("shoe",), "joota": ("shoe",), "juta": ("shoe",), "जूते": ("shoe",), "जूता": ("shoe",), "बूट": ("shoe",),
    "चप्पल": ("chappal",), "chappals": ("chappal",), "slipper": ("flip-flop", "chappal"), "sandal": ("sandal", "chappal"),
    # accessories
    "ghadi": ("watch",), "घड़ी": ("watch",), "घड्याळ": ("watch",), "बैग": ("bag",), "थैली": ("bag",),
    "बटुआ": ("wallet",), "पाकीट": ("wallet",), "चश्मा": ("sunglasses",), "jhumka": ("jhumka", "earring"),
    "झुमके": ("jhumka", "earring"),
    # home & kitchen
    "दीया": ("diya",), "दिया": ("diya",), "दीये": ("diya",), "दिये": ("diya",), "diye": ("diya",), "deepak": ("diya",), "पणती": ("diya",), "पर्दे": ("curtain",), "parde": ("curtain",),
    "तौलिया": ("towel",), "टॉवेल": ("towel",), "मोमबत्ती": ("candle",), "पौधा": ("plant",), "रोप": ("plant",),
    "बर्तन": ("kitchen",), "bartan": ("kitchen",), "भांडी": ("kitchen",), "रसोई": ("kitchen",),
    "तवा": ("tawa",), "कढ़ाई": ("kadhai",), "कढई": ("kadhai",), "kadai": ("kadhai",), "कुकर": ("cooker",),
    "बोतल": ("bottle",), "बाटली": ("bottle",), "केतली": ("kettle",),
    # grocery
    "chai": ("tea",), "patti": ("tea",), "पत्ती": ("tea",), "चाय": ("tea",), "चहा": ("tea",), "chawal": ("rice",), "चावल": ("rice",), "तांदूळ": ("rice",),
    "दाल": ("dal",), "डाळ": ("dal",), "घी": ("ghee",), "तूप": ("ghee",), "shahad": ("honey",), "शहद": ("honey",),
    "मध": ("honey",), "मसाला": ("masala",), "आटा": ("atta",), "पीठ": ("atta",), "कॉफी": ("coffee",),
    "तेल": ("oil",), "हल्दी": ("turmeric",), "haldi": ("turmeric",), "बादाम": ("almond",), "badam": ("almond",),
    "गुड़": ("jaggery",), "gud": ("jaggery",),
    # electronics
    "इयरफोन": ("earphone", "earbud"), "हेडफोन": ("headphone",), "चार्जर": ("charger",), "स्पीकर": ("speaker",),
    "earphone": ("earphone", "earbud", "neckband"), "earbud": ("earbud", "earphone"),
    # books
    "kitab": ("book",), "किताब": ("book",), "पुस्तक": ("book",), "novel": ("novel", "book"),
    # beauty
    "साबुन": ("soap",), "साबण": ("soap",), "sabun": ("soap",), "काजल": ("kajal",),
    # sports & toys
    "बल्ला": ("bat",), "गेंद": ("ball",), "चेंडू": ("ball",), "योग": ("yoga",), "योगा": ("yoga",),
    "diwali": ("diwali", "diya", "candle", "festive"), "दिवाली": ("diwali", "diya", "candle", "festive"),
    "दिवाळी": ("diwali", "diya", "candle", "festive"), "festival": ("festive", "festival"),
    "decoration": ("decor", "decoration"), "सजावट": ("decor", "decoration"),
    "khilona": ("toy",), "khilone": ("toy",), "खिलौना": ("toy",), "खिलौने": ("toy",), "खेळणी": ("toy",),
    "खेळणे": ("toy",),
}

# Words that name a whole category (after glossary translation and singularising).
CATEGORY_WORDS: dict[str, str] = {
    "clothing": "clothing", "clothe": "clothing", "dress": "clothing", "apparel": "clothing",
    "shoe": "footwear", "footwear": "footwear", "chappal": "footwear", "sandal": "footwear", "sneaker": "footwear",
    "accessory": "accessories", "accessorie": "accessories", "jewellery": "accessories", "jewelry": "accessories",
    "decor": "home", "furniture": "home",
    "kitchen": "kitchen", "cookware": "kitchen", "utensil": "kitchen",
    "grocery": "grocery", "grocerie": "grocery", "kirana": "grocery", "किराना": "grocery", "किराणा": "grocery",
    "electronic": "electronics", "gadget": "electronics", "इलेक्ट्रॉनिक्स": "electronics",
    "book": "books", "novel": "books",
    "beauty": "beauty", "skincare": "beauty", "cosmetic": "beauty", "makeup": "beauty",
    "sport": "sports", "fitness": "sports", "gym": "sports", "खेल": "sports", "खेळ": "sports",
    "toy": "toys", "game": "toys",
}

# ---------- budgets ----------

_NUM = r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|हज़ार|हजार)?\s*(?:₹|rs\.?|/-|rupees?|रुपये|रुपए|रु\.?)?"
_MAX_BEFORE = r"(?:under|below|less than|lesser than|within|upto|up to|max|maximum|not more than|<=?|cheaper than)"
_MAX_AFTER = r"(?:se kam|ke andar|ke under|tak|se neeche|से कम|के अंदर|के भीतर|तक|पेक्षा कमी|च्या आत|च्या आतील|पर्यंत|आत)"
_MIN_BEFORE = r"(?:above|over|more than|greater than|starting|from|min|minimum|>=?)"
_MIN_AFTER = r"(?:se upar|se zyada|se jyada|से ऊपर|से ज़्यादा|से ज्यादा|पेक्षा जास्त|च्या वर)"

_RANGE = re.compile(rf"(?:between\s+)?{_NUM}\s*(?:-|–|to|and|se)\s*{_NUM}", re.I)
_MAX_1 = re.compile(rf"{_MAX_BEFORE}\s*{_NUM}", re.I)
_MAX_2 = re.compile(rf"{_NUM}\s*{_MAX_AFTER}", re.I)
_MIN_1 = re.compile(rf"{_MIN_BEFORE}\s*{_NUM}", re.I)
_MIN_2 = re.compile(rf"{_NUM}\s*{_MIN_AFTER}", re.I)

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _amount(number: str, thousand: str | None) -> Decimal:
    value = Decimal(number.replace(",", ""))
    return value * 1000 if thousand else value


@dataclass
class ParsedQuery:
    text: str  # for meaning search: the shopper's words minus the budget, plus English translations
    terms: list[str] = field(default_factory=list)  # English keyword stems to match in titles/descriptions
    # One group per word the shopper typed, holding its alternatives ("kurta" → kurta/kurti), so a
    # product matching a synonym counts as matching that word once, not as a separate word.
    concepts: list[tuple[str, ...]] = field(default_factory=list)
    categories: set[str] = field(default_factory=set)
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort: Sort = "relevance"


def singular(word: str) -> str:
    """Crude English singular for matching ("shoes" → "shoe", "glasses" → "glass", "toys" → "toy")."""
    if len(word) > 4 and word.endswith("es") and word[:-2].endswith(("s", "x", "ch", "sh")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    # Devanagari words include vowel signs (Unicode "marks"), which \w alone would split on.
    return re.findall(r"[\wऀ-ॿ\-]+", text.lower())


def parse_query(query: str) -> ParsedQuery:
    raw = query.translate(_DEVANAGARI_DIGITS).strip()
    min_price = max_price = None

    # Budget: remove the phrase so "1000" isn't searched as a word.
    if m := _RANGE.search(raw):
        a, b = _amount(m.group(1), m.group(2)), _amount(m.group(3), m.group(4))
        if a > 0 and b > 0 and _looks_like_price(raw, m):
            min_price, max_price = min(a, b), max(a, b)
            raw = raw.replace(m.group(0), " ")
    for pattern, is_max in ((_MAX_1, True), (_MAX_2, True), (_MIN_1, False), (_MIN_2, False)):
        if m := pattern.search(raw):
            amount = _amount(m.group(1), m.group(2))
            if amount > 0:
                if is_max and max_price is None:
                    max_price = amount
                elif not is_max and min_price is None:
                    min_price = amount
                raw = raw.replace(m.group(0), " ")

    tokens = _tokens(raw)
    sort: Sort = "relevance"
    if any(t in CHEAP_WORDS for t in tokens):
        sort = "price_asc"
    elif any(t in BEST_WORDS for t in tokens):
        sort = "rating"

    kept = [t for t in tokens if t not in FILLER and (len(t) >= 2 or not t.isascii())]
    terms: list[str] = []
    concepts: list[tuple[str, ...]] = []
    categories: set[str] = set()
    extra: list[str] = []
    for token in kept:
        translated = GLOSSARY.get(token) or GLOSSARY.get(singular(token))
        group: list[str] = []
        for word in translated or (token,):
            stem = singular(word)
            if stem in CATEGORY_WORDS:
                categories.add(CATEGORY_WORDS[stem])
            if word in CATEGORY_WORDS:
                categories.add(CATEGORY_WORDS[word])
            if stem.isascii() and not stem.isdigit():
                group.append(stem)
                if stem not in terms:
                    terms.append(stem)
        if group and tuple(group) not in concepts:
            concepts.append(tuple(group))
        if translated:
            extra.extend(translated)

    # The embedding model reads whole sentences well ("something cool for summer"), so it gets the
    # original wording (only the budget removed); filler removal is just for keyword matching.
    sentence = " ".join(raw.split())
    text = " ".join([sentence] + [w for w in dict.fromkeys(extra) if w not in tokens]) if sentence else query.strip()
    return ParsedQuery(text=text, terms=terms, concepts=concepts, categories=categories, min_price=min_price, max_price=max_price, sort=sort)


def _looks_like_price(text: str, m: re.Match[str]) -> bool:
    """A bare "500-1000" is a budget, but "set of 2-4" or "1000 pcs" isn't: require a currency sign or
    a price word nearby."""
    around = text[max(0, m.start() - 12) : m.end() + 12].lower()
    return bool(re.search(r"₹|rs\b|rupee|inr|price|budget|between|रुपये|रुपए", around))
