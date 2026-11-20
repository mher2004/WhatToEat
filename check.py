"""Sanity checks on the latest raw scrape. Read-only: does not touch the database."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from sizes import unit_prices

LIMIT = 25  # rows shown per section

folder = sorted(Path("raw/yerevan_city").iterdir())[-1]
print("checking folder:", folder)

items, per_category, cats_by_id = [], Counter(), defaultdict(list)
for f in sorted(folder.glob("cat*_p*.json")):
    cat = f.name.split("_")[0]
    lst = json.loads(f.read_text(encoding="utf-8"))["data"]["list"]
    per_category[cat] += len(lst)
    for it in lst:
        cats_by_id[it["id"]].append(cat)
    items += lst


def show(title, rows, fmt):
    print(f"\n--- {title} ({len(rows)}) ---")
    for r in rows[:LIMIT]:
        print(fmt(r))


def line(i):
    return f'{i["name"]} | price {i["price"]} | weight {i.get("weight")} {i.get("weightMeasure")}'


def effective(i):
    d = i.get("discountedPrice") or 0
    return d if d > 0 else i["price"]


print("items per category:", dict(per_category))
print("items:", len(items), "| unique ids:", len(cats_by_id))
print("ids in more than one category:", sum(1 for c in cats_by_id.values() if len(set(c)) > 1))
print("ids repeated inside one category:", sum(1 for c in cats_by_id.values() if len(c) > len(set(c))))
print("weightMeasure values:", Counter(i.get("weightMeasure") for i in items))

results = [(i, unit_prices(i)) for i in items]
print("size sources:", dict(Counter(u["source"] for _, u in results)))

# Sizes that need a human look
for src in ("conflict", "unknown", "api_no_unverified", "api_ml_differs"):
    show(f"source = {src}", [i for i, u in results if u["source"] == src], line)
show("source = api_differs (API grams differ from name grams)",
     [i for i, u in results if u["source"] == "api_differs"], line)
show("weightMeasure '#'", [i for i in items if i.get("weightMeasure") == "#"], line)
show("weightMeasure 'ML' sample", [i for i in items if i.get("weightMeasure") == "ML"], line)

# Does the site's productPricePerUnit (per kg) agree with price / weight?
same_regular = same_discounted = 0
rest = []
for i in items:
    ppu, w = i.get("productPricePerUnit"), i.get("weight")
    if i.get("weightMeasure") == "G" and w and ppu:
        if abs(i["price"] / w * 1000 - ppu) <= 2:
            same_regular += 1
        elif abs(effective(i) / w * 1000 - ppu) <= 2:
            same_discounted += 1
        else:
            rest.append((i, round(effective(i) / w * 1000), ppu))
print("\nper-kg check: matches regular price:", same_regular,
      "| matches discounted price:", same_discounted, "| unexplained:", len(rest))
show("unexplained per-kg mismatches", rest,
     lambda r: f'{r[0]["name"]} | price {r[0]["price"]} disc {r[0].get("discountedPrice")} '
               f'| weight {r[0]["weight"]} | ours {r[1]} | site {r[2]}')

# Unit mistakes show up as absurd prices
by_kg = sorted(((u["price_per_kg"], i["name"]) for i, u in results if u["price_per_kg"]), reverse=True)
show("highest price per kg", by_kg, lambda r: f"{r[0]:>9} | {r[1]}")
show("lowest price per kg", by_kg[::-1], lambda r: f"{r[0]:>9} | {r[1]}")
by_l = sorted(((u["price_per_l"], i["name"]) for i, u in results if u["price_per_l"]), reverse=True)
show("highest price per litre", by_l, lambda r: f"{r[0]:>9} | {r[1]}")

discounted = [i for i in items if (i.get("discountedPrice") or 0) > 0]
print(f"\ndiscounted items: {len(discounted)} of {len(items)}")
