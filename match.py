"""Map every product in whattoeat.db to a canonical ingredient and price the ingredients.

Usage:
    python3 match.py              # match, save to DB, print coverage
    python3 match.py --unmapped   # also write unmapped_report.txt (most frequent words first)
    python3 match.py --samples    # write match_samples.txt: random products per ingredient to eyeball
"""
import random
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict

from ingredients import ANY_EXCLUDE, GLOBAL_EXCLUDE, RAW_EXCLUDE, all_ingredients

BRAND = re.compile(r"«[^»]*»|\([^)]*\)")
GLOBAL_EXC = [re.compile(p) for p in GLOBAL_EXCLUDE + ANY_EXCLUDE]

SCHEMA = """
DROP TABLE IF EXISTS ingredients;
CREATE TABLE ingredients (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_hy TEXT NOT NULL,
  price_basis TEXT NOT NULL, grams_per_piece REAL
);
CREATE TABLE IF NOT EXISTS product_ingredients (
  product_id INTEGER PRIMARY KEY REFERENCES products_raw(id),
  ingredient_id TEXT NOT NULL REFERENCES ingredients(id)
);
CREATE TABLE IF NOT EXISTS ingredient_prices (
  ingredient_id TEXT PRIMARY KEY REFERENCES ingredients(id),
  basis TEXT NOT NULL, n_products INTEGER NOT NULL,
  min_price REAL, median_price REAL, max_price REAL,   -- AMD per kg / per litre / per piece
  computed_at TEXT NOT NULL
);
"""


def clean(name):
    return BRAND.sub(" ", name).lower()


RAW_EXC = [re.compile(p) for p in RAW_EXCLUDE]
VEG = "1926"


def match(name, category, ingredients):
    n = clean(name)
    if any(p.search(n) for p in GLOBAL_EXC):
        return None
    if category == VEG and any(p.search(name.lower()) for p in RAW_EXC):
        return None
    for ing in ingredients:
        if ing["cats"] and category not in ing["cats"]:
            continue
        if any(p.search(n) for p in ing["exc"]):
            continue
        if any(p.search(n) for p in ing["inc"]):
            return ing["id"]
    return None


def main():
    ings = all_ingredients()
    con = sqlite3.connect("whattoeat.db")
    con.executescript(SCHEMA)
    con.execute("DELETE FROM ingredients")
    con.executemany("INSERT INTO ingredients VALUES (?,?,?,?,?)",
                    [(i["id"], i["en"], i["hy"], i["basis"], i["gpp"]) for i in ings])

    rows = con.execute("SELECT id, name, category_id FROM products_raw").fetchall()
    con.execute("DELETE FROM product_ingredients")
    mapped, unmapped = {}, []
    for pid, name, cat in rows:
        ing = match(name, cat, ings)
        if ing:
            mapped[pid] = ing
        else:
            unmapped.append((pid, name, cat))
    con.executemany("INSERT INTO product_ingredients VALUES (?,?)", list(mapped.items()))

    # ---- ingredient prices: latest price of each product, junk removed ----
    # Dropped: products whose size could not be trusted, and per-unit outliers
    # (above 3x the median: gourmet/tiny packs; below median/30: likely wrong sizes).
    BAD_SIZE = ("conflict", "unknown", "api_differs", "api_ml_differs", "api_no_unverified")
    latest = {}
    for pid, kg, l, pc, src in con.execute(
            """SELECT p.product_id, p.price_per_kg, p.price_per_l, p.price_per_piece, r.size_source
               FROM prices p
               JOIN (SELECT product_id, MAX(id) mid FROM prices GROUP BY product_id) m ON p.id = m.mid
               JOIN products_raw r ON r.id = p.product_id"""):
        latest[pid] = ({"kg": kg, "l": l, "pc": pc}, src)
    by_ing = defaultdict(list)
    for pid, ing in mapped.items():
        by_ing[ing].append(pid)
    basis = {i["id"]: i["basis"] for i in ings}
    con.execute("DROP TABLE IF EXISTS ingredient_prices")
    con.execute("""CREATE TABLE ingredient_prices (
        ingredient_id TEXT PRIMARY KEY REFERENCES ingredients(id),
        basis TEXT NOT NULL, n_products INTEGER NOT NULL, n_used INTEGER NOT NULL,
        min_price REAL, p25_price REAL, median_price REAL, max_price REAL,  -- AMD per kg / litre / piece
        computed_at TEXT NOT NULL)""")
    now = con.execute("SELECT MAX(scraped_at) FROM prices").fetchone()[0]
    for ing, pids in by_ing.items():
        vals = sorted(latest[p][0][basis[ing]] for p in pids
                      if p in latest and latest[p][1] not in BAD_SIZE and latest[p][0][basis[ing]])
        if not vals:
            continue
        med = statistics.median(vals)
        kept = [v for v in vals if med / 30 <= v <= med * 3] or vals
        p25 = statistics.quantiles(kept, n=4)[0] if len(kept) >= 4 else kept[0]
        con.execute("INSERT INTO ingredient_prices VALUES (?,?,?,?,?,?,?,?,?)",
                    (ing, basis[ing], len(pids), len(kept), min(kept), p25,
                     statistics.median(kept), max(kept), now))
    con.commit()

    food_cats = {"1923", "22", "6", "1927", "7", "29", "27", "1928", "1926", "25", "26"}
    in_food = [r for r in rows if r[2] in food_cats]
    print(f"products: {len(rows)} | matched: {len(mapped)} ({len(mapped)/len(rows):.0%}) "
          f"| ingredients used: {len(by_ing)} of {len(ings)}")
    per_cat_total = Counter(c for _, _, c in rows)
    per_cat_map = Counter(c for pid, _, c in rows if pid in mapped)
    for c in sorted(per_cat_total, key=lambda x: -per_cat_total[x]):
        print(f"  cat {c:>5}: {per_cat_map[c]:>4}/{per_cat_total[c]:<4} matched")
    print("ingredients with no products:", [i["id"] for i in ings if i["id"] not in by_ing])

    if "--unmapped" in sys.argv:
        word = re.compile(r"[а-яёա-ֆa-z]{3,}")
        by_cat = defaultdict(Counter)
        for _, name, cat in unmapped:
            for w in set(word.findall(clean(name))):
                by_cat[cat][w[:6]] += 1
        with open("unmapped_report.txt", "w", encoding="utf-8") as f:
            for cat, cnt in by_cat.items():
                f.write(f"\n=== cat {cat}: {sum(1 for u in unmapped if u[2]==cat)} unmapped\n")
                f.write(", ".join(f"{w}:{n}" for w, n in cnt.most_common(70)) + "\n")
            f.write("\n\n--- 40 random unmapped names per category ---\n")
            random.seed(0)
            for cat in by_cat:
                names = [n for _, n, c in unmapped if c == cat]
                f.write(f"\n# {cat}\n" + "\n".join(random.sample(names, min(40, len(names)))) + "\n")
        print("wrote unmapped_report.txt")

    if "--samples" in sys.argv:
        names = {pid: n for pid, n, _ in rows}
        random.seed(1)
        with open("match_samples.txt", "w", encoding="utf-8") as f:
            for ing, pids in sorted(by_ing.items()):
                f.write(f"\n## {ing} ({len(pids)})\n")
                for p in random.sample(pids, min(6, len(pids))):
                    f.write(f"  {names[p]}\n")
        print("wrote match_samples.txt")


if __name__ == "__main__":
    main()
