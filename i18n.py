"""Interface texts (Armenian default, English available) and meal-name parsing."""
MEAL_ALIASES = {
    "նախաճաշ": "breakfast", "ճաշ": "lunch", "ընթրիք": "dinner",
    "завтрак": "breakfast", "обед": "lunch", "ужин": "dinner",
    "breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner",
}


def parse_meals(text):
    out = []
    for m in text.split(","):
        key = m.strip().lower()
        if key not in MEAL_ALIASES:
            raise SystemExit(f"Unknown meal {m!r}. Use: նախաճաշ, ճաշ, ընթրիք (or breakfast, lunch, dinner)")
        out.append(MEAL_ALIASES[key])
    return out


TEXT = {
 "hy": dict(
    meals={"breakfast": "նախաճաշ", "lunch": "ճաշ", "dinner": "ընթրիք"},
    units={"g": "գ", "ml": "մլ", "pc": "հատ"}, currency="դրամ", none="ոչինչ",
    hdr="{people} հոգի, օրական {budget} դրամ։ «ուտելու արժեք»՝ օգտագործված սննդի սովորական գինը, "
        "«խանութում»՝ ամբողջ փաթեթների իրական գինը (տանն ունեք՝ {pantry})։",
    option="Տարբերակ {n}՝ ուտելու արժեք {eaten} դրամ | խանութում {shop} դրամ", shown="   <-- ներքևում",
    nofit="{budget} դրամ բյուջեն {people} հոգու համար չի բավարարում{real}։ "
          "Ամենաէժան օրը (ուտելու արժեքով)՝ {cheapest} դրամ։", real=" որպես խանութի իրական հաշիվ",
    day="Օր {d}", day_eaten="Օր {d}՝ ուտելու արժեք {eaten} դրամ", day_nofit="Օր {d}՝ {budget} դրամով ոչինչ չի բավարարում։",
    shoplist="Գնումների ցուցակ ({label})", col_ing="բաղադրիչ", col_need="պետք է", col_buy="գնել",
    loose="(կշռով)", home="տանն ունեք (չի գնվում)՝", noprice="!! գին չի գտնվել՝",
    pay="--> խանութում վճարում եք՝ {pay} դրամ, որից {left} դրամը ավելցուկ է հաջորդ ճաշերի համար",
    label_all="բոլոր {n} օրերը (գնվում են միասին)", option_label="Տարբերակ {n}",
    budget_days="(բյուջե {n} օրվա համար՝ {b} դրամ)", steps_for="{who}{name} ({people} հոգու համար)",
    recipes_up_to="{meal}. բաղադրատոմսեր մինչև {share} դրամ {people} հոգու համար"),
 "en": dict(
    meals={"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner"},
    units={"g": "g", "ml": "ml", "pc": "pc"}, currency="AMD", none="none",
    hdr="{people} people, {budget} AMD/day. 'eaten' = typical price of the food used; "
        "'shop' = what you really pay for whole packs (pantry: {pantry}).",
    option="Option {n}: eaten {eaten} AMD | shop {shop} AMD", shown="   <-- shown below",
    nofit="Nothing fits {budget} AMD for {people} people{real}. Cheapest possible day (food eaten): {cheapest} AMD.",
    real=" as a real shop bill", day="Day {d}", day_eaten="Day {d}: eaten {eaten} AMD",
    day_nofit="Day {d}: nothing fits {budget} AMD.",
    shoplist="Shopping list for {label}:", col_ing="ingredient", col_need="need", col_buy="buy",
    loose="(loose, by weight)", home="assumed at home (not bought):", noprice="!! no price found for:",
    pay="--> pay at the shop: {pay} AMD, of which {left} AMD is leftover you can use in later meals",
    label_all="all {n} days (bought together)", option_label="Option {n}",
    budget_days="(budget for {n} days: {b} AMD)", steps_for="{who}{name} (for {people})",
    recipes_up_to="{meal}: recipes up to {share} AMD for {people} people"),
}
