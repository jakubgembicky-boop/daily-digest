# Daily Digest

Personal daily news PWA. 88 RSS/API sources → Groq AI clustering + ranking → GitHub Pages → iPhone.

Runs autonomously every morning at 05:30 UTC via GitHub Actions. No server, no subscription.

---

## Setup (one-time, ~15 minutes)

### 1. Create a GitHub repository

1. Go to [github.com](https://github.com) → **New repository**
2. Name it `daily-digest` (or anything you like)
3. Set it to **Private** (your news reading is your own business)
4. Don't initialise with a README — push the code directly

### 2. Push this code

```bash
cd daily-digest
git init
git add .
git commit -m "initial"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/daily-digest.git
git push -u origin main
```

### 3. Enable GitHub Pages

1. Repo → **Settings** → **Pages**
2. Source: **GitHub Actions** (not a branch)
3. Your PWA will be at `https://YOUR_USERNAME.github.io/daily-digest/`

### 4. Add API secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Where to get it | Required? |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys | **Yes** |
| `GUARDIAN_API_KEY` | [open-platform.theguardian.com](https://open-platform.theguardian.com/access/) | Recommended |

### 5. Run it

**Actions** tab → **Build Daily Digest** → **Run workflow**

First run takes ~5 minutes. After that it runs automatically every morning.

### 6. Add to iPhone home screen

1. Open your GitHub Pages URL in Safari
2. Tap the **Share** button → **Add to Home Screen**
3. Done — it works offline too

---

## What it does each morning

1. **Fetches** ~1,200 articles from 78 sources (RSS + APIs)
2. **Clusters** same-story articles across sources (~600 clusters)
3. **Scores** all clusters in one global pool — top 30 win (no quotas)
4. **Summarises** each story with Groq Llama 3.3 70B (free)
5. **Picks** a 🎲 Random surprise + 📚 Learning article
6. **Builds** `digest.json` + dated archive → deploys to GitHub Pages

---

## Categories

| Emoji | Category | Sources |
|---|---|---|
| 🇸🇰 | Slovakia | Denník N, Aktuality, SME, Pravda (Slovak preserved) |
| 🇨🇿 | Czechia | ČT24, iROZHLAS, iDnes, Novinky (Czech preserved) |
| 🇪🇺 | Europe & Defense | BBC, EUobserver, Politico EU, DW, Spiegel, Defense News |
| 🔴 | War | Ukrainska Pravda, RFE/RL, Reuters |
| 🏒⚽ | Sport | BBC Sport + ESPN live scores (NHL, PL, BL1, SA, La Liga…) |
| 🌍 | Global | BBC, Guardian, WSJ, FT, Reuters, AP, The Atlantic |
| 💻 | Tech | Verge, Ars Technica, Wired, HN, MIT Tech Review + 15 more |
| 📈 | Economy | Reuters, CNBC, MarketWatch, FT, Project Syndicate + market snapshot |
| 👥 | HR & Management | HBR, McKinsey, MIT Sloan, Fast Company, HR Dive |
| 🏃 | Health | BBC Health/Science, Peter Attia, Outside, Men's Health |
| 🎲 | Random | Quanta, Aeon, Nautilus, Atlas Obscura, Smithsonian, Kottke |
| 📚 | Learning | HBR Long Read, Guardian Long Read, Aeon, Farnam Street |

---

## API keys — all free

| Key | Free tier |
|---|---|
| Groq | 1,000 req/day · 30 RPM · 6,000 TPM |
| Guardian | Unlimited reads, rate-limited |

NHL scores and ESPN football data need no key.

---

## Local development

```bash
pip install -r requirements.txt

# Set keys
export GROQ_API_KEY=gsk_...
export GUARDIAN_API_KEY=...

# Full run
python scripts/main.py

# Dry-run (no Groq calls, fast)
python scripts/main.py --dry-run

# Serve PWA locally
cd pwa && python -m http.server 8000
# open http://localhost:8000
```

---

## Architecture

```
GitHub Actions (05:30 UTC)
  └─ scripts/main.py
       ├─ fetch.py      → 78 sources, concurrent, image extraction
       ├─ cluster.py    → Groq: same-story grouping per category
       ├─ score.py      → Global pool, importance×0.45 + relevance×0.45
       ├─ process.py    → Groq: per-source summaries + synthesis
       ├─ widgets.py    → NHL + ESPN scores + Yahoo Finance market data
       ├─ generate.py   → Groq: Random surprise + Learning article
       ├─ build.py      → digest.json + pwa/digests/YYYY-MM-DD.json
       └─ stats.py      → monthly_stats.json (floor boost, no-zero rule)

pwa/
  ├─ index.html + app.js + style.css  (vanilla JS, no framework)
  ├─ sw.js          → offline cache
  └─ digests/       → 30-day calendar history
```
