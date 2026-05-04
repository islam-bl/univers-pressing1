# Catalogue Univers Pressing — Prix exacts selon le tableau fourni

CATALOG = {
    "costume":        {"fr": "Costume",        "ar": "بدلة",        "repassage": 10.00, "nettoyage": {"min": 25, "max": 30}, "teinture": None},
    "veste":          {"fr": "Veste",           "ar": "فيستة",       "repassage": 5.00,  "nettoyage": 15.00,                  "teinture": None},
    "pantalon":       {"fr": "Pantalon",        "ar": "سروال",       "repassage": 5.00,  "nettoyage": 12.00,                  "teinture": 30.00},
    "djellaba":       {"fr": "Djellaba",        "ar": "جلابة نساء",  "repassage": 5.00,  "nettoyage": 15.00,                  "teinture": 50.00},
    "djellaba_telifa":{"fr": "Djellaba Telifa", "ar": "جلابة رجال",  "repassage": 5.00,  "nettoyage": 15.00,                  "teinture": None},
    "takchita":       {"fr": "Takchita",        "ar": "تكشيطة",      "repassage": 10.00, "nettoyage": {"min": 25, "max": 30}, "teinture": None},
    "caftan":         {"fr": "Caftan",          "ar": "قفطان",       "repassage": 5.00,  "nettoyage": {"min": 13, "max": 15}, "teinture": None},
    "kamis":          {"fr": "Kamis",           "ar": "قميص",        "repassage": 5.00,  "nettoyage": {"min": 13, "max": 15}, "teinture": None},
    "dfina":          {"fr": "Dfina",           "ar": "دفينة",       "repassage": 5.00,  "nettoyage": {"min": 13, "max": 15}, "teinture": None},
    "chemise":        {"fr": "Chemise",         "ar": "قميجة",       "repassage": 5.00,  "nettoyage": 10.00,                  "teinture": {"min": 30, "max": 50}},
    "tricot":         {"fr": "Tricot",          "ar": "تريكو",       "repassage": 5.00,  "nettoyage": {"min": 10, "max": 13}, "teinture": None},
    "velours":        {"fr": "Velours",         "ar": "مخمل",        "repassage": 5.00,  "nettoyage": 6.00,                   "teinture": None},
    "robe_simple":    {"fr": "Robe Simple",     "ar": "كسوة عادية",  "repassage": 5.00,  "nettoyage": 13.00,                  "teinture": None},
    "robe_plissee":   {"fr": "Robe Plissée",    "ar": "كسوة بليات",  "repassage": 10.00, "nettoyage": 28.00,                  "teinture": None},
    "jupe_simple":    {"fr": "Jupe Simple",     "ar": "مونيك عادية", "repassage": 5.00,  "nettoyage": 12.00,                  "teinture": None},
    "jupe_plissee":   {"fr": "Jupe Plissée",    "ar": "مونيك بليات", "repassage": 10.00, "nettoyage": 30.00,                  "teinture": None},
    "manteau":        {"fr": "Manteau",         "ar": "مانطو",       "repassage": 5.00,  "nettoyage": 30.00,                  "teinture": None},
    "jacket":         {"fr": "Jacket",          "ar": "جاكيطة",      "repassage": 5.00,  "nettoyage": {"min": 15, "max": 20}, "teinture": None},
    "tshirt":         {"fr": "T-Shirt",         "ar": "تشورت",       "repassage": 5.00,  "nettoyage": 10.00,                  "teinture": None},
    "cravate":        {"fr": "Cravate",         "ar": "رابط عنق",    "repassage": 3.50,  "nettoyage": 5.00,                   "teinture": None},
    "daim":           {"fr": "Daim",            "ar": "دام",         "repassage": 3.50,  "nettoyage": {"min": 100, "max": 120},"teinture": None},
    "cuir":           {"fr": "Cuir",            "ar": "جلد",         "repassage": 3.50,  "nettoyage": {"min": 100, "max": 120},"teinture": None},
    "nubuck":         {"fr": "Nubuck",          "ar": "نوبك",        "repassage": 3.50,  "nettoyage": {"min": 100, "max": 120},"teinture": None},
    "couverture":     {"fr": "Couverture",      "ar": "غطية",        "repassage": 3.50,  "nettoyage": {"min": 30, "max": 40}, "teinture": None},
    "tapis":          {"fr": "Tapis",           "ar": "زربية",       "repassage": 3.50,  "nettoyage": 50.00,                  "teinture": None},
}

SERVICE_TYPES = {
    "repassage":            {"fr": "Repassage",               "ar": "تحديد"},
    "nettoyage":            {"fr": "Nettoyage",               "ar": "تصبين"},
    "nettoyage_repassage":  {"fr": "Nettoyage + Repassage",   "ar": "تصبين + تحديد"},
    "teinture":             {"fr": "Teinture",                "ar": "الصباغة"},
}

def price_value(p):
    """Retourne une valeur numérique pour un prix (min si fourchette)."""
    if isinstance(p, dict):
        return p["min"]
    return p

def get_price(article_key, service_type):
    article = CATALOG.get(article_key)
    if not article:
        return None
    if service_type == "nettoyage_repassage":
        n = article.get("nettoyage")
        r = article.get("repassage")
        if n is None or r is None:
            return None
        return price_value(n) + price_value(r)
    return article.get(service_type)

def format_price(p):
    """Formate un prix pour affichage."""
    if p is None:
        return None
    if isinstance(p, dict):
        return f"{p['min']} à {p['max']}"
    return str(p)

def get_catalog_for_js():
    result = {}
    for k, v in CATALOG.items():
        result[k] = {
            "fr": v["fr"],
            "ar": v["ar"],
            "repassage": v.get("repassage"),
            "nettoyage": v.get("nettoyage"),
            "nettoyage_repassage": None,  # calculé côté JS
            "teinture": v.get("teinture"),
        }
    return result
