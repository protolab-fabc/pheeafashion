#!/usr/bin/env python3
"""
SCRAPPER VINTED - PheeA Fashion
Dependances : pip install requests
"""

import json, time, os, sys, re
import requests
from datetime import datetime

VINTED_USER_ID  = "3138419705"
VINTED_USERNAME = "pheeafashion"
BASE_URL        = "https://www.vinted.be"
OUTPUT_FILE     = "data.json"
MAX_ITEMS       = 200
DELAY           = 1.5

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Referer":         f"{BASE_URL}/",
    "Origin":          BASE_URL,
    "DNT":             "1",
}

CAT_MAP = {
    "women": "Femme", "femme": "Femme",
    "men":   "Homme", "homme": "Homme",
    "kids":  "Enfant","enfant": "Enfant",
    "accessories": "Accessoires",
}

def detect_category(url, title):
    for key, val in CAT_MAP.items():
        if key in url.lower():
            return val
    t = title.lower()
    if any(w in t for w in ["robe","jupe","femme","soutien","blouse","tunique","legging"]):
        return "Femme"
    if any(w in t for w in ["costume","blazer","polo","cravate","chemise homme"]):
        return "Homme"
    if any(w in t for w in ["enfant","bebe","baby","garcon","fille"," ans"]):
        return "Enfant"
    if any(w in t for w in ["sac","ceinture","chapeau","bijou","montre","lunettes","collier"]):
        return "Accessoires"
    return "Femme"

def format_item(raw):
    url   = raw.get("url", "") or ""
    title = raw.get("title", "Article") or "Article"
    try:
        price = float(raw.get("price", 0) or 0)
    except Exception:
        price = 0.0

    img = ""
    photo = raw.get("photo") or raw.get("photos", [None])[0]
    if isinstance(photo, dict):
        img = photo.get("url") or photo.get("full_size_url") or ""

    return {
        "id":       str(raw.get("id", int(time.time()))),
        "titre":    title,
        "prix":     round(price, 2),
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url if url.startswith("http") else f"{BASE_URL}{url}",
        "image":    img,
        "taille":   raw.get("size_title",  "") or "",
        "marque":   raw.get("brand_title", "") or "",
    }

def get_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    # Recuperation des cookies via la page d'accueil
    r = session.get(BASE_URL, timeout=15)
    r.raise_for_status()
    print(f"  Page accueil: {r.status_code} | Cookies: {list(session.cookies.keys())}")
    if "_vinted_be_session" not in session.cookies:
        print("  [WARN] Cookie _vinted_be_session absent")
    return session

def send_github_alert(reason):
    import urllib.request as _req
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_token or not github_repo:
        return
    body = (
        "## Scrapper en echec\n\n"
        f"**Raison :** {reason}\n"
        f"**Date :** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"[Relancer le scrapper](https://github.com/{github_repo}/actions)"
    )
    try:
        payload = json.dumps({
            "title":  f"Scrapper en echec - {datetime.now().strftime('%d/%m/%Y')}",
            "body":   body,
            "labels": ["scrapper-error"],
        }).encode()
        req = _req.Request(
            f"https://api.github.com/repos/{github_repo}/issues",
            data=payload,
            headers={
                "Authorization":  f"token {github_token}",
                "Accept":         "application/vnd.github.v3+json",
                "Content-Type":   "application/json",
            },
            method="POST",
        )
        _req.urlopen(req, timeout=10)
        print("  Alerte GitHub envoyee")
    except Exception as e:
        print(f"  Erreur alerte: {e}")

def run():
    print("=" * 52)
    print("  SCRAPPER VINTED - PheeA Fashion")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 52)

    print("  Initialisation session Vinted BE...")
    try:
        session = get_session()
    except Exception as e:
        msg = f"Impossible d'initialiser la session: {e}"
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    print(f"  Recherche articles vendeur {VINTED_USER_ID}...")
    articles, seen = [], set()

    try:
        page = 1
        while len(articles) < MAX_ITEMS:
            params = {
                "user_id":    VINTED_USER_ID,
                "order":      "newest_first",
                "page":       page,
                "per_page":   20,
            }
            r = session.get(
                f"{BASE_URL}/api/v2/catalog/items",
                params=params,
                timeout=20,
            )

            if r.status_code == 401:
                print("  [WARN] 401 - tentative re-auth...")
                session = get_session()
                time.sleep(3)
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
            if not items:
                print(f"  Fin a la page {page} (0 item)")
                break

            for raw in items:
                art = format_item(raw)
                if art["id"] not in seen:
                    seen.add(art["id"])
                    articles.append(art)

            print(f"  Page {page} -> {len(items)} items | Cumul: {len(articles)}")
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
        send_github_alert("0 article recupere - Vinted bloque les IPs GitHub Actions")
        sys.exit(1)

    output = {
        "meta": {
            "source":     "Vinted",
            "profil":     f"{BASE_URL}/member/{VINTED_USER_ID}-{VINTED_USERNAME}",
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
