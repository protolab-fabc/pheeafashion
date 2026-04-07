#!/usr/bin/env python3
"""
SCRAPPER VINTED - Profil configurable
Dependances : pip install requests seleniumbase
"""

import json, time, os, sys, re
import requests
from datetime import datetime

DEFAULT_PROFIL_URL = "https://www.vinted.be/member/3138419705-pheeafashion"

OUTPUT_FILE = "data.json"
DELAY = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "DNT": "1",
}

def parse_profil_url(url):
    match = re.search(r"(https?://[^/]+)/member/(\d+)-([^/?#]+)", url)
    if not match:
        print(f"[ERREUR] Lien invalide : {url}")
        sys.exit(1)
    return match.group(2), match.group(3), match.group(1)

raw_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROFIL_URL
VINTED_USER_ID, VINTED_USERNAME, BASE_URL = parse_profil_url(raw_url)
PROFIL_URL = f"{BASE_URL}/member/{VINTED_USER_ID}-{VINTED_USERNAME}?tab=closet"

CAT_URL = {
    "women": "Femme", "femme": "Femme", "ladies": "Femme",
    "woman": "Femme", "dame": "Femme", "dames": "Femme",
    "men": "Homme", "homme": "Homme", "man": "Homme",
    "heren": "Homme", "herren": "Homme",
    "kids": "Enfant", "enfant": "Enfant", "children": "Enfant",
    "baby": "Enfant", "bebe": "Enfant", "junior": "Enfant",
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
        if key in url_l:
            return val
    for w in CAT_TITLE_ACCESSOIRES:
        if w in title_l:
            return "Accessoires"
    for w in CAT_TITLE_ENFANT:
        if w in title_l:
            return "Enfant"
    for w in CAT_TITLE_HOMME:
        if w in title_l:
            return "Homme"
    for w in CAT_TITLE_FEMME:
        if w in title_l:
            return "Femme"
    return "Femme"

def to_float(val):
    if val is None:
        return None
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
    url = raw.get("url", "") or ""
    title = raw.get("title", "Article") or "Article"
    price = extract_price(raw)
    img = ""
    photo = raw.get("photo") or (raw.get("photos") or [None])[0]
    if isinstance(photo, dict):
        img = photo.get("url") or photo.get("full_size_url") or ""
    return {
        "id":       str(raw.get("id", int(time.time()))),
        "titre":    title,
        "prix":     price,
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url if url.startswith("http") else f"{BASE_URL}{url}",
        "image":    img,
        "taille":   raw.get("size_title", "") or "",
        "marque":   raw.get("brand_title", "") or "",
    }

def get_session():
    try:
        from seleniumbase import SB
        print(f"  Lancement Chrome headless -> {PROFIL_URL}")
        with SB(uc=True, headless=True) as sb:
            sb.open(PROFIL_URL)
            sb.sleep(4)
            raw_cookies = sb.get_cookies()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        print(f"  Cookies obtenus : {list(cookies.keys())}")
        if "access_token_web" not in cookies:
            print("  [WARN] access_token_web absent")
        s = requests.Session()
        s.headers.update(HEADERS)
        s.headers.update({"Referer": f"{BASE_URL}/", "Origin": BASE_URL})
        domain = BASE_URL.replace("https://", "")
        for name, value in cookies.items():
            s.cookies.set(name, value, domain=domain)
        return s
    except ImportError:
        print("[ERREUR] seleniumbase non installe.")
        sys.exit(1)

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
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        _req.urlopen(req, timeout=10)
        print("  Alerte GitHub envoyee")
    except Exception as e:
        print(f"  Erreur alerte: {e}")

def is_good_seller_item(item):
    if str(item.get("user_id", "")) == str(VINTED_USER_ID):
        return True
    if str(item.get("seller_id", "")) == str(VINTED_USER_ID):
        return True
    user = item.get("user")
    if isinstance(user, dict) and str(user.get("id", "")) == str(VINTED_USER_ID):
        return True
    return False

def run():
    print("=" * 52)
    print(f"  SCRAPPER VINTED - {VINTED_USERNAME}")
    print(f"  Profil : {PROFIL_URL}")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 52)

    print("  Initialisation session via Chrome headless...")
    try:
        session = get_session()
    except Exception as e:
        msg = f"Impossible d'initialiser la session: {e}"
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    API_URL = f"{BASE_URL}/api/v2/catalog/items"
    print(f"  Endpoint : {API_URL}?user_id={VINTED_USER_ID}")

    articles, seen = [], set()
    page = 1
    empty_streak = 0

    try:
        while True:
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

            if r.status_code == 429:
                retry = int(r.headers.get("Retry-After", 60))
                print(f"  [WARN] Rate limit, attente {retry}s...")
                time.sleep(retry)
                continue

            if r.status_code == 404:
                print(f"  Page {page} -> 404, fin")
                break

            r.raise_for_status()

            try:
                data = r.json()
            except Exception as e:
                print(f"  [WARN] JSON invalide page {page}: {e}")
                break

            items = data.get("items", [])
            items_vendeur = [item for item in items if is_good_seller_item(item)]

            if not items_vendeur:
                empty_streak += 1
                print(f"  Page {page} -> 0 items vendeur (streak {empty_streak})")
                if empty_streak >= 2 or not items:
                    print("  Fin de pagination")
                    break
            else:
                empty_streak = 0
                for raw in items_vendeur:
                    art = format_item(raw)
                    if art["id"] not in seen:
                        seen.add(art["id"])
                        articles.append(art)
                print(f"  Page {page} -> {len(items_vendeur)} items vendeur | Cumul: {len(articles)}")

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

    output = {
        "meta": {
            "source":     "Vinted",
            "profil":     PROFIL_URL,
            "total":      len(articles),
            "mis_a_jour": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "statut":     "ok",
        },
        "articles": articles,
    }

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  {len(articles)} articles sauvegardes")
    print(f"  Mis a jour: {output['meta']['mis_a_jour']}")

if __name__ == "__main__":
    run()
