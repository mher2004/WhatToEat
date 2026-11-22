"""Real shopping costs: turn 'amount needed' into actual products and whole packs.

For each ingredient we look at every matched product in the database (latest price, trusted size) and pick the
product + number of packs that covers the need for the least money. Loose items sold by weight (price per kg)
are bought in 100 g steps.
"""
import math
import statistics
from collections import defaultdict

from cost import ingredient_amount

BAD_SIZE = ("conflict", "unknown", "api_differs", "api_ml_differs", "api_no_unverified")
PANTRY_DEFAULT = ("salt", "black_pepper", "sunflower_oil")


def load_info(con, lang="hy"):
    col = "COALESCE(NULLIF(name_hy, ''), name_en)" if lang == "hy" else "name_en"
    return {i: (n, b, g) for i, n, b, g in
            con.execute(f"SELECT id, {col}, price_basis, grams_per_piece FROM ingredients")}


def build_catalog(con, info):
    """ingredient_id -> list of purchasable options {name, price, pack, loose, unit_price} (pack in kg / l / pc)."""
    cat = defaultdict(list)
    q = """SELECT pi.ingredient_id, r.name, r.pack_grams, r.pack_ml, r.pack_pieces, r.size_source, p.effective_price
           FROM product_ingredients pi
           JOIN products_raw r ON r.id = pi.product_id
           JOIN prices p ON p.product_id = r.id
           JOIN (SELECT product_id, MAX(id) mid FROM prices GROUP BY product_id) m ON p.id = m.mid"""
    for ing, name, g, ml, pc, src, price in con.execute(q):
        if src in BAD_SIZE or not price:
            continue
        basis = info[ing][1]
        pack = {"kg": (g or 0) / 1000, "l": (ml or 0) / 1000, "pc": pc or 0}[basis]
        if pack <= 0:
            continue
        cat[ing].append(dict(name=name, price=price, pack=pack, loose=(src == "api_kg"),
                             unit_price=price / pack))
    for ing, opts in cat.items():           # drop outlier unit prices (same rule as ingredient_prices)
        med = statistics.median(o["unit_price"] for o in opts)
        cat[ing] = [o for o in opts if med / 30 <= o["unit_price"] <= med * 3] or opts
    return cat


def needs_of(recipes, info):
    """Aggregate the ingredient amounts (in each ingredient's price basis) of several recipes."""
    need = defaultdict(float)
    for r in recipes:
        for ing, qty, unit, _ in r["lines"]:
            _, basis, gpp = info[ing]
            a = ingredient_amount(qty, unit, basis, gpp)
            if a is not None:
                need[ing] += a
    return need


def cheapest_buy(options, need):
    best = None
    for o in options:
        if o["loose"]:
            amount = math.ceil(need / 0.1 - 1e-9) * 0.1
            n, cost = amount / o["pack"], o["price"] * amount / o["pack"]
        else:
            n = math.ceil(need / o["pack"] - 1e-9)
            cost = n * o["price"]
        leftover = n * o["pack"] - need
        key = (cost, leftover)
        if best is None or key < best[0]:
            best = (key, dict(option=o, n=n, cost=cost, leftover=leftover))
    return best[1]


def shopping(catalog, info, recipes, pantry=PANTRY_DEFAULT):
    """Return {lines, pay, consumed, leftover_value, pantry, unpriced} for a set of recipes bought together."""
    need = needs_of(recipes, info)
    lines, pay, consumed, pantry_used, unpriced = [], 0.0, 0.0, [], []
    for ing, amt in sorted(need.items(), key=lambda x: info[x[0]][0]):
        if ing in pantry:
            pantry_used.append(ing)
            continue
        if not catalog.get(ing):
            unpriced.append(ing)
            continue
        b = cheapest_buy(catalog[ing], amt)
        o = b["option"]
        used_value = o["unit_price"] * amt
        pay += b["cost"]
        consumed += used_value
        lines.append(dict(ing=ing, label=info[ing][0], basis=info[ing][1], need=amt, name=o["name"],
                          n=b["n"], pack=o["pack"], cost=b["cost"], leftover=b["leftover"], loose=o["loose"]))
    return dict(lines=lines, pay=round(pay), consumed=round(consumed),
                leftover_value=round(pay - consumed), pantry=pantry_used, unpriced=unpriced)


def fmt_amount(x, basis, units=None):
    u = units or {"g": "g", "ml": "ml", "pc": "pc"}
    if basis == "kg":
        return f"{x * 1000:.0f} {u['g']}"
    if basis == "l":
        return f"{x * 1000:.0f} {u['ml']}"
    return f"{x:g} {u['pc']}"
