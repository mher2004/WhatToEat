"""Meal planner: people + meals + daily budget -> best day menus, steps and shopping list.
Armenian by default; use --lang en for English.

    python3 plan.py --people 2 --meals նախաճաշ,ճաշ,ընթրիք --budget 2500
    python3 plan.py --people 4 --meals ճաշ,ընթրիք --budget 4000 --days 3 --steps
    python3 plan.py --people 2 --meals ընթրիք --budget 900 --all     # every dinner that fits
    python3 plan.py --people 2 --budget 2500 --pick 2 --steps --real
Budget is per day for the whole group (AMD / դրամ).
"""
import argparse
import itertools
import json
import sqlite3

from cost import recipe_cost
from i18n import TEXT, parse_meals
from shop import PANTRY_DEFAULT, build_catalog, fmt_amount, load_info, shopping

# Ingredients that define the "feel" of a dish; two dishes sharing one of these feel repetitive.
MAIN = {"potato", "rice", "pasta", "bulgur", "buckwheat", "lentils", "beans", "egg", "chicken_thigh",
        "chicken_breast", "mince", "pork", "beef", "sausage", "cabbage", "cottage_cheese", "oats", "flour"}


def load_recipes(con, people, mode, lang):
    out = {}
    for rid, name, name_hy, meals, tags, steps, steps_hy in con.execute(
            "SELECT id, name, name_hy, meals, tags, steps, steps_hy FROM recipes"):
        c = recipe_cost(con, rid, people, mode)
        if c["missing"]:           # can't be priced reliably -> skip
            continue
        hy = lang == "hy"
        out[rid] = dict(id=rid, name=(name_hy if hy and name_hy else name), meals=json.loads(meals),
                        tags=json.loads(tags),
                        steps=json.loads(steps_hy) if hy and steps_hy else json.loads(steps),
                        cost=c["total"], lines=c["lines"], ings={l[0] for l in c["lines"]})
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
    plans = []
    for combo in itertools.product(*pools):
        if len({r["id"] for r in combo}) < len(combo):
            continue                                  # same dish twice in one day
        if sum(r["cost"] for r in combo) <= budget:
            plans.append(combo)
    plans.sort(key=lambda c: -score(c, budget))
    chosen = []
    for p in plans:
        if pay_fn and pay_fn(p) > budget:      # --real: the actual shop bill must fit the budget
            continue
        if all(sum(a["id"] != b["id"] for a, b in zip(p, q)) >= 2 or len(p) == 1 for q in chosen):
            chosen.append(p)
        if len(chosen) == top:
            break
    return chosen if pay_fn else (chosen or plans[:top])


def show_shopping(sh, title, T):
    print(f"\n{title}")
    print(f"  {T['col_ing']:<28}{T['col_need']:>9}   {T['col_buy']}")
    for l in sh["lines"]:
        pack = fmt_amount(l["pack"], l["basis"], T["units"])
        what = (f"{l['name'][:46]}  {T['loose']}" if l["loose"] else f"{l['n']:g} x {l['name'][:46]}  [{pack}]")
        print(f"  {l['label']:<28}{fmt_amount(l['need'], l['basis'], T['units']):>9}   {what}  = {l['cost']:.0f} {T['currency']}")
    if sh["pantry"]:
        print("  " + T["home"], ", ".join(sh["pantry_labels"]))
    if sh["unpriced"]:
        print("  " + T["noprice"], ", ".join(sh["unpriced"]))
    print("  " + T["pay"].format(pay=sh["pay"], left=sh["leftover_value"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", type=int, required=True, help="number of people / մարդկանց քանակ")
    ap.add_argument("--meals", default="նախաճաշ,ճաշ,ընթրիք", help="e.g. նախաճաշ,ճաշ,ընթրիք or breakfast,lunch,dinner")
    ap.add_argument("--budget", type=int, required=True, help="per day, whole group, in dram / օրական բյուջե")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--top", type=int, default=3, help="how many menu options to show")
    ap.add_argument("--pick", type=int, default=1, help="which option to show steps + shopping list for")
    ap.add_argument("--real", action="store_true", help="the real shop bill (whole packs) must fit the budget")
    ap.add_argument("--pantry", default=",".join(PANTRY_DEFAULT),
                    help="ingredient ids you already have at home (comma separated, or 'none')")
    ap.add_argument("--prices", default="p25", choices=["p25", "median"])
    ap.add_argument("--steps", action="store_true", help="print cooking instructions")
    ap.add_argument("--all", action="store_true", help="list every recipe that fits each meal's share")
    ap.add_argument("--sides", action="store_true", help="allow side dishes as a main")
    ap.add_argument("--lang", default="hy", choices=["hy", "en"])
    a = ap.parse_args()
    T = TEXT[a.lang]
    meals = parse_meals(a.meals)
    pantry = () if a.pantry == "none" else tuple(x.strip() for x in a.pantry.split(",") if x.strip())

    con = sqlite3.connect("whattoeat.db")
    recipes = load_recipes(con, a.people, a.prices, a.lang)
    if not recipes:
        raise SystemExit("No priced recipes in the database. Run:  python3 match.py  then  python3 recipes.py")
    info = load_info(con, a.lang)
    catalog = build_catalog(con, info)

    def shop_for(combo):
        sh = shopping(catalog, info, combo, pantry)
        sh["pantry_labels"] = [info[i][0] for i in sh["pantry"]]
        return sh

    if a.all:
        share = a.budget / len(meals)
        for m in meals:
            print("\n" + T["recipes_up_to"].format(meal=T["meals"][m], share=f"{share:.0f}", people=a.people))
            for r in sorted((r for r in recipes.values() if m in r["meals"] and r["cost"] <= share),
                            key=lambda r: r["cost"]):
                print(f"  {r['cost']:>6}  {r['name']}")
        return

    pantry_txt = ", ".join(info[i][0] for i in pantry if i in info) or T["none"]
    if a.days == 1:
        options = day_plans(recipes, meals, a.budget, top=a.top, include_sides=a.sides,
                            pay_fn=(lambda c: shop_for(c)["pay"]) if a.real else None)
        if not options:
            cheapest = sum(min(r["cost"] for r in recipes.values() if m in r["meals"]) for m in meals)
            print(T["nofit"].format(budget=a.budget, people=a.people, cheapest=cheapest,
                                    real=T["real"] if a.real else ""))
            return
        print(T["hdr"].format(people=a.people, budget=a.budget, pantry=pantry_txt))
        pick = min(max(a.pick, 1), len(options))
        for n, combo in enumerate(options, 1):
            sh = shop_for(combo)
            print("\n=== " + T["option"].format(n=n, eaten=sum(r["cost"] for r in combo), shop=sh["pay"])
                  + (T["shown"] if n == pick else ""))
            for m, r in zip(meals, combo):
                print(f"  {T['meals'][m]:<9} {r['cost']:>6}  {r['name']}")
        days = [options[pick - 1]]
        label = T["option_label"].format(n=pick)
    else:
        days, used = [], set()
        for d in range(a.days):
            opts = day_plans(recipes, meals, a.budget, exclude=used, top=1, include_sides=a.sides)
            if not opts:
                opts = day_plans(recipes, meals, a.budget, top=1, include_sides=a.sides)
            if not opts:
                print(T["day_nofit"].format(d=d + 1, budget=a.budget))
                break
            days.append(opts[0])
            used |= {r["id"] for r in opts[0]}
        for d, combo in enumerate(days, 1):
            print("\n=== " + T["day_eaten"].format(d=d, eaten=sum(r["cost"] for r in combo)) + " ===")
            for m, r in zip(meals, combo):
                print(f"  {T['meals'][m]:<9} {r['cost']:>6}  {r['name']}")
        label = T["label_all"].format(n=len(days))

    if a.steps:
        for d, combo in enumerate(days, 1):
            for m, r in zip(meals, combo):
                who = (T["day"].format(d=d) + " " if len(days) > 1 else "") + T["meals"][m] + ": "
                print("\n--- " + T["steps_for"].format(who=who, name=r["name"], people=a.people) + " ---")
                for i, s in enumerate(r["steps"], 1):
                    print(f"  {i}. {s}")
    show_shopping(shop_for([r for c in days for r in c]), T["shoplist"].format(label=label), T)
    if a.days > 1:
        print("  " + T["budget_days"].format(n=len(days), b=a.budget * len(days)))


if __name__ == "__main__":
    main()
