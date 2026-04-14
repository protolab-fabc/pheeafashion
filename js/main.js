/* ── EMOJIS PAR CATÉGORIE ── */
const EMOJI_CAT = {
  "Femme":       ["👗","👠","👒","👜","🧣","💄","🥻","👙"],
  "Homme":       ["👔","👟","🕴️","🧥","👖","🎩","🧤","⌚"],
  "Enfant":      ["🧒","👶","🎀","🧸","🛹","🎠","🎒","👟"],
  "Accessoires": ["👜","💍","🕶️","⌚","👒","🧣","💎","🎀"],
};
function getEmoji(cat) {
  const arr = EMOJI_CAT[cat] || ["👕"];
  return arr[Math.floor(Math.random() * arr.length)];
}

/* ── NETTOYAGE DES CHAMPS SCRAPPÉS ── */

// Extrait la taille propre : "XL / 42 / 14 État Neuf..." → "XL"
function cleanTaille(raw) {
  if (!raw) return '';
  // Coupe avant "État"
  let s = raw.split(/\bÉtat\b/i)[0];
  // Coupe avant "Matière"
  s = s.split(/\bMati[eè]re\b/i)[0];
  // Garder seulement la première partie (avant /)
  s = s.split('/')[0].trim();
  return s.replace(/\s+/g, ' ').trim();
}

// Extrait la marque propre : "Street One Menu relatif à la marque..." → "Street One"
function cleanMarque(raw) {
  if (!raw) return '';
  let s = raw.split(/\bMenu relatif\b/i)[0].trim();
  // Ignorer "pas de marque"
  if (/pas de marque/i.test(s)) return '';
  return s.trim();
}

// Auto-détecte la catégorie Enfant via la taille (ex: "10 ans", "152 cm")
function detectCat(cat, tailleRaw) {
  if (cat === 'Enfant') return 'Enfant';
  if (/\d+\s*ans|\b\d{3}\s*cm\b/i.test(tailleRaw || '')) return 'Enfant';
  return cat;
}

/* ── DONNÉES & CHARGEMENT ── */
let articles = [];

async function loadData() {
  try {
    const resp = await fetch('data.json?t=' + Date.now());
    if (!resp.ok) throw new Error('data.json introuvable');
    const data = await resp.json();

    articles = (data.articles || []).map(a => {
      const tailleClean  = cleanTaille(a.taille || '');
      const marqueClean  = cleanMarque(a.marque || '');
      const catDetected  = detectCat(a.cat || 'Femme', a.taille || '');
      return {
        id:       a.id,
        titre:    a.titre,
        prix:     a.prix || 0,
        cat:      catDetected,
        platform: a.platform || 'Vinted',
        lien:     a.lien || '#',
        image:    a.image || '',
        taille:   tailleClean,
        marque:   marqueClean,
        emoji:    getEmoji(catDetected),
      };
    });

    if (data.meta) {
      const badge = document.getElementById('last-update');
      if (badge) badge.textContent = 'Mis à jour ' + data.meta.mis_a_jour;
    }
  } catch(e) {
    // Données de démo si data.json indisponible
    articles = [
      { id:1, titre:"Robe fleurie vintage",   prix:18, cat:"Femme",       platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"S",  marque:"",        emoji:"👗" },
      { id:2, titre:"Veste en jean oversize",  prix:24, cat:"Femme",       platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"M",  marque:"",        emoji:"🧥" },
      { id:3, titre:"Chemise à carreaux",      prix:14, cat:"Homme",       platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"L",  marque:"",        emoji:"👔" },
      { id:4, titre:"Sneakers blanches T42",   prix:22, cat:"Homme",       platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"42", marque:"",        emoji:"👟" },
      { id:5, titre:"Ensemble enfant 4 ans",   prix:9,  cat:"Enfant",      platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"4A", marque:"",        emoji:"🧒" },
      { id:6, titre:"Sac à main caramel",      prix:16, cat:"Accessoires", platform:"Vinted", lien:"https://www.vinted.be/member/3138419705-pheeafashion", image:"", taille:"",  marque:"Bessie",  emoji:"👜" },
    ];
  }

  document.getElementById('stat-total').textContent = articles.length;
  updateFilterCounts();
  renderGrid();
}

/* ── ÉTAT DES FILTRES ── */
const platformColors = { Vinted:"#09B1BA", TikTok:"#111111", Facebook:"#1877F2", Instagram:"#E1306C" };
let filterCat       = "tous";
let filterPlatforms = new Set();

/* ── COMPTEURS PAR CATÉGORIE ── */
function updateFilterCounts() {
  document.querySelectorAll('[data-cat]').forEach(btn => {
    const cat = btn.dataset.cat;
    const count = cat === 'tous'
      ? articles.filter(a => filterPlatforms.size === 0 || filterPlatforms.has(a.platform)).length
      : articles.filter(a => a.cat === cat && (filterPlatforms.size === 0 || filterPlatforms.has(a.platform))).length;

    // Badge compteur
    const badgeClass = 'fbtn-count';
    let badge = btn.querySelector('.' + badgeClass);
    if (!badge) {
      badge = document.createElement('span');
      badge.className = badgeClass;
      btn.appendChild(badge);
    }
    badge.textContent = count > 0 ? ` ${count}` : '';

    // Désactiver si 0 résultats (sauf "Tous")
    if (cat !== 'tous') {
      btn.disabled = count === 0;
      btn.style.opacity = count === 0 ? '0.3' : '';
      btn.style.cursor  = count === 0 ? 'not-allowed' : '';
    }
  });
}

/* ── RENDU DE LA GRILLE ── */
function renderGrid() {
  const grid = document.getElementById('grid');
  const filtered = articles.filter(a => {
    const catOk  = filterCat === 'tous' || a.cat === filterCat;
    const platOk = filterPlatforms.size === 0 || filterPlatforms.has(a.platform);
    return catOk && platOk;
  });

  document.getElementById('count-display').textContent =
    filtered.length + (filtered.length > 1 ? ' articles' : ' article');

  if (filtered.length === 0) {
    grid.innerHTML = '<div class="empty">Aucun article pour ces filtres.</div>';
    return;
  }

  grid.innerHTML = filtered.map((a, i) => {
    const emojiHtml = `<span style="font-size:2.8rem">${a.emoji}</span>`;
    const imgHtml = a.image
      ? `<img src="${a.image}" alt="${a.titre}" loading="lazy"
             style="width:100%;height:100%;object-fit:cover;position:absolute;top:0;left:0;"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
         <span style="font-size:2.8rem;display:none;width:100%;height:100%;align-items:center;justify-content:center;position:absolute;top:0;left:0;">${a.emoji}</span>`
      : emojiHtml;

    // Afficher taille et marque nettoyées
    const extra = [a.taille, a.marque].filter(Boolean).join(' · ');

    return `
    <a class="card" href="${a.lien}" target="_blank" style="animation-delay:${i*0.04}s">
      <div class="card-img-placeholder">
        ${imgHtml}
        <span class="platform-dot" style="background:${platformColors[a.platform]}"></span>
        <span class="platform-pill">${a.platform}</span>
      </div>
      <div class="card-body">
        <div class="card-title">${a.titre}</div>
        ${extra ? `<div class="card-extra">${extra}</div>` : ''}
        <div class="card-meta">
          <span class="card-price">${a.prix > 0 ? a.prix + ' €' : 'Gratuit'}</span>
          <span class="card-cat">${a.cat}</span>
        </div>
        <span class="card-cta">Voir l'annonce</span>
      </div>
    </a>`;
  }).join('');
}

/* ── ÉCOUTEURS DE FILTRES CATÉGORIE ── */
document.querySelectorAll('[data-cat]').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.disabled) return;
    filterCat = btn.dataset.cat;
    document.querySelectorAll('[data-cat]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateFilterCounts();
    renderGrid();
  });
});

/* ── ÉCOUTEURS DE FILTRES PLATEFORME ── */
document.querySelectorAll('[data-platform]').forEach(btn => {
  btn.addEventListener('click', () => {
    const p = btn.dataset.platform;
    if (filterPlatforms.has(p)) {
      filterPlatforms.delete(p);
      btn.classList.remove('active');
    } else {
      filterPlatforms.add(p);
      btn.classList.add('active');
    }
    // Si un filtre de catégorie actif donne 0 résultats → reset sur "tous"
    const activeCount = articles.filter(a =>
      (filterCat === 'tous' || a.cat === filterCat) &&
      (filterPlatforms.size === 0 || filterPlatforms.has(a.platform))
    ).length;
    if (activeCount === 0 && filterCat !== 'tous') {
      filterCat = 'tous';
      document.querySelectorAll('[data-cat]').forEach(b => b.classList.remove('active'));
      document.querySelector('[data-cat="tous"]').classList.add('active');
    }
    updateFilterCounts();
    renderGrid();
  });
});

loadData();

/* ── MENU HAMBURGER ── */
(function () {
  const btn = document.getElementById('hamburger-btn');
  const nav = document.getElementById('mobile-nav');
  if (!btn || !nav) return;

  let ignoreScroll = false;

  function openMenu() {
    btn.classList.add('open');
    nav.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    nav.setAttribute('aria-hidden', 'false');
    ignoreScroll = true;
    setTimeout(() => { ignoreScroll = false; }, 350);
  }

  function closeMenu() {
    btn.classList.remove('open');
    nav.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    nav.setAttribute('aria-hidden', 'true');
  }

  btn.addEventListener('click', () => {
    btn.classList.contains('open') ? closeMenu() : openMenu();
  });

  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('click', (e) => {
    if (nav.classList.contains('open') && !nav.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
      closeMenu();
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) closeMenu();
  });

  window.addEventListener('scroll', () => {
    if (!ignoreScroll && nav.classList.contains('open')) closeMenu();
  }, { passive: true });
})();
