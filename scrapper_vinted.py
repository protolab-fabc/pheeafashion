#!/usr/bin/env python3
"""
SCRAPPER VINTED - PheeA Fashion
Dependances : pip install vinted-api-wrapper requests
"""

import json, time, os, sys, requests
from datetime import datetime

try:
    from vinted import Vinted
except ImportError:
    print("[ERREUR] Installe vinted-api-wrapper : pip install vinted-api-wrapper")
    sys.exit(1)

VINTED_USER_ID  = "3138419705"
VINTED_USERNAME = "pheeafashion"
VINTED_BASE_URL = "https://www.vinted.be"
OUTPUT_FILE     = "data.json"
MAX_ITEMS       = 200
PER_PAGE        = 20
DELAY           = 1.5

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

def format_item(raw: dict) -> dict:
    url   = raw.get("url", "") or ""
    title = raw.get("title", "Article") or "Article"
    try:
        price = float(raw.get("price", 0) or 0)
    except Exception:
        price = 0.0

    img = ""
    photo = raw.get("photo") or {}
    if isinstance(photo, dict):
        img = photo.get("url", "") or photo.get("full_size_url", "") or ""

    return {
        "id":       str(raw.get("id", int(time.time()))),
        "titre":    title,
        "prix":     round(price, 2),
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url,
        "image":    img,
        "taille":   raw.get("size_title",  "") or "",
        "marque":   raw.get("brand_title", "") or "",
    }

def get_session_cookies() -> dict:
    """Recupere les cookies via le wrapper Vinted."""
    vinted = Vinted(domain="be")
    # Le wrapper expose la session requests interne
    session = getattr(vinted, "session", None) or getattr(vinted, "_session", None)
    if session and hasattr(session, "cookies"):
        return dict(session.cookies)
    # Fallback : recuperer les cookies manuellement
    resp = requests.get(
        VINTED_BASE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-BE,fr;q=0.9",
        },
        timeout=10,
    )
    return dict(resp.cookies)

def fetch_page(session: requests.Session, page: int) -> list:
    """Appel direct a l'API Vinted catalog/items."""
    url = f"{VINTED_BASE_URL}/api/v2/catalog/items"
    params = {
        "user_id":    VINTED_USER_ID,
        "order":      "newest_first",
        "page":       page,
        "per_page":   PER_PAGE,
        "time":       time.time(),
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "fr-BE,fr;q=0.9",
        "Referer":         f"{VINTED_BASE_URL}/membre/{VINTED_USER_ID}-{VINTED_USERNAME}/infos",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = session.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()

    # Vinted peut renvoyer du HTML (blocage Cloudflare) au lieu de JSON
    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type:
        raise ValueError(f"Reponse non-JSON (Content-Type: {content_type}) — IP peut-etre bloquee")

    data = resp.json()
    return data.get("items", [])

def send_github_alert(reason: str):
    import urllib.request as _req
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_token or not github_repo:
        return
    body = (
        "## Scrapper en echec\n\n"
        f"**Raison :** {reason}\n"
        f"**Date :** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        "Vinted a peut-etre change son API ou bloque les IPs GitHub Actions.\n\n"
        f"[Relancer](https://github.com/{github_repo}/actions)"
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
    print("  SCRAPPER VINTED - PheeA Fashion")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 52)

    # 1. Obtenir les cookies d'authentification
    print("  Recuperation des cookies Vinted...")
    try:
        cookies = get_session_cookies()
        print(f"  {len(cookies)} cookie(s) recupere(s): {list(cookies.keys())}")
    except Exception as e:
        msg = f"Impossible d'obtenir les cookies: {e}"
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    # 2. Creer une session requests avec les cookies
    session = requests.Session()
    session.cookies.update(cookies)

    # 3. Scraper les pages
    print(f"  Recherche articles vendeur {VINTED_USER_ID}...")
    articles, seen = [], set()

    try:
        page = 1
        while len(articles) < MAX_ITEMS:
            raw_items = fetch_page(session, page)

            if not raw_items:
                print(f"  Fin a la page {page} (0 item)")
                break

            for raw in raw_items:
                art = format_item(raw)
                if art["id"] not in seen:
                    seen.add(art["id"])
                    articles.append(art)

            print(f"  Page {page} -> {len(raw_items)} items | Cumul: {len(articles)}")
            page += 1
            time.sleep(DELAY)

    except ValueError as e:
        # IP bloquee ou reponse inattendue
        msg = str(e)
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)
    except Exception as e:
        if len(articles) == 0:
            msg = f"Erreur scraping page {page}: {e}"
            print(f"[ERREUR] {msg}")
            send_github_alert(msg)
            sys.exit(1)
        else:
            print(f"  [WARN] Arret apres erreur a la page {page}: {e}")

    if len(articles) == 0:
        send_github_alert("0 article recupere")
        sys.exit(1)

    # 4. Sauvegarde
    output = {
        "meta": {
            "source":     "Vinted",
            "profil":     f"{VINTED_BASE_URL}/member/{VINTED_USER_ID}-{VINTED_USERNAME}",
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
