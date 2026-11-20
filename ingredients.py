"""Canonical ingredient dictionary + product-name matching rules.

Each ingredient:  id, English name, Armenian name, price basis ('kg' | 'l' | 'pc'),
                  grams per piece (for 'pc' items, used to convert recipe grams -> pieces),
                  category ids the product must come from (None = any),
                  include patterns, exclude patterns.

Patterns are regexes applied to the lower-cased product name with «brands» removed.
Use W() to anchor a stem at the start of a word: W("լոլիկ") matches "լոլիկ", "լոլիկի" but not "…լոլիկ".
Order matters: the FIRST ingredient that matches wins, so put specific ones before generic ones.
"""
import re

LETTERS = "а-яёա-ֆa-z"


def W(stem):
    """Stem at the start of a word."""
    return rf"(?<![{LETTERS}]){stem}"


def WW(word):
    """Whole word."""
    return rf"(?<![{LETTERS}]){word}(?![{LETTERS}])"


# Never an ingredient, whatever else matches.
GLOBAL_EXCLUDE = [
    W("հյութ"), W("պաղպաղակ"), W("ըմպ"), W("կոկտեյլ"), W("դեսերտ"), W("պուդինգ"),
    W("թխվածք"), W("տորթ"), W("կոնֆետ"), W("չիպս"), W("վաֆլ"), W("շոկոլադ"), W("կակաո"),
    W("նրբաբլիթ"), W("пирожн"), W("սնեկ"), W("հաբ"), W("շիլա"), W("սուրճ"), W("թեյ"),
    W("քաղցրաբլիթ"), W("պաղպ"), W("պլոմբիր"), W("լիմոնադ"), W("գազավորված"),
]

ANY_EXCLUDE = ["ապուր", "աղցան", "բանջարեղեն", "սոուսում"]
# checked on the raw name (brands included): peeled/cut ready-to-cook packs are not the raw vegetable
RAW_EXCLUDE = ["պատրաստի", "ալֆաել", "կտրտած", "քերած", "մաքրած"]

C_BAKERY, C_DAIRY, C_SAUSAGE, C_MEAT, C_POULTRY = "1923", "22", "6", "1927", "7"
C_SEMI, C_FISH, C_FISHFRESH, C_VEG, C_CANNED, C_GROC = "29", "27", "1928", "1926", "25", "26"

FRUITY = "|".join(W(x) for x in ["արքայ", "թուզ", "պինակ", "գնդիկ", "արտադրանք", 
    "ելակ", "բանան", "դեղձ", "ազնվամոր", "հապալաս", "բալ", "մանգո", "վանիլ", "մարակույա",
    "կոկոս", "խնձոր", "տանձ", "ծիրան", "կիվի", "արքայանարինջ", "մրգ", "հատապտուղ", "թխ",
    "ելակի", "սալոր", "սև հաղարջ", "կիտրոն", "չիչ", "կարամել", "մեղր"])

I = []


def add(id, en, hy, basis, cats, inc, exc=(), gpp=None):
    I.append(dict(id=id, en=en, hy=hy, basis=basis, gpp=gpp, cats=cats,
                  inc=[re.compile(p) for p in inc], exc=[re.compile(p) for p in exc]))


# ---------------- vegetables & fruit (cat 1926) ----------------
V = [C_VEG]
add("tomato", "Tomato", "Լոլիկ", "kg", V, [W("լոլիկ")], [W("չորաց"), W("հյութ"), W("կանաչ")], 120)
add("cucumber", "Cucumber", "Վարունգ", "kg", V, [W("վարունգ")], [], 120)
add("potato", "Potato", "Կարտոֆիլ", "kg", V, [W("կարտոֆիլ")], [W("ֆրի"), W("բազուկ"), W("քաղցր"), W("գազար")], 150)
add("carrot", "Carrot", "Գազար", "kg", V, [W("գազար")], [W("կարտոֆիլ"), W("կաղամբ")], 80)
add("onion", "Onion", "Սոխ", "kg", V, [W("սոխ")], [W("կանաչ"), W("կոճ")], 110)
add("garlic", "Garlic", "Սխտոր", "kg", V, [W("սխտոր")], [], 5)
add("bell_pepper", "Bell pepper", "Քաղցր պղպեղ", "kg", V, [W("պղպեղ")], [W("կծու"), W("չիլի")], 150)
add("hot_pepper", "Hot pepper", "Կծու պղպեղ", "kg", V, [W("պղպեղ"), W("չիլի")], [], 20)
add("cabbage", "Cabbage", "Կաղամբ", "kg", V, [W("կաղամբ")], [W("ծովակաղամբ")], 1000)
add("cauliflower", "Cauliflower", "Ծաղկակաղամբ", "kg", V, [W("ծաղկակաղամբ")], [], 800)
add("broccoli", "Broccoli", "Բրոկկոլի", "kg", V, [W("բրոկկոլի")], [], 300)
add("eggplant", "Eggplant", "Սմբուկ", "kg", V, [W("սմբուկ")], [], 250)
add("zucchini", "Zucchini", "Դդմիկ", "kg", V, [W("դդմիկ"), W("կաբաչ")], [], 250)
add("pumpkin", "Pumpkin", "Դդում", "kg", V, [W("դդում")], [], 1500)
add("beet", "Beetroot", "Ճակնդեղ", "kg", V, [W("ճակնդեղ")], [], 150)
add("radish", "Radish", "Բողկ", "kg", V, [W("բողկ")], [W("միկրոկանաչ")], 20)
add("spinach", "Spinach", "Սպանախ", "kg", V, [W("սպանախ")], [], None)
add("lettuce", "Lettuce", "Հազար / Սալաթ", "kg", V, [W("հաճար"), W("սալաթ"), W("այսբերգ")], [W("աղցան")], 200)
add("parsley", "Parsley", "Մաղադանոս", "kg", V, [W("մաղադանոս")], [W("չորաց")], 30)
add("cilantro", "Cilantro", "Համեմ", "kg", V, [W("համեմ")], [W("չորաց")], 30)
add("dill", "Dill", "Սամիթ", "kg", V, [W("սամիթ")], [W("չորաց")], 30)
add("basil", "Basil", "Ռեհան", "kg", V, [W("ռեհան")], [W("չորաց")], 30)
add("mint", "Mint", "Անանուխ", "kg", V, [W("անանուխ")], [W("չորաց")], 30)
add("green_onion", "Green onion", "Կանաչ սոխ", "kg", V, [W("սոխ.*կանաչ"), W("կանաչ.*սոխ")], [], 20)
add("mushroom", "Mushroom", "Սունկ", "kg", V, [W("շամպինիոն"), W("սունկ")], [W("մարինաց"), W("չորաց")], 20)
add("avocado", "Avocado", "Ավոկադո", "pc", V, [W("ավոկադո")], [], 200)
add("lemon", "Lemon", "Կիտրոն", "kg", V, [W("կիտրոն")], [W("հյութ"), "խոտ"], 100)
add("apple", "Apple", "Խնձոր", "kg", V, [W("խնձոր")], [W("հյութ"), W("չորաց")], 180)
add("pear", "Pear", "Տանձ", "kg", V, [W("տանձ")], [], 180)
add("banana", "Banana", "Բանան", "kg", V, [W("բանան")], [], 120)
add("orange", "Orange", "Նարինջ", "kg", V, [W("նարինջ")], [W("արքայ"), W("հյութ"), W("քամած")], 200)
add("tangerine", "Mandarin", "Մանդարին", "kg", V, [W("մանդարին")], [], 80)
add("grape", "Grapes", "Խաղող", "kg", V, [W("խաղող")], [], None)
add("strawberry", "Strawberry", "Ելակ", "kg", V, [W("ելակ")], [], None)
add("peach", "Peach", "Դեղձ / Նեկտարին", "kg", V, [W("դեղձ"), W("նեկտարին")], [], 150)
add("apricot", "Apricot", "Ծիրան", "kg", V, [W("ծիրան")], [W("չոր")], 40)
add("watermelon", "Watermelon", "Ձմերուկ", "kg", V, [W("ձմերուկ")], [], 4000)
add("melon", "Melon", "Սեխ", "kg", V, [W("սեխ")], [], 1500)
add("pomegranate", "Pomegranate", "Նուռ", "kg", V, [W("նուռ")], [W("հյութ")], 300)
add("ginger", "Ginger", "Կոճապղպեղ", "kg", [C_VEG, C_GROC], [W("կոճապղպեղ")], [W("աղացած")], None)

# ---------------- meat & poultry ----------------
add("egg", "Chicken egg", "Հավկիթ", "pc", [C_POULTRY], [W("հավկիթ"), W("ձու")], [W("լոր")], 55)
add("quail_egg", "Quail egg", "Լորի ձու", "pc", [C_POULTRY], [W("լորի ձու")], [], 12)
add("quail", "Quail", "Լոր", "kg", [C_POULTRY], [W("լոր")], [], None)
add("chicken_breast", "Chicken breast", "Հավի կրծքամիս", "kg", [C_POULTRY, C_MEAT], [W("կրծքամ"), W("կրծքի")], [W("խորոված"), W("մարինաց")], None)
add("chicken_thigh", "Chicken thigh/drumstick", "Հավի բուդ / ազդրամիս", "kg", [C_POULTRY, C_MEAT],
    [W("ազդրամիս"), W("բուդ"), W("քարաճիկ")], [W("խոզի"), W("ցլիկ"), W("տավար"), W("մարինաց")], None)
add("chicken_wings", "Chicken wings", "Հավի թևիկներ", "kg", [C_POULTRY, C_MEAT], [W("թևիկ"), W("ուսիկ"), W("ուսեր")], [], None)
add("chicken_liver", "Chicken liver/hearts", "Հավի լյարդ / սիրտ", "kg", [C_POULTRY], [W("սիրտ"), W("լյարդ"), W("ստամոք")], [], None)
add("chicken_whole", "Whole chicken", "Ամբողջական հավ", "kg", [C_POULTRY], [W("հավ(?![ա-ֆ])"), W("ճուտ")], [W("հավի")], None)
add("duck", "Duck", "Բադ", "kg", [C_POULTRY], [W("բադ")], [], None)
add("turkey", "Turkey", "Հնդկահավ", "kg", [C_POULTRY, C_MEAT], [W("հնդկահավ")], [], None)
add("chicken_other", "Chicken (other cuts)", "Հավի միս", "kg", [C_POULTRY, C_MEAT], [W("հավի")], [W("քյաբաբ"), W("խճողակ")], None)
add("mince", "Minced meat", "Աղացած միս (ֆարշ)", "kg", [C_MEAT, C_SEMI], [W("աղացած"), W("ֆարշ")], [], None)
add("pork", "Pork", "Խոզի միս", "kg", [C_MEAT], [W("խոզի")], [], None)
add("beef", "Beef/veal", "Տավարի / հորթի միս", "kg", [C_MEAT], [W("ցլիկ"), W("տավարի"), W("հորթի")], [W("քյաբաբ")], None)
add("lamb", "Lamb", "Գառան միս", "kg", [C_MEAT], [W("գառ"), W("ոչխար")], [], None)

# ---------------- fish ----------------
FISH = [C_FISH, C_FISHFRESH]
add("salmon", "Salmon/trout", "Սաղմոն / Իշխան", "kg", FISH, [W("սաղմոն"), W("իշխան")], [W("ձկնկիթ"), W("ապխտ"), W("պաշտետ"), W("մածուկ"), W("սենդվիչ"), W("լյարդ"), "ծովատառ", "ա-լյա"], None)
add("sturgeon", "Sturgeon", "Թառափ", "kg", FISH, [W("թառափ")], [W("ձկնկիթ")], None)
add("herring", "Herring", "Ծովատառեխ", "kg", FISH, [W("ծովատառեխ")], [], None)
add("shrimp", "Shrimp", "Ծովախեցգետին", "kg", FISH, [W("ծովախեցգետին"), W("ծովախեց")], [W("ձողիկ"), W("մածուկ")], None)
add("squid", "Squid", "Կաղամար", "kg", FISH, [W("կաղամար")], [], None)
add("fish_other", "Fish fillet (other)", "Ձկան ֆիլե", "kg", FISH, [W("ֆիլե"), W("ձուկ")], [W("ձողիկ"), W("ձկնկիթ")], None)
add("canned_tuna", "Canned tuna", "Պահածոյացված թյունոս", "kg", [C_CANNED], [W("թյունոս")], [], None)
add("sprats", "Canned sprats", "Շպրոտ", "kg", [C_CANNED], [W("շպրոտ")], [], None)

# ---------------- sausage ----------------
add("sausage", "Sausage / frankfurters", "Երշիկ / Նրբերշիկ", "kg", [C_SAUSAGE], [W("երշիկ"), W("նրբերշիկ"), W("սոսիս")], [], None)
add("bacon", "Bacon", "Բեկոն", "kg", [C_SAUSAGE], [W("բեկոն")], [], None)
add("ham", "Ham", "Խոզապուխտ", "kg", [C_SAUSAGE], [W("խոզապուխտ"), W("վզամիս"), W("ճարպապուխտ")], [], None)

# ---------------- dairy ----------------
D = [C_DAIRY]
add("milk", "Milk", "Կաթ", "l", D, [WW("կաթ")], [W("խտացրած"), W("փոշի"), W("ջնար"), W("պանրիկ"), FRUITY], None)
add("kefir", "Kefir", "Կեֆիր", "l", D, [W("կեֆիր"), W("ռյաժենկա"), W("ռեժան")], [], None)
add("matsun", "Matsun / ayran", "Մածուն / Թան", "l", D, [W("մածուն"), W("թան")], [], None)
add("sour_cream", "Sour cream", "Թթվասեր", "kg", D, [W("թթվասեր")], [], None)
add("butter", "Butter", "Կարագ", "kg", D, [W("կարագ")], [W("թխ")], None)
add("cream", "Cream", "Սերուցք", "kg", D, [W("սերուցք")], [W("պանիր"), W("պաղպ"), W("կարագ"), W("սփրեդ")], None)
add("cottage_cheese", "Cottage cheese", "Կաթնաշոռ", "kg", D, [W("կաթնաշոռ")], [W("պանիր"), W("պանրային"), W("դեսերտ"), W("ըմպ"), FRUITY], None)
add("yogurt", "Yogurt (plain)", "Յոգուրտ", "kg", D, [W("յոգուրտ"), W("մածնաբրդոշ")], [W("ըմպ"), FRUITY], None)
add("mozzarella", "Mozzarella", "Մոցարելա", "kg", D, [W("մոցարել")], [], None)
add("feta_brynza", "Brine cheese (feta/brynza)", "Պանիր (Լոռի / Չանախ / Բրինզա)", "kg", D, [W("չանախ"), W("լոռի"), W("չեչիլ"), W("սուլուգունի"), W("ֆետա"), W("բրինզա"), W("ջերմուկ")], [W("հալած")], None)
add("hard_cheese", "Hard cheese", "Պինդ պանիր", "kg", D, [W("գաուդա"), W("պարմիջանո"), W("չեդդեր"), W("էդամ"), W("մաասդամ"), W("ռուսական"), W("հոլանդական")], [W("հալած")], None)
add("processed_cheese", "Processed cheese", "Հալած պանիր", "kg", D, [W("հալած"), W("պանրիկ")], [W("վանիլ"), W("ջնար"), W("պրոտ")], None)
add("cheese", "Cheese (other)", "Պանիր", "kg", D, [W("պանիր")], [W("հալած"), W("պանրիկ")], None)

# ---------------- grocery staples (cat 26) ----------------
G = [C_GROC]
add("olive_oil", "Olive oil", "Ձիթապտղի ձեթ", "l", [C_GROC, C_CANNED], [W("ձիթապտղի ձեթ"), W("ձիթապտղի յուղ")], [W("արևածաղկի"), W("չիր")], None)
add("sunflower_oil", "Sunflower oil", "Արևածաղկի ձեթ", "l", G, [W("արևածաղկի"), W("բուսական ձեթ"), W("բուսայուղ")], [W("հալած")], None)
add("flour", "Flour", "Ալյուր", "kg", G, [W("ալյուր")], [W("բրնձի"), W("եգիպտացորենի")], None)
add("noodles", "Noodles", "Լապշա", "kg", G, [W("լապշա")], [], None)
add("rice", "Rice", "Բրինձ", "kg", G, [W("բրինձ")], [W("փաթիլ")], None)
add("buckwheat", "Buckwheat", "Հնդկաձավար", "kg", G, [W("հնդկաձավար")], [], None)
add("bulgur", "Bulgur", "Բլղուր / Հաճար", "kg", G, [W("բլղուր"), W("հաճար")], [], None)
add("lentils", "Lentils", "Ոսպ", "kg", G, [W("ոսպ")], [], None)
add("chickpeas", "Chickpeas", "Սիսեռ", "kg", G, [W("սիսեռ")], [], None)
add("beans", "Beans", "Լոբի", "kg", [C_GROC, C_CANNED], [W("լոբի")], [], None)
add("peas_canned", "Canned peas", "Պահածոյացված ոլոռ", "kg", [C_CANNED], [W("ոլոռ")], [], None)
add("corn_canned", "Canned corn", "Պահածոյացված եգիպտացորեն", "kg", [C_CANNED], [W("եգիպտացորեն")], [], None)
add("oats", "Oats / oat flakes", "Վարսակի փաթիլներ", "kg", G, [W("վարսակ")], [], None)
add("pasta", "Pasta", "Մակարոնեղեն", "kg", G, [W("մակարոն"), W("սպագետտ"), W("վերմիշել"), W("կաննելոն"), W("լազանյա"), W("ֆետուչինի"), W("պեննե"), W("ֆուզիլի"), W("ռիգատոնի")], [W("հավի"), W("ապուր")], None)
add("sugar", "Sugar", "Շաքարավազ", "kg", G, [W("շաքար")], [W("վանիլ"), W("կոկոս"), W("փոշի"), W("առանց"), "մյուսլի"], None)
add("basil_dried", "Basil", "Չորացրած ռեհան", "kg", [C_VEG, C_GROC], [W("բազիլիկ")], [], None)
add("bay_leaf", "Bay leaf", "Դափնու տերև", "kg", [C_VEG, C_GROC], [W("դափնու")], [], None)
add("oregano", "Oregano", "Օրեգանո", "kg", [C_GROC], [W("օրեգանո")], [], None)
add("cinnamon", "Cinnamon", "Դարչին", "kg", [C_GROC], [W("դարչին")], [], None)
add("cloves", "Cloves", "Մեխակ", "kg", [C_GROC], [W("մեխակ")], [], None)
add("tahini", "Tahini", "Թահին", "kg", [C_GROC], [W("թահին")], [], None)
add("split_peas", "Split peas", "Չոր ոլոռ", "kg", [C_GROC], [W("ոլոռ")], [], None)
add("semolina_groats", "Groats (dzavar)", "Ձավար", "kg", [C_GROC], [W("ձավար")], [], None)
add("salt", "Salt", "Աղ", "kg", G, [WW("աղ")], [W("հյութ")], None)
add("vinegar", "Vinegar", "Քացախ", "l", G, [W("քացախ")], [W("բալզամ")], None)
add("yeast", "Yeast", "Խմորիչ", "kg", G, [W("խմորիչ")], [], None)
add("baking_powder", "Baking powder", "Փխրեցուցիչ / Սոդա", "kg", G, [W("փխրեցուցիչ"), W("սոդա")], [], None)
add("black_pepper", "Black pepper", "Սև պղպեղ", "kg", G, [W("սև պղպեղ")], [], None)
add("paprika", "Paprika", "Պապրիկա", "kg", G, [W("պապրիկա")], [], None)
add("spice_mix", "Spice mix", "Համեմունք", "kg", G, [W("համեմունք")], [], None)
add("tomato_paste", "Tomato paste", "Տոմատի մածուկ", "kg", [C_CANNED, C_GROC], [W("տոմատի մածուկ"), W("տոմատ մածուկ"), W("տոմատի պյուրե")], [], None)
add("ketchup", "Ketchup", "Կետչուպ", "kg", [C_CANNED], [W("կետչուպ")], [], None)
add("mayonnaise", "Mayonnaise", "Մայոնեզ", "kg", [C_CANNED], [W("մայոնեզ")], [], None)
add("mustard", "Mustard", "Մանանեխ", "kg", [C_CANNED], [W("մանանեխ")], [], None)
add("soy_sauce", "Soy sauce", "Սոյայի սոուս", "l", [C_CANNED], [W("սոյայի սոուս")], [], None)
add("olives", "Olives", "Ձիթապտուղ", "kg", [C_CANNED], [W("ձիթապտուղ")], [], None)
add("honey", "Honey", "Մեղր", "kg", [C_CANNED], [W("մեղր")], [W("մանանեխ"), W("սոուս")], None)
add("jam", "Jam / preserves", "Ջեմ / Մուրաբա", "kg", [C_CANNED], [W("ջեմ"), W("մուրաբա")], [], None)
add("gherkins_pickles", "Pickled vegetables", "Թթու / Մարինացված բանջարեղեն", "kg", [C_CANNED], [W("մարինացված"), W("թթու")], [], None)

# ---------------- bakery ----------------
add("lavash", "Lavash", "Լավաշ", "kg", [C_BAKERY], [W("լավաշ")], [], None)
add("puff_pastry", "Puff pastry / dough", "Շերտավոր խմոր", "kg", [C_BAKERY, C_SEMI], [W("շերտավոր խմոր"), W("խմոր")], [W("խմորիչ")], None)
add("bread", "Bread", "Հաց", "kg", [C_BAKERY], [W("հաց"), W("բագետ"), W("բատոն"), W("լոշիկ"), W("բոքոն")], [W("չորահաց"), W("ձողիկ")], None)
add("dumplings", "Dumplings (pelmeni)", "Պելմենի / Խինկալի", "kg", [C_SEMI], [W("պելմեն"), W("խինկալի"), W("վարենիկ")], [], None)


def all_ingredients():
    return I