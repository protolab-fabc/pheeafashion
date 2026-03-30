# PheeA Fashion — Site vitrine Vinted

Site catalogue automatique connecté à Vinted.  
**Aucun cookie, aucune configuration** — fonctionne tout seul.

## 🚀 Mise en place (15 min)

### 1 — Créer un compte GitHub
→ [github.com](https://github.com) (gratuit)

### 2 — Créer un repository
- Clique **New repository**
- Nom : `pheeafashion`
- Visibilité : **Public**
- Clique **Create repository**

### 3 — Uploader les fichiers
Glisse ces fichiers dans le repo :
```
index.html
scrapper_vinted.py
data.json
```
Pour le fichier workflow, clique **Add file → Create new file**,  
tape comme nom : `.github/workflows/scrapper.yml`  
puis colle le contenu du fichier `scrapper.yml`.

### 4 — Activer GitHub Pages
- **Settings → Pages**
- Source : **Deploy from a branch**
- Branch : **main / (root)**
- **Save**

Ton site sera sur : `https://TON-USERNAME.github.io/pheeafashion/`

### 5 — Premier scrapping manuel
- Onglet **Actions**
- Clique **Scrapper Vinted - PheeA Fashion**
- Clique **Run workflow**

✅ Le site se met à jour **toutes les heures automatiquement**.  
✅ **Aucun cookie à gérer.** Le scrapper se connecte anonymement.  
✅ En cas de problème, tu reçois une **alerte par email** via GitHub Issues.
