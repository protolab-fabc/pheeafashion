#!/usr/bin/env python3
"""
SCRAPPER VINTED - PheeA Fashion
Auto-authentification : recupere un token anonyme a chaque execution.
Aucun cookie a maintenir. Tourne sur GitHub Actions toutes les heures.
"""

import requests, json, time, re, os, sys
from datetime import datetime

VINTED_USER_ID  = "3138419705"
VINTED_USERNAME = "pheeafashion"
VINTED_DOMAIN   = "https://www.vinted.be"
OUTPUT_FILE     = "data.json"
MAX_PAGES       = 10
DELAY           = 1.5

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(BASE_HEADERS)

CAT_MAP = {
    "women": "Femme", "femme": "Femme",
    "men": "Homme",   "homme": "Homme",
    "kids": "Enfant", "enfant": "Enfant",
    "accessories": "Accessoires",
}

def detect_category(url, title):
    for key, val in CAT_MAP.items():
        if key in url.lower(): return val
    t = title.lower()
    if any(w in t for w in ["robe","jupe","femme","soutien","blouse","tunique","legging"]): return "Femme"
    if any(w in t for w in ["costume","blazer","polo","cravate","chemise homme"]): return "Homme"
    if any(w in t for w in ["enfant","bebe","baby","garcon","fille"," ans"]): return "Enfant"
    if any(w in t for w in ["sac","ceinture","chapeau","bijou","montre","lunettes","collier"]): return "Accessoires"
    return "Femme"

def get_anon_token():
    """
    Visite la page profil publique pour recuperer un token anonyme.
    Vinted set automatiquement les cookies de session pour tout visiteur.
    """
    print("  Recuperation du token anonyme...")
    profile_url = f"{VINTED_DOMAIN}/member/{VINTED_USER_ID}-{VINTED_USERNAME}"

    try:
        r = SESSION.get(profile_url, timeout=20)
        print(f"  Page profil: {r.status_code}")

        if r.status_code != 200:
            return False, f"Page profil inaccessible ({r.status_code})"

        cookies = dict(SESSION.cookies)
        print(f"  Cookies recus: {list(cookies.keys())}")

        # Chercher CSRF token dans le HTML
        csrf = ""
        patterns = [
            'csrf-token" content="([^"]+)"',
            '"CSRF_TOKEN":"([^"]+)"',
            'data-csrf="([^"]+)"',
        ]
        for pattern in patterns:
            m = re.search(pattern, r.text)
            if m:
                csrf = m.group(1)
                print(f"  CSRF token trouve: {csrf[:20]}...")
                break

        if csrf:
            SESSION.headers["X-CSRF-Token"] = csrf

        # Headers pour les appels API
        SESSION.headers["Accept"] = "application/json, text/plain, */*"
        SESSION.headers["Referer"] = profile_url
        SESSION.headers["X-Requested-With"] = "XMLHttpRequest"

        return True, "ok"

    except Exception as e:
        return False, str(e)

def scrape_page(page):
    url = (
        f"{VINTED_DOMAIN}/api/v2/catalog/items"
        f"?user_id={VINTED_USER_ID}&page={page}&per_page=20&order=newest_first"
    )
    try:
        r = SESSION.get(url, timeout=20)
        print(f"  Page {page} -> {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            for key in ["items", "data", "products", "listings"]:
                if key in data and isinstance(data[key], list) and data[key]:
                    return data[key]
            for key, val in data.items():
                if isinstance(val, list) and val and isinstance(val[0], dict) and "title" in val[0]:
                    return val

    except Exception as e:
        print(f"  Erreur: {e}")
    return []

def format_item(raw):
    url = raw.get("url", raw.get("path", ""))
    if not url.startswith("http"):
        url = f"{VINTED_DOMAIN}{url}"
    title = raw.get("title", "Article")
    try:
        price_raw = raw.get("price", 0)
        price = float(price_raw.get("amount", 0)) if isinstance(price_raw, dict) else float(str(price_raw))
    except:
        price = 0
    photos = raw.get("photos", [])
    img = ""
    if photos and isinstance(photos, list):
        p = photos[0]
        img = p.get("url", "") or p.get("full_size_url", "")
    if not img:
        p = raw.get("photo", {})
        if isinstance(p, dict):
            img = p.get("url", "") or p.get("full_size_url", "")
    return {
        "id":       str(raw.get("id", int(time.time()))),
        "titre":    title,
        "prix":     round(price, 2),
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url,
        "image":    img,
        "taille":   raw.get("size_title", ""),
        "marque":   raw.get("brand_title", ""),
    }

def send_github_alert(reason):
    """Cree une issue GitHub si le scrapping echoue."""
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_token or not github_repo:
        return
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    body = (
        "## Scrapper en echec\n\n"
        f"**Raison :** {reason}\n"
        f"**Date :** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        "Vinted a peut-etre change son API ou bloque les IPs GitHub.\n\n"
        f"[Relancer le scrapper](https://github.com/{github_repo}/actions)"
    )
    try:
        requests.post(
            f"https://api.github.com/repos/{github_repo}/issues",
            headers=headers,
            json={
                "title": f"Scrapper en echec — {datetime.now().strftime('%d/%m/%Y')}",
                "body": body,
                "labels": ["scrapper-error"]
            },
            timeout=10
        )
        print("  Alerte GitHub envoyee")
    except Exception as e:
        print(f"  Erreur alerte: {e}")

def run():
    print("=" * 52)
    print("  SCRAPPER VINTED - PheeA Fashion (sans cookie)")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 52)

    # Etape 1 : token anonyme
    ok, msg = get_anon_token()
    if not ok:
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    # Etape 2 : scrapper
    articles, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        items = scrape_page(page)
        if not items:
            print(f"  Fin a la page {page}")
            break
        for raw in items:
            art = format_item(raw)
            if art["id"] not in seen:
                seen.add(art["id"])
                articles.append(art)
        print(f"  Cumul: {len(articles)} articles")
        if page < MAX_PAGES:
            time.sleep(DELAY)

    if len(articles) == 0:
        send_github_alert("0 article recupere - Vinted bloque peut-etre les IPs GitHub Actions")
        sys.exit(1)

    # Etape 3 : sauvegarder
    output = {
        "meta": {
            "source":     "Vinted",
            "profil":     f"{VINTED_DOMAIN}/member/{VINTED_USER_ID}-{VINTED_USERNAME}",
            "total":      len(articles),
            "mis_a_jour": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "statut":     "ok",
        },
        "articles": articles,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  {len(articles)} articles sauvegardes dans {OUTPUT_FILE}")
    print(f"  Mis a jour: {output['meta']['mis_a_jour']}")

if __name__ == "__main__":
    run()
