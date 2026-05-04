// Catalogue Univers Pressing — Prix exacts selon le tableau officiel
// Les fourchettes sont représentées avec min et max

const CATALOG = {
  "costume":         {"fr":"Costume",        "ar":"بدلة",        "repassage":10.00, "nettoyage":{"min":25,"max":30}, "teinture":null},
  "veste":           {"fr":"Veste",           "ar":"فيستة",       "repassage":5.00,  "nettoyage":15.00,               "teinture":null},
  "pantalon":        {"fr":"Pantalon",        "ar":"سروال",       "repassage":5.00,  "nettoyage":12.00,               "teinture":30.00},
  "djellaba":        {"fr":"Djellaba",        "ar":"جلابة نساء",  "repassage":5.00,  "nettoyage":15.00,               "teinture":50.00},
  "djellaba_telifa": {"fr":"Djellaba Telifa", "ar":"جلابة رجال",  "repassage":5.00,  "nettoyage":15.00,               "teinture":null},
  "takchita":        {"fr":"Takchita",        "ar":"تكشيطة",      "repassage":10.00, "nettoyage":{"min":25,"max":30}, "teinture":null},
  "caftan":          {"fr":"Caftan",          "ar":"قفطان",       "repassage":5.00,  "nettoyage":{"min":13,"max":15}, "teinture":null},
  "kamis":           {"fr":"Kamis",           "ar":"قميص",        "repassage":5.00,  "nettoyage":{"min":13,"max":15}, "teinture":null},
  "dfina":           {"fr":"Dfina",           "ar":"دفينة",       "repassage":5.00,  "nettoyage":{"min":13,"max":15}, "teinture":null},
  "chemise":         {"fr":"Chemise",         "ar":"قميجة",       "repassage":5.00,  "nettoyage":10.00,               "teinture":{"min":30,"max":50}},
  "tricot":          {"fr":"Tricot",          "ar":"تريكو",       "repassage":5.00,  "nettoyage":{"min":10,"max":13}, "teinture":null},
  "velours":         {"fr":"Velours",         "ar":"مخمل",        "repassage":5.00,  "nettoyage":6.00,                "teinture":null},
  "robe_simple":     {"fr":"Robe Simple",     "ar":"كسوة عادية",  "repassage":5.00,  "nettoyage":13.00,               "teinture":null},
  "robe_plissee":    {"fr":"Robe Plissée",    "ar":"كسوة بليات",  "repassage":10.00, "nettoyage":28.00,               "teinture":null},
  "jupe_simple":     {"fr":"Jupe Simple",     "ar":"مونيك عادية", "repassage":5.00,  "nettoyage":12.00,               "teinture":null},
  "jupe_plissee":    {"fr":"Jupe Plissée",    "ar":"مونيك بليات", "repassage":10.00, "nettoyage":30.00,               "teinture":null},
  "manteau":         {"fr":"Manteau",         "ar":"مانطو",       "repassage":5.00,  "nettoyage":30.00,               "teinture":null},
  "jacket":          {"fr":"Jacket",          "ar":"جاكيطة",      "repassage":5.00,  "nettoyage":{"min":15,"max":20}, "teinture":null},
  "tshirt":          {"fr":"T-Shirt",         "ar":"تشورت",       "repassage":5.00,  "nettoyage":10.00,               "teinture":null},
  "cravate":         {"fr":"Cravate",         "ar":"رابط عنق",    "repassage":3.50,  "nettoyage":5.00,                "teinture":null},
  "daim":            {"fr":"Daim",            "ar":"دام",         "repassage":3.50,  "nettoyage":{"min":100,"max":120},"teinture":null},
  "cuir":            {"fr":"Cuir",            "ar":"جلد",         "repassage":3.50,  "nettoyage":{"min":100,"max":120},"teinture":null},
  "nubuck":          {"fr":"Nubuck",          "ar":"نوبك",        "repassage":3.50,  "nettoyage":{"min":100,"max":120},"teinture":null},
  "couverture":      {"fr":"Couverture",      "ar":"غطية",        "repassage":3.50,  "nettoyage":{"min":30,"max":40}, "teinture":null},
  "tapis":           {"fr":"Tapis",           "ar":"زربية",       "repassage":3.50,  "nettoyage":50.00,               "teinture":null}
};

const SERVICES = {
  "repassage":           {"fr":"Repassage",             "ar":"تحديد"},
  "nettoyage":           {"fr":"Nettoyage",             "ar":"تصبين"},
  "nettoyage_repassage": {"fr":"Nettoyage + Repassage", "ar":"تصبين + تحديد"},
  "teinture":            {"fr":"Teinture",              "ar":"الصباغة"}
};

/**
 * Retourne la valeur numérique minimale d'un prix (nombre ou fourchette).
 */
function priceMin(p) {
  if (p === null || p === undefined) return null;
  if (typeof p === 'object') return p.min;
  return p;
}

/**
 * Formate un prix pour l'affichage (fourchette ou valeur fixe).
 */
function formatPrice(p) {
  if (p === null || p === undefined) return 'N/D';
  if (typeof p === 'object') return `${p.min} à ${p.max} DH`;
  return `${p.toFixed(2)} DH`;
}

/**
 * Calcule le prix pour un article + service donné.
 * Pour Nettoyage+Repassage : additionne les deux prix (valeur min si fourchette).
 * Retourne null si le service n'existe pas pour cet article.
 */
function getPrice(articleKey, serviceKey) {
  const art = CATALOG[articleKey];
  if (!art) return null;
  if (serviceKey === 'nettoyage_repassage') {
    const n = art.nettoyage;
    const r = art.repassage;
    if (n === null || n === undefined || r === null || r === undefined) return null;
    return priceMin(n) + priceMin(r);
  }
  const p = art[serviceKey];
  return (p === null || p === undefined) ? null : priceMin(p);
}

/**
 * Retourne le texte d'affichage du prix (ex: "17.00 DH" ou "N/D").
 */
function getPriceDisplay(articleKey, serviceKey) {
  const art = CATALOG[articleKey];
  if (!art) return 'N/D';
  if (serviceKey === 'nettoyage_repassage') {
    const n = art.nettoyage;
    const r = art.repassage;
    if (n === null || n === undefined || r === null || r === undefined) return 'N/D';
    const total = priceMin(n) + priceMin(r);
    // Show breakdown
    return `${total.toFixed(2)} DH (${formatPrice(n)} + ${formatPrice(r)})`;
  }
  return formatPrice(art[serviceKey]);
}
