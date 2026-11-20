"""Recipe cost from live ingredient prices.

    python3 cost.py                 # cost of every recipe for 2 people, cheapest first
    python3 cost.py 4 median        # 4 people, use median prices instead of p25

cost = sum over ingredients of (amount needed) x (price per kg / litre / piece).
This is the *proportional* cost (what you actually eat). The real shopping cost, which rounds up to
whole packs, comes later with the planner.
"""
import json
import sqlite3
import sys


def ingredient_amount(qty, unit, basis, gpp):
    """Convert a recipe quantity (g/ml/pc) into the price basis (kg, l or pc)."""
    if basis == "kg":
        if unit in ("g", "ml"):          # liquids ~ 1 g/ml
            return qty / 1000
        if gpp:
            return qty * gpp / 1000      # pieces -> kg
    elif basis == "l":
        if unit in ("g", "ml"):
            return qty / 1000
    elif basis == "pc":
        if unit == "pc":
            return qty
        if gpp:
            return qty / gpp             # grams -> pieces
    return None


def recipe_cost(con, recipe_id, people, mode="p25"):
    col = {"p25": "p25_price", "median": "median_price"}[mode]
    servings = con.execute("SELECT servings FROM recipes WHERE id=?", (recipe_id,)).fetchone()[0]
    scale = people / servings
    total, lines, missing = 0.0, [], []
    for ing, qty, unit, staple, basis, gpp, price in con.execute(
            f"""SELECT ri.ingredient_id, ri.quantity, ri.unit, ri.is_staple, i.price_basis, i.grams_per_piece,
                       p.{col}
                FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
                LEFT JOIN ingredient_prices p ON p.ingredient_id = ri.ingredient_id
                WHERE ri.recipe_id = ?""", (recipe_id,)):
        amount = ingredient_amount(qty * scale, unit, basis, gpp)
        if price is None or amount is None:
            missing.append(ing)
            continue
        c = amount * price
        total += c
        lines.append((ing, qty * scale, unit, round(c)))
    return {"total": round(total), "per_person": round(total / people), "lines": lines, "missing": missing}


def main():
    people = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    mode = sys.argv[2] if len(sys.argv) > 2 else "p25"
    con = sqlite3.connect("whattoeat.db")
    rows = []
    for rid, name, meals in con.execute("SELECT id, name, meals FROM recipes"):
        c = recipe_cost(con, rid, people, mode)
        rows.append((c["per_person"], c["total"], name, "/".join(json.loads(meals)), c["missing"]))
    print(f"{people} people, {mode} prices (AMD)\\n".replace("\\n", "\n"))
    print(f"{'per person':>10} {'total':>7}  meal              recipe")
    for pp, total, name, meals, missing in sorted(rows):
        flag = f"   !! no price: {', '.join(missing)}" if missing else ""
        print(f"{pp:>10} {total:>7}  {meals:<17} {name}{flag}")


if __name__ == "__main__":
    main()
