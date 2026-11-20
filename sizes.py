"""Package size parsing and unit prices for Yerevan City products.

Understands Armenian and Russian units in product names.
Run `python3 sizes.py` to execute the built-in tests.
"""
import re

# unit text -> (kind, multiplier to base unit: grams / ml / pieces)
UNITS = {
    "кг": ("g", 1000), "կգ": ("g", 1000),
    "гр": ("g", 1), "г": ("g", 1), "գր": ("g", 1), "գ": ("g", 1),
    "л": ("ml", 1000), "լ": ("ml", 1000),
    "мл": ("ml", 1), "մլ": ("ml", 1),
    "шт": ("pc", 1), "հտ": ("pc", 1),
}

UNIT_ALT = "кг|կգ|гр|գր|г|գ|мл|մլ|л|լ|шт|հտ"
NUM = r"\d+(?:[.,]\d+)?"
NOT_LETTER = r"(?![а-яёա-ֆa-z])"   # the unit must not continue into another letter

# number + unit ("10 литров" or "5 грн" don't match)
SIZE_RE = re.compile(rf"({NUM})\s*({UNIT_ALT}){NOT_LETTER}", re.IGNORECASE)

# "280±5գր" -> "280գր"   (the 5 is a tolerance, not the size)
TOL_WITH_UNIT_RE = re.compile(rf"({NUM})\s*±\s*{NUM}\s*({UNIT_ALT}){NOT_LETTER}", re.IGNORECASE)
# "400գր±3%" / "300գր±15գր" -> "400գր" / "300գր"
TOL_RE = re.compile(rf"±\s*{NUM}\s*(?:%|(?:{UNIT_ALT}){NOT_LETTER})?", re.IGNORECASE)
# multipack "5x6գր" -> "30գր"
MULT_RE = re.compile(rf"(\d+)\s*[xXхХ×]\s*({NUM})\s*({UNIT_ALT}){NOT_LETTER}", re.IGNORECASE)

# A name ending in a bare "հտ" / "шт" (no number) means "sold per piece": 1 piece.
TRAILING_PIECE_RE = re.compile(r"(?:^|\s)(?:հտ|шт)\.?\s*$", re.IGNORECASE)


def _clean_name(name):
    """Remove tolerances ('±5գր', '±3%') and expand multipacks ('5x6գր' -> '30գր')."""
    name = TOL_WITH_UNIT_RE.sub(r"\1\2", name)
    name = TOL_RE.sub("", name)
    return MULT_RE.sub(
        lambda m: f"{int(m.group(1)) * float(m.group(2).replace(',', '.')):g}{m.group(3)}", name)


def parse_name_size(name):
    """Extract grams / ml / pieces from a product name like 'Լավաշ 4հտ 400գր±3%'."""
    name = _clean_name(name)
    out = {"grams": None, "ml": None, "pieces": None}
    for num, unit in SIZE_RE.findall(name):
        v = float(num.replace(",", "."))
        kind, mult = UNITS[unit.lower()]
        key = {"g": "grams", "ml": "ml", "pc": "pieces"}[kind]
        out[key] = v * mult
    if out["pieces"] is None and TRAILING_PIECE_RE.search(name):
        out["pieces"] = 1.0
    return out


def pack_size(item):
    """Work out the package size of an API item.

    Returns a dict: grams, ml, pieces, source.
    source tells you how the size was found, so guesses can be audited:
      api_kg            loose item, price is per kg
      api               weight in grams from the API (agrees with the name or no name size)
      api_differs       API grams differ from the grams in the name (drained weight?)
      api_ml, api_ml_differs   same, for millilitres
      api_pc            piece count from the API
      api_no_confirmed  measure 'NO', weight is grams and the name confirms it
      api_no_ml_confirmed  measure 'NO', weight is ml (e.g. 1000 for '1լ') and the name confirms it
      api_no_unverified measure 'NO', weight taken as grams, nothing to confirm it
      api_no_piece      measure 'NO' with weight 1: one piece, not 1 gram
      name_parse        size taken from the product name
      conflict          measure 'NO': weight and name disagree, review by hand
      unknown           no size found
    """
    w, m = item.get("weight"), item.get("weightMeasure")
    named = parse_name_size(item["name"])

    def out(g=None, ml=None, pc=None, src=""):
        return {"grams": g, "ml": ml, "pieces": pc, "source": src}

    if item.get("isKilogram"):
        return out(g=1000.0, src="api_kg")  # price is per kg
    if w and m == "G":
        differs = named["grams"] is not None and abs(named["grams"] - w) >= 1
        return out(g=float(w), pc=named["pieces"], src="api_differs" if differs else "api")
    if w and m == "ML":
        differs = named["ml"] is not None and abs(named["ml"] - w) >= 1
        return out(ml=float(w), pc=named["pieces"], src="api_ml_differs" if differs else "api_ml")
    if w and m == "PC":
        return out(pc=float(w), src="api_pc")
    if w and m == "NO":
        if w == 1:  # weight 1 on a non-kg item is a unit count, not 1 gram
            if named["grams"] or named["ml"]:
                return out(named["grams"], named["ml"], named["pieces"], "name_parse")
            return out(pc=1.0, src="api_no_piece")
        if named["grams"] is not None and abs(named["grams"] - w) < 1:
            return out(g=float(w), pc=named["pieces"], src="api_no_confirmed")
        if named["ml"] is not None and abs(named["ml"] - w) < 1:
            return out(ml=float(w), pc=named["pieces"], src="api_no_ml_confirmed")
        if named["grams"] is None and named["ml"] is None:
            return out(g=float(w), pc=named["pieces"], src="api_no_unverified")
        return out(src="conflict")
    if named["grams"] or named["ml"] or named["pieces"]:
        return out(named["grams"], named["ml"], named["pieces"], "name_parse")
    return out(src="unknown")


def unit_prices(item):
    """Our own unit prices, from the price actually paid (discounted if there is a discount)."""
    discounted = item.get("discountedPrice") or 0
    price = round(discounted if discounted > 0 else item["price"])
    s = pack_size(item)
    return {
        "effective_price": price,
        "price_per_kg": round(price / s["grams"] * 1000) if s["grams"] else None,
        "price_per_l": round(price / s["ml"] * 1000) if s["ml"] else None,
        "price_per_piece": round(price / s["pieces"], 1) if s["pieces"] else None,
        **s,
    }


def _item(name, weight=0, measure=None, kg=False, price=1000.0, disc=0.0):
    return {"name": name, "weight": weight, "weightMeasure": measure,
            "isKilogram": kg, "price": price, "discountedPrice": disc}


def _run_tests():
    # Armenian (real names from the data)
    assert parse_name_size("Տորթ «Վինտաժ» 1400գր")["grams"] == 1400
    assert parse_name_size("Լավաշ «Կախարդական» չոր 4հտ 400գր±3%") == {
        "grams": 400, "ml": None, "pieces": 4}
    assert parse_name_size("Բագետ ավանդական 1հտ") == {
        "grams": None, "ml": None, "pieces": 1}
    assert parse_name_size("Չորահացի ձողիկներ «Մարիո Ֆոնգո»մինի,ձիթ.ձեթ100գր")["grams"] == 100
    assert parse_name_size("Թխվածքաբլիթ «Ֆիթնես Քուք» քունջութով ա/շ 200գ")["grams"] == 200
    assert parse_name_size("Շերտավոր խմոր 1կգ")["grams"] == 1000
    assert parse_name_size("Լավաշ «Ավան» չոր 4հտ")["pieces"] == 4
    assert parse_name_size("Ձմերուկ մինի հտ")["pieces"] == 1       # bare trailing 'հտ'
    # tolerances are not sizes
    assert parse_name_size("Հացի ձողիկ «Գոլդեն Բեյքրի» քունջութով 280±5գր")["grams"] == 280
    assert parse_name_size("Տորտիլյա «Պանո» 300գր±15գր")["grams"] == 300
    assert parse_name_size("Հաց «Պիկանտ Համ» մինի, տեսականի 370±20գր")["grams"] == 370
    assert parse_name_size("Հացի ձողիկ «Պիկանտ Համ» քունջութ 120±10գ")["grams"] == 120
    # multipacks
    assert parse_name_size("Ձողիկներ կաթի համար «Դոլֆին» շոկոլադե միջուկով 5x6գր")["grams"] == 30
    assert parse_name_size("Սերուցք «Պրեզիդենտ» 10x10գր")["grams"] == 100
    # Russian
    assert parse_name_size("Молоко 3.2% 1л")["ml"] == 1000
    assert parse_name_size("Кефир 500 мл")["ml"] == 500
    assert parse_name_size("Сыр Российский 250г")["grams"] == 250
    assert parse_name_size("Мука 2кг")["grams"] == 2000
    assert parse_name_size("Яйца 10шт")["pieces"] == 10
    assert parse_name_size("Масло 0,5л")["ml"] == 500
    assert parse_name_size("Елка зеленая 210см") == {
        "grams": None, "ml": None, "pieces": None}

    # whole-item logic
    u = unit_prices(_item("Ель 120см", 1, "PC", price=4590.0))
    assert u["source"] == "api_pc" and u["price_per_piece"] == 4590

    u = unit_prices(_item("Չորահաց 200գր", price=2690.0, disc=2289.997))
    assert u["effective_price"] == 2290 and u["price_per_kg"] == 11450

    # weight 1 + measure NO on a per-piece product: ONE PIECE, never 1 gram
    u = unit_prices(_item("Ավոկադո հտ", 1, "NO", price=455.0, disc=385.0))
    assert u["source"] == "api_no_piece" and u["price_per_piece"] == 385
    assert u["price_per_kg"] is None

    # loose item sold by kg
    u = unit_prices(_item("Խնձոր կգ", 1, "NO", kg=True, price=515.0, disc=395.0))
    assert u["source"] == "api_kg" and u["price_per_kg"] == 395

    # no API weight, bare 'հտ' in the name
    u = unit_prices(_item("Ձմերուկ մինի հտ", 0, None, price=2190.0))
    assert u["source"] == "name_parse" and u["price_per_piece"] == 2190

    # canned goods: API weight differs from the name (drained weight?) -> flagged, API used
    u = unit_prices(_item("Թյունոս «Կալվո» ձիթայուղի մեջ 160գր", 104, "G", price=1760.0))
    assert u["source"] == "api_differs" and u["grams"] == 104 and u["price_per_kg"] == 16923

    # millilitres
    u = unit_prices(_item("Կաթ 1լ", 1000, "ML", price=590.0))
    assert u["source"] == "api_ml" and u["price_per_l"] == 590
    u = unit_prices(_item("Մարինացված վարունգ 1500մլ", 900, "ML", price=1690.0))
    assert u["source"] == "api_ml_differs" and u["ml"] == 900

    # NO with grams confirmed by the name
    u = unit_prices(_item("Տորթ «Դան Դեսերտ» 1000գր", 1000, "NO", price=4060.0))
    assert u["source"] == "api_no_confirmed" and u["price_per_kg"] == 4060
    # measure NO + weight in ml (milk 1 L): millilitres, not grams
    u = unit_prices(_item("Կաթ «Պարմալատ» ուլտրապաստերիզացված 3.5% 1լ", 1000, "NO", price=1390.0))
    assert u["source"] == "api_no_ml_confirmed" and u["ml"] == 1000 and u["price_per_l"] == 1390
    assert u["grams"] is None

    # per-piece item with an API weight: both grams and pieces
    u = unit_prices(_item("Տավարի քյաբաբ հտ", 200, "NO", price=890.0))
    assert u["source"] == "api_no_unverified" and u["grams"] == 200
    assert u["price_per_piece"] == 890 and u["price_per_kg"] == 4450

    # multipack that used to be a conflict
    u = unit_prices(_item("Ձողիկներ «Դոլֆին» 5x6գր", 30, "NO", price=445.0))
    assert u["source"] == "api_no_confirmed" and u["grams"] == 30

    # tolerance no longer causes a false api_differs
    u = unit_prices(_item("Հաց «Ֆիթնես Քուք» ձիթապտղով 400±12գր", 400, "G", price=720.0))
    assert u["source"] == "api" and u["price_per_kg"] == 1800
    print("sizes.py tests passed")


if __name__ == "__main__":
    _run_tests()
