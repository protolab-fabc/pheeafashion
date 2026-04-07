#!/usr/bin/env python3
"""
SCRAPPER VINTED - Profil configurable
Dependances : pip install requests

Usage:
  python scrapper_vinted.py
  python scrapper_vinted.py https://www.vinted.be/member/3138419705-pheeafashion
"""

import json, time, os, sys, re
import requests
from datetime import datetime

# ──────────────────────────────────────────────
#  ✏️  COLLE TON LIEN ICI (ou passe-le en argument)
# ──────────────────────────────────────────────
DEFAULT_PROFIL_URL = "https://www.vinted.be/member/3138419705-pheeafashion"
# ──────────────────────────────────────────────

OUTPUT_FILE = "data.json"
DELAY       = 1.5

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "DNT":             "1",
}

def parse_profil_url(url):
    match = re.search(r"(https?://[^/]+)/member/(\d+)-([^/?#]+)", url)
    if not match:
        print(f"[ERREUR] Lien invalide : {url}")
        print("  Format attendu : https://www.vinted.be/member/USERID-USERNAME")
        sys.exit(1)
    return match.group(2), match.group(3), match.group(1)

raw_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROFIL_URL
VINTED_USER_ID, VINTED_USERNAME, BASE_URL = parse_profil_url(raw_url)
PROFIL_URL = f"{BASE_URL}/member/{VINTED_USER_ID}-{VINTED_USERNAME}?tab=closet"

CAT_URL = {
    "women": "Femme", "femme": "Femme", "ladies": "Femme",
    "woman": "Femme", "dame": "Femme", "dames": "Femme",
    "men":   "Homme", "homme": "Homme", "man": "Homme",
    "heren": "Homme", "herren": "Homme",
    "kids":  "Enfant", "enfant": "Enfant", "children": "Enfant",
    "baby":  "Enfant", "bebe": "Enfant", "junior": "Enfant",
    "garcon": "Enfant", "fille": "Enfant", "girl": "Enfant", "boy": "Enfant",
    "accessories": "Accessoires", "accessoires": "Accessoires",
    "accessory": "Accessoires", "bags": "Accessoires", "jewelry": "Accessoires",
    "bijoux": "Accessoires", "shoes": "Accessoires", "chaussures": "Accessoires",
}
CAT_TITLE_ACCESSOIRES = [
    "sac", "pochette", "ceinture", "chapeau", "bonnet", "echarpe", "foulard",
    "bijou", "collier", "bague", "bracelet", "montre", "lunettes", "lunette",
    "chaussure", "basket", "botte", "sandale", "escarpin", "talon", "mocassin",
    "portefeuille", "sac a main", "tote bag", "backpack", "sac dos",
    "gants", "mitaines", "casquette",
]
CAT_TITLE_ENFANT = [
    "enfant", "bebe", "baby", "garcon", "fille", " ans", "naissance",
    "maternelle", "junior", "kid", "kids", "creche", "pyjama enfant",
    "body bebe", "combinaison bebe", "gigoteuse",
]
CAT_TITLE_HOMME = [
    "costume", "blazer homme", "polo homme", "cravate", "chemise homme",
    "pull homme", "sweat homme", "veste homme", "manteau homme", "jean homme",
    "pantalon homme", "short homme", "bermuda", "jogging homme",
]
CAT_TITLE_FEMME = [
    "robe", "jupe", "blouse", "tunique", "legging", "soutien", "brassiere",
    "bustier", "crop top", "cardigan femme", "pull femme", "manteau femme",
    "veste femme", "chemisier", "combinaison", "salopette femme", "body",
    "lingerie", "nuisette", "pyjama femme", "maillot bain", "bikini",
]

def detect_category(url, title):
    url_l, title_l = url.lower(), title.lower()
    for key, val in CAT_URL.items():
        if key in url_l: return val
    for w in CAT_TITLE_ACCESSOIRES:
        if w in title_l: return "Accessoires"
    for w in CAT_TITLE_ENFANT:
        if w in title_l: return "Enfant"
    for w in CAT_TITLE_HOMME:
        if w in title_l: return "Homme"
    for w in CAT_TITLE_FEMME:
        if w in title_l: return "Femme"
    return "Femme"

def to_float(val):
    if val is None: return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if f > 0 else None
    if isinstance(val, str):
        try:
            f = float(val.replace(",", ".").replace(" ", "").replace("\u202f", ""))
            return f if f > 0 else None
        except Exception:
            return None
    return None

def extract_price(raw):
    candidates = []
    candidates.append(raw.get("price_numeric"))
    p = raw.get("price")
    if isinstance(p, dict):
        candidates.append(p.get("amount"))
        candidates.append(p.get("currency_amount"))
    else:
        candidates.append(p)
    for key in ("total_item_price", "item_price", "original_price"):
        v = raw.get(key)
        candidates.append(v.get("amount") if isinstance(v, dict) else v)
    for c in candidates:
        r = to_float(c)
        if r is not None:
            return round(r, 2)
    return 0.0

def format_item(raw):
    url   = raw.get("url", "") or ""
    title = raw.get("title", "Article") or "Article"
    price = extract_price(raw)

    img   = ""
    photo = raw.get("photo") or (raw.get("photos") or [None])[0]
    if isinstance(photo, dict):
        img = photo.get("url") or photo.get("full_size_url") or ""

    if price == 0.0:
        price_fields = {k: v for k, v in raw.items() if "price" in k.lower()}
        print(f"    [DEBUG PRIX] '{title[:35]}' | champs: {price_fields}")

    return {
        "id":       str(raw.get("id", int(time.time()))),
        "titre":    title,
        "prix":     price,
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url if url.startswith("http") else f"{BASE_URL}{url}",
        "image":    img,
        "taille":   raw.get("size_title",  "") or "",
        "marque":   raw.get("brand_title", "") or "",
    }

def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.headers.update({"Referer": f"{BASE_URL}/", "Origin": BASE_URL})
    print(f"  Visite profil pour cookies : {PROFIL_URL}")
    r = s.get(PROFIL_URL, timeout=15)
    r.raise_for_status()
    print(f"  Statut: {r.status_code} | Cookies: {list(s.cookies.keys())}")
    if "access_token_web" not in s.cookies:
        print("  [WARN] access_token_web absent !")
    return s

def send_github_alert(reason):
    import urllib.request as _req
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_token or not github_repo:
        return
    try:
        payload = json.dumps({
            "title":  f"Scrapper en echec - {datetime.now().strftime('%d/%m/%Y')}",
            "body":   f"## Scrapper en echec\n\n**Raison :** {reason}\n**Date :** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "labels": ["scrapper-error"],
        }).encode()
        req = _req.Request(
            f"https://api.github.com/repos/{github_repo}/issues",
            data=payload,
            headers={
                "Authorization": f"token {github_token}",
                "Accept":        "application/vnd.github.v3+json",
                "Content-Type":  "application/json",
            },
            method="POST",
        )
        _req.urlopen(req, timeout=10)
        print("  Alerte GitHub envoyee")
    except Exception as e:
        print(f"  Erreur alerte: {e}")

def run():
    print("=" * 52)
    print(f"  SCRAPPER VINTED - {VINTED_USERNAME}")
    print(f"  Profil : {PROFIL_URL}")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 52)

    print("  Initialisation session...")
    try:
        session = get_session()
    except Exception as e:
        msg = f"Impossible d'initialiser la session: {e}"
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    API_URL = f"{BASE_URL}/api/v2/catalog/items"

    # ── Récupère d'abord le nombre total d'articles ──────────────────────────
    r0 = session.get(API_URL, params={"user_id": VINTED_USER_ID, "page": 1, "per_page": 1}, timeout=20)
    r0.raise_for_status()
    pagination  = r0.json().get("pagination", {})
    total_items = pagination.get("total_entries", 0)
    total_pages = pagination.get("total_pages", 1)
    MAX_ITEMS   = total_items  # on scrape TOUT ce que Vinted déclare
    print(f"  Articles declares sur le profil : {total_items} ({total_pages} pages)")
    print(f"  Endpoint : {API_URL}?user_id={VINTED_USER_ID}")

    articles, seen = [], set()

    try:
        page = 1
        while len(articles) < MAX_ITEMS:
            r = session.get(
                API_URL,
                params={
                    "user_id":  VINTED_USER_ID,
                    "order":    "newest_first",
                    "page":     page,
                    "per_page": 20,
                },
                timeout=20,
            )

            if r.status_code == 401:
                print("  [WARN] 401 - re-auth...")
                session = get_session()
                time.sleep(3)
                continue

            if r.status_code == 404:
                print(f"  Page {page} -> 404, fin")
                break

            if r.status_code == 429:
                retry = int(r.headers.get("Retry-After", 60))
                print(f"  [WARN] Rate limit, attente {retry}s...")
                time.sleep(retry)
                continue

            r.raise_for_status()

            try:
                data = r.json()
            except Exception as e:
                print(f"  [WARN] JSON invalide page {page}: {e}")
                break

            items = data.get("items", [])
            if not items:
                print(f"  Fin a la page {page} (0 item)")
                break

            for raw in items:
                art = format_item(raw)
                if art["id"] not in seen:
                    seen.add(art["id"])
                    articles.append(art)

            print(f"  Page {page}/{total_pages} -> {len(items)} items | Cumul: {len(articles)}/{total_items}")
            page += 1
            time.sleep(DELAY)

    except Exception as e:
        if len(articles) == 0:
            msg = f"Erreur scraping: {e}"
            print(f"[ERREUR] {msg}")
            send_github_alert(msg)
            sys.exit(1)
        else:
            print(f"  [WARN] Arret apres erreur: {e}")

    if len(articles) == 0:
        send_github_alert("0 article recupere")
        sys.exit(1)

    # ── Ecrase complètement data.json — les articles vendus/supprimés
    #    disparaissent naturellement car on repart de zéro à chaque run
    output = {
        "meta": {
            "source":          "Vinted",
            "profil":          PROFIL_URL,
            "total":           len(articles),
            "total_vinted":    total_items,
            "mis_a_jour":      datetime.now().strftime("%d/%m/%Y %H:%M"),
            "statut":          "ok",
        },
        "articles": articles,
    }

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    prix_ok   = sum(1 for a in articles if a["prix"] > 0)
    prix_zero = len(articles) - prix_ok
    print(f"\n  {len(articles)}/{total_items} articles sauvegardes")
    print(f"  Avec prix: {prix_ok} | Sans prix: {prix_zero}")
    print(f"  Mis a jour: {output['meta']['mis_a_jour']}")

if __name__ == "__main__":
    run()
