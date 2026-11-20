"""Meal planner: people + meals + daily budget -> best day menus, steps and shopping list.

    python3 plan.py --people 2 --meals breakfast,lunch,dinner --budget 2500
    python3 plan.py --people 4 --meals lunch,dinner --budget 4000 --days 3 --steps
    python3 plan.py --people 2 --meals dinner --budget 1000 --all     # every dinner that fits

Budget is per day for the whole group (AMD). Costs use p25 ingredient prices (--prices median to change).
"""
import argparse
import itertools
import json
import sqlite3
from collections import defaultdict

from cost import recipe_cost
from shop import build_catalog, fmt_amount, load_info, shopping, PANTRY_DEFAULT

# Ingredients that define the "feel" of a dish; two dishes sharing one of these feel repetitive.
MAIN = {"potato", "rice", "pasta", "bulgur", "buckwheat", "lentils", "beans", "egg", "chicken_thigh",
        "chicken_breast", "mince", "pork", "beef", "sausage", "cabbage", "cottage_cheese", "oats", "flour"}


def load_recipes(con, people, mode):
    out = {}
    for rid, name, name_hy, meals, tags, steps in con.execute(
            "SELECT id, name, name_hy, meals, tags, steps FROM recipes"):
        c = recipe_cost(con, rid, people, mode)
        if c["missing"]:           # can't be priced reliably -> skip
            continue
        ings = {l[0] for l in c["lines"]}
        out[rid] = dict(id=rid, name=name_hy or name, meals=json.loads(meals), tags=json.loads(tags),
                        steps=json.loads(steps), cost=c["total"], lines=c["lines"], ings=ings)
    return out


def score(combo, budget):
    """Higher is better: varied ingredients, no repeated main ingredient, spends sensibly."""
    mains = [r["ings"] & MAIN for r in combo]
    repeats = sum(len(a & b) for a, b in itertools.combinations(mains, 2))
    distinct = len(set().union(*[r["ings"] for r in combo]))
    cost = sum(r["cost"] for r in combo)
    return distinct - 3 * repeats - 1.5 * cost / budget


def day_plans(recipes, meals, budget, exclude=(), top=3, include_sides=False, pay_fn=None):
    pools = []
    for m in meals:
        pool = [r for r in recipes.values()
                if m in r["meals"] and r["id"] not in exclude and (include_sides or "side" not in r["tags"])]
        if not pool:
            return []
        pools.append(pool)
    cheapest = [min(r["cost"] for r in p) for p in pools]
    plans = []
    for combo in itertools.product(*pools):
        if len({r["id"] for r in combo}) < len(combo):
            continue                                  # same dish twice in one day
        if sum(r["cost"] for r in combo) <= budget:
            plans.append(combo)
    plans.sort(key=lambda c: -score(c, budget))
    # keep results diverse: don't show 3 plans that differ in a single meal only
    chosen = []
    for p in plans:
        if pay_fn and pay_fn(p) > budget:      # --real: the actual shop bill must fit the budget
            continue
        if all(sum(a["id"] != b["id"] for a, b in zip(p, q)) >= 2 or len(p) == 1 for q in chosen):
            chosen.append(p)
        if len(chosen) == top:
            break
    return chosen if pay_fn else (chosen or plans[:top])


def show_shopping(sh, title):
    print(f"\n{title}")
    print(f"  {'ingredient':<22}{'need':>8}   buy")
    for l in sh["lines"]:
        pack = fmt_amount(l["pack"], l["basis"])
        what = (f"{l['name'][:46]}  (loose, by weight)" if l["loose"]
                else f"{l['n']:g} x {l['name'][:46]}  [{pack}]")
        print(f"  {l['label']:<22}{fmt_amount(l['need'], l['basis']):>8}   {what}  = {l['cost']:.0f} AMD")
    if sh["pantry"]:
        print("  assumed at home (not bought):", ", ".join(sh["pantry"]))
    if sh["unpriced"]:
        print("  !! no price found for:", ", ".join(sh["unpriced"]))
    print(f"  --> pay at the shop: {sh['pay']} AMD, of which {sh['leftover_value']} AMD is leftover "
          f"you can use in later meals")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", type=int, required=True)
    ap.add_argument("--meals", default="breakfast,lunch,dinner")
    ap.add_argument("--budget", type=int, required=True, help="AMD per day, whole group")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--top", type=int, default=3, help="how many menu options to show")
    ap.add_argument("--pick", type=int, default=1, help="which option to show steps + shopping list for")
    ap.add_argument("--real", action="store_true", help="the real shop bill (whole packs) must fit the budget")
    ap.add_argument("--pantry", default=",".join(PANTRY_DEFAULT),
                    help="ingredients you already have at home (comma separated, or 'none')")
    ap.add_argument("--prices", default="p25", choices=["p25", "median"])
    ap.add_argument("--steps", action="store_true", help="print cooking instructions")
    ap.add_argument("--all", action="store_true", help="list every recipe that fits each meal's share")
    ap.add_argument("--sides", action="store_true", help="allow side dishes as a main")
    a = ap.parse_args()
    meals = [m.strip() for m in a.meals.split(",")]
    pantry = () if a.pantry == "none" else tuple(x.strip() for x in a.pantry.split(",") if x.strip())

    con = sqlite3.connect("whattoeat.db")
    recipes = load_recipes(con, a.people, a.prices)
    info = load_info(con)
    catalog = build_catalog(con, info)
    pay_of = lambda combo: shopping(catalog, info, combo, pantry)["pay"]

    if a.all:
        share = a.budget / len(meals)
        for m in meals:
            print(f"\n{m}: recipes up to {share:.0f} AMD for {a.people} people")
            for r in sorted((r for r in recipes.values() if m in r["meals"] and r["cost"] <= share),
                            key=lambda r: r["cost"]):
                print(f"  {r['cost']:>6}  {r['name']}")
        return

    if a.days == 1:
        options = day_plans(recipes, meals, a.budget, top=a.top, include_sides=a.sides,
                            pay_fn=pay_of if a.real else None)
        if not options:
            cheapest = sum(min(r["cost"] for r in recipes.values() if m in r["meals"]) for m in meals)
            print(f"Nothing fits {a.budget} AMD for {a.people} people"
                  f"{' as a real shop bill' if a.real else ''}. Cheapest possible day (food eaten): {cheapest} AMD.")
            return
        print(f"{a.people} people, {a.budget} AMD/day. 'eaten' = typical price of the food used; "
              f"'shop' = what you really pay for whole packs (pantry: {', '.join(pantry) or 'none'}).")
        for n, combo in enumerate(options, 1):
            sh = shopping(catalog, info, combo, pantry)
            mark = "   <-- shown below" if n == a.pick else ""
            print(f"\n=== Option {n}: eaten {sum(r['cost'] for r in combo)} AMD | shop {sh['pay']} AMD{mark}")
            for m, r in zip(meals, combo):
                print(f"  {m:<9} {r['cost']:>6}  {r['name']}")
        pick = min(max(a.pick, 1), len(options))
        days = [options[pick - 1]]
        label = f"Option {pick}"
    else:
        days, used = [], set()
        for d in range(a.days):
            opts = day_plans(recipes, meals, a.budget, exclude=used, top=1, include_sides=a.sides)
            if not opts:
                opts = day_plans(recipes, meals, a.budget, top=1, include_sides=a.sides)
            if not opts:
                print(f"Day {d + 1}: nothing fits {a.budget} AMD.")
                break
            days.append(opts[0])
            used |= {r["id"] for r in opts[0]}
        for d, combo in enumerate(days, 1):
            print(f"\n=== Day {d}: eaten {sum(r['cost'] for r in combo)} AMD ===")
            for m, r in zip(meals, combo):
                print(f"  {m:<9} {r['cost']:>6}  {r['name']}")
        label = f"all {len(days)} days (bought together)"

    if a.steps:
        for d, combo in enumerate(days, 1):
            for m, r in zip(meals, combo):
                print(f"\n--- {('Day %d ' % d) if len(days) > 1 else ''}{m}: {r['name']} (for {a.people}) ---")
                for i, s in enumerate(r["steps"], 1):
                    print(f"  {i}. {s}")
    show_shopping(shopping(catalog, info, [r for c in days for r in c], pantry), f"Shopping list for {label}:")
    if a.days > 1:
        print(f"  (budget for {len(days)} days: {a.budget * len(days)} AMD)")


if __name__ == "__main__":
    main()
