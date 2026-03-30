#!/usr/bin/env python3
"""
SCRAPPER VINTED - PheeA Fashion
Dependances : pip install vinted-api-wrapper
"""

import json, time, os, sys
from datetime import datetime

try:
    from vinted import Vinted
except ImportError:
    print("[ERREUR] Installe vinted-api-wrapper : pip install vinted-api-wrapper")
    sys.exit(1)

VINTED_USER_ID  = "3138419705"
VINTED_USERNAME = "pheeafashion"
VINTED_DOMAIN   = "https://www.vinted.be"
OUTPUT_FILE     = "data.json"
MAX_ITEMS       = 200
DELAY           = 1.0

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
    url   = getattr(raw, "url",   "") or ""
    title = getattr(raw, "title", "Article") or "Article"
    try:
        price = float(getattr(raw, "price", 0) or 0)
    except Exception:
        price = 0.0

    img   = ""
    photo = getattr(raw, "photo", None)
    if photo:
        img = getattr(photo, "url", "") or getattr(photo, "full_size_url", "") or ""

    return {
        "id":       str(getattr(raw, "id", int(time.time()))),
        "titre":    title,
        "prix":     round(price, 2),
        "cat":      detect_category(url, title),
        "platform": "Vinted",
        "lien":     url,
        "image":    img,
        "taille":   getattr(raw, "size_title",  "") or "",
        "marque":   getattr(raw, "brand_title", "") or "",
    }

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
        "Vinted a peut-etre change son API ou bloque les IPs GitHub.\n\n"
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

    print("  Initialisation client Vinted BE...")
    try:
        vinted = Vinted(domain="be")
    except Exception as e:
        msg = f"Impossible d'initialiser Vinted: {e}"
        print(f"[ERREUR] {msg}")
        send_github_alert(msg)
        sys.exit(1)

    print(f"  Recherche articles vendeur {VINTED_USER_ID}...")
    articles, seen = [], set()

    try:
        page = 1
        while len(articles) < MAX_ITEMS:
            search_url = (
                f"https://www.vinted.be/api/v2/catalog/items"
                f"?user_id={VINTED_USER_ID}"
                f"&order=newest_first"
                f"&page={page}"
                f"&per_page=20"
            )
            result = vinted.search(url=search_url)
            items  = getattr(result, "items", [])

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
        send_github_alert("0 article recupere - Vinted bloque peut-etre les IPs GitHub Actions")
        sys.exit(1)

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
