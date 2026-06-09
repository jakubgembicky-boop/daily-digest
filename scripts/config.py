"""
Central configuration: categories, sources, scoring constants, learning domains.
All source lists, category metadata, and tuning knobs live here.
"""

# ─── Category metadata ────────────────────────────────────────────────────────
# Keys are used as category IDs throughout the pipeline.
# 'language' controls translation enforcement (sk/cs are NEVER translated).

CATEGORIES = {
    "slovakia": {
        "label":    "Slovakia",
        "emoji":    "🇸🇰",
        "accent":   "#0080C7",
        "language": "sk",   # preserve — never translate
    },
    "czechia": {
        "label":    "Czechia",
        "emoji":    "🇨🇿",
        "accent":   "#B45309",
        "language": "cs",   # preserve — never translate
    },
    "europe": {
        "label":    "Europe & Defense",
        "emoji":    "🇪🇺",
        "accent":   "#003399",
        "language": "en",
    },
    "war": {
        "label":    "Ukraine–Russia War",
        "emoji":    "🔴",
        "accent":   "#CC2222",
        "language": "en",
    },
    "sport": {
        "label":    "Sport",
        "emoji":    "🏒⚽",
        "accent":   "#1DB954",
        "language": "en",
    },
    "global": {
        "label":    "Global",
        "emoji":    "🌍",
        "accent":   "#F59E0B",
        "language": "en",
    },
    "tech": {
        "label":    "Tech",
        "emoji":    "💻",
        "accent":   "#7C3AED",
        "language": "en",
    },
    "economy": {
        "label":    "Economy & Finance",
        "emoji":    "📈",
        "accent":   "#6B7280",
        "language": "en",
    },
    "hr": {
        "label":    "HR & Management",
        "emoji":    "👥",
        "accent":   "#0891B2",
        "language": "en",
    },
    "health": {
        "label":    "Health & Lifestyle",
        "emoji":    "🏃",
        "accent":   "#059669",
        "language": "en",
    },
    "random": {
        "label":    "Random",
        "emoji":    "🎲",
        "accent":   "#EC4899",
        "language": "en",
    },
    "learning": {
        "label":    "Learning",
        "emoji":    "📚",
        "accent":   "#6366F1",
        "language": "en",
    },
}

# Tab order for the PWA (Today is synthetic, not a category)
TAB_ORDER = [
    "slovakia", "czechia", "europe", "war",
    "sport", "global", "tech", "economy",
    "hr", "health", "random", "learning",
]

# ─── Scoring constants ────────────────────────────────────────────────────────
SCORE_IMPORTANCE_WEIGHT  = 0.45
SCORE_RELEVANCE_WEIGHT   = 0.45
SCORE_BREAKING_BONUS     = 1.0
MONTHLY_FLOOR_THRESHOLD  = 0.05   # category below 5% share gets a boost
MONTHLY_FLOOR_MAX_BOOST  = 0.5    # max boost — never overrides a breaking story
TARGET_STORIES           = 30
GROQ_DELAY_SECONDS       = 2      # between Groq calls — 30 RPM free limit

# ─── User profile (fed into relevance scoring prompt) ────────────────────────
USER_PROFILE = (
    "MBA student at INSEAD; Slovak national living in Central Europe; "
    "HR/CHRO professional and consultant; interested in tech trends, "
    "health optimization, global geopolitics, Central European affairs, "
    "leadership, and behavioral science."
)

# ─── Groq models ─────────────────────────────────────────────────────────────
GROQ_PRIMARY_MODEL  = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

# ─── Sources ──────────────────────────────────────────────────────────────────
# Fields:
#   name            display name
#   url             RSS/Atom URL (None for pure-API sources)
#   category        one of CATEGORIES keys
#   type            "rss" | "guardian" | "hackernews" | "nhl" |
#                   "football_data" | "api_football"
#   is_subscription True if article likely paywalled (shown as 💎 in UI)
#   params          extra dict for API-type sources

SOURCES = [

    # ── Slovakia (5) ─────────────────────────────────────────────────────────
    {
        "name": "Denník N",
        "url": "https://dennikn.sk/feed/",
        "category": "slovakia", "type": "rss", "is_subscription": True,
        "params": {},
    },
    {
        "name": "Aktuality.sk",
        "url": "https://www.aktuality.sk/rss/",
        "category": "slovakia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "SME.sk",
        "url": "https://www.sme.sk/rss/",
        "category": "slovakia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Slovak Spectator",
        "url": "https://spectator.sme.sk/rss/",
        "category": "slovakia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Pravda.sk",
        "url": "https://spravy.pravda.sk/rss/xml/",
        "category": "slovakia", "type": "rss", "is_subscription": False,
        "params": {},
    },

    # ── Czechia (5) — FREE only, Czech preserved ──────────────────────────────
    {
        "name": "ČT24",
        "url": "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy",
        "category": "czechia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "iROZHLAS.cz",
        "url": "https://www.irozhlas.cz/rss/irozhlas",
        "category": "czechia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "iDnes.cz",
        "url": "https://servis.idnes.cz/rss.aspx",
        "category": "czechia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Novinky.cz",
        "url": "https://www.novinky.cz/rss2/",
        "category": "czechia", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Aktuálně.cz",
        "url": "https://aktualne.cz/rss/",
        "category": "czechia", "type": "rss", "is_subscription": False,
        "params": {},
    },

    # ── Europe & Defense (8) ─────────────────────────────────────────────────
    {
        "name": "BBC Europe",
        "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "EUobserver",
        "url": "https://euobserver.com/rss",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Politico Europe",
        "url": "https://www.politico.eu/feed/",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Deutsche Welle",
        "url": "https://rss.dw.com/rdf/rss-en-eu",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Guardian",
        "url": None,
        "category": "europe", "type": "guardian", "is_subscription": False,
        "params": {"section": "world", "q": "europe"},
    },
    {
        "name": "Defense News",
        "url": "https://www.defensenews.com/arc/outboundfeeds/rss/",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "War on the Rocks",
        "url": "https://warontherocks.com/feed",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Breaking Defense",
        "url": "https://breakingdefense.com/feed/",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Der Spiegel International",
        "url": "https://www.spiegel.de/international/index.rss",
        "category": "europe", "type": "rss", "is_subscription": False,
        "params": {},
    },

    # ── Ukraine–Russia War (4) ────────────────────────────────────────────────
    {
        "name": "Ukrainska Pravda",
        "url": "https://www.pravda.com.ua/eng/rss/view_news/",
        "category": "war", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "RFE/RL Ukraine",
        "url": "https://www.rferl.org/api/zrqotpumit",
        "category": "war", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Reuters World",
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "category": "war", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Guardian",
        "url": None,
        "category": "war", "type": "guardian", "is_subscription": False,
        "params": {"q": "ukraine OR russia", "section": "world"},
    },

    # ── Sport (4 RSS + 4 API — scores always paired with match report) ────────
    # Data APIs (handled in widgets.py, not scored through pipeline)
    {
        "name": "NHL",
        "url": None,
        "category": "sport", "type": "nhl", "is_subscription": False,
        "params": {},
    },
    {
        "name": "football-data.org",
        "url": None,
        "category": "sport", "type": "football_data", "is_subscription": False,
        "params": {"competitions": ["PL", "BL1", "SA", "PD", "FL1", "CL", "MLS"]},
    },
    {
        "name": "API-Football SK",
        "url": None,
        "category": "sport", "type": "api_football", "is_subscription": False,
        "params": {"league_id": 332},
    },
    {
        "name": "API-Football CZ",
        "url": None,
        "category": "sport", "type": "api_football", "is_subscription": False,
        "params": {"league_id": 345},
    },
    # Editorial / match reports (go through scoring pipeline)
    {
        "name": "BBC Sport",
        "url": "https://feeds.bbci.co.uk/sport/rss.xml",
        "category": "sport", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "BBC Football",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "category": "sport", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "BBC Tennis",
        "url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
        "category": "sport", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Guardian",
        "url": None,
        "category": "sport", "type": "guardian", "is_subscription": False,
        "params": {"section": "sport"},
    },

    # ── Global (7) ────────────────────────────────────────────────────────────
    {
        "name": "The Guardian",
        "url": None,
        "category": "global", "type": "guardian", "is_subscription": False,
        "params": {"section": "world,politics,business", "page-size": 12},
    },
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "global", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Reuters World",
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "category": "global", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "AP Top News",
        "url": "https://apnews.com/apf-topnews?format=rss",
        "category": "global", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "AP International",
        "url": "https://apnews.com/apf-intlnews?format=rss",
        "category": "global", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "WSJ World",
        "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        "category": "global", "type": "rss", "is_subscription": True,
        "params": {},
    },
    {
        "name": "WSJ Markets",
        "url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "category": "global", "type": "rss", "is_subscription": True,
        "params": {},
    },
    {
        "name": "FT International",
        "url": "https://www.ft.com/rss/home/international",
        "category": "global", "type": "rss", "is_subscription": True,
        "params": {},
    },
    {
        "name": "The Atlantic",
        "url": "https://www.theatlantic.com/feed/all/",
        "category": "global", "type": "rss", "is_subscription": True,
        "params": {},
    },

    # ── Economy & Finance (8 + WSJ/FT cross-ref from Global) ─────────────────
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "AP Business",
        "url": "https://apnews.com/apf-business?format=rss",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "CNBC",
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Project Syndicate",
        "url": "https://www.project-syndicate.org/rss",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # bne IntelliNews feed times out — dropped

    {
        "name": "Emerging Europe",
        "url": "https://emerging-europe.com/feed/",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # Euractiv blocks scrapers (403) — dropped

    {
        "name": "HNonline.sk",
        "url": "https://hnonline.sk/rss",
        "category": "economy", "type": "rss", "is_subscription": False,
        "params": {},
    },

    # ── Tech (20) ─────────────────────────────────────────────────────────────
    # News & analysis
    {
        "name": "Hacker News",
        "url": None,
        "category": "tech", "type": "hackernews", "is_subscription": False,
        "params": {"min_score": 100},
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Engadget",
        "url": "https://www.engadget.com/rss.xml",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "TechRadar",
        "url": "https://www.techradar.com/rss",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Register",
        "url": "https://www.theregister.com/headlines.atom",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Guardian",
        "url": None,
        "category": "tech", "type": "guardian", "is_subscription": False,
        "params": {"section": "technology"},
    },
    # Hardware & reviews
    {
        "name": "Tom's Hardware",
        "url": "https://www.tomshardware.com/feeds/all",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Tom's Guide",
        "url": "https://www.tomsguide.com/feeds/all",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # NotebookCheck RSS gone (404) — dropped
    # PCMag blocks scrapers (403) — dropped
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "CNET",
        "url": "https://www.cnet.com/rss/news/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Trusted Reviews",
        "url": "https://www.trustedreviews.com/feed",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # Audio & AV
    {
        "name": "What Hi-Fi",
        "url": "https://www.whathifi.com/feeds/all",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "SoundGuys",
        "url": "https://www.soundguys.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Headfonics",
        "url": "https://headfonics.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # Mobile
    {
        "name": "9to5Mac",
        "url": "https://9to5mac.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Android Authority",
        "url": "https://www.androidauthority.com/feed/",
        "category": "tech", "type": "rss", "is_subscription": False,
        "params": {},
    },

    # ── HR & Management (15) ──────────────────────────────────────────────────
    # HR trade
    {
        "name": "HR Dive",
        "url": "https://www.hrdive.com/feeds/news/",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # SHRM RSS gone (404) — dropped
    # People Management no RSS feed — dropped
    # CIPD RSS gone (all 404) — dropped
    # Leadership
    {
        "name": "Harvard Business Review",
        "url": "https://feeds.hbr.org/harvardbusiness",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "MIT Sloan",
        "url": "https://sloanreview.mit.edu/feed/",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "McKinsey Insights",
        "url": "https://www.mckinsey.com/rss/",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Strategy+Business",
        "url": "https://www.strategy-business.com/rss",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # Future of work
    # Gallup RSS gone (404) — dropped
    # Deloitte Insights RSS gone (404) — dropped
    {
        "name": "Fast Company",
        "url": "https://www.fastcompany.com/rss",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # Knowledge@Wharton blocks scrapers (403) — dropped
    # Business
    {
        "name": "Inc. Magazine",
        "url": "https://www.inc.com/rss/",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/money/work-and-careers/rss",
        "category": "hr", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "The Economist",
        "url": "https://www.economist.com/business/rss.xml",
        "category": "hr", "type": "rss", "is_subscription": True,
        "params": {},
    },

    # ── Health & Lifestyle (8) ────────────────────────────────────────────────
    {
        "name": "BBC Health",
        "url": "https://feeds.bbci.co.uk/news/health/rss.xml",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "BBC Science",
        "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
    # NIH News blocks scrapers (403) — dropped
    {
        "name": "The Guardian",
        "url": None,
        "category": "health", "type": "guardian", "is_subscription": False,
        "params": {"section": "science"},
    },
    {
        "name": "Peter Attia",
        "url": "https://peterattiamd.com/feed/",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Outside Online",
        "url": "https://www.outsideonline.com/feed/",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Men's Health",
        "url": "https://www.menshealth.com/rss/",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
    {
        "name": "Psychology Today",
        "url": "https://www.psychologytoday.com/us/front/feed",
        "category": "health", "type": "rss", "is_subscription": False,
        "params": {},
    },
]

# ─── Random sources (separate pool — not scored through main pipeline) ────────
# Used exclusively by generate.py to pick today's surprise article.
RANDOM_SOURCES = [
    {
        "name": "Quanta Magazine",
        "url": "https://www.quantamagazine.org/feed/",
    },
    {
        "name": "Aeon",
        "url": "https://aeon.co/feed.rss",
    },
    {
        "name": "Nautilus",
        "url": "https://nautil.us/feed/",
    },
    {
        "name": "Atlas Obscura",
        "url": "https://www.atlasobscura.com/feeds/latest",
    },
    {
        "name": "The Marginalian",       # was Brain Pickings — culture/science/art/philosophy
        "url": "https://www.themarginalian.org/feed/",
    },
    {
        "name": "Open Culture",          # art, music, world culture, curious history
        "url": "https://www.openculture.com/feed",
    },
    {
        "name": "Damn Interesting",      # fascinating true stories from history & science
        "url": "https://www.damninteresting.com/feed/",
    },
]

# ─── Learning sources (separate pool — not scored through main pipeline) ──────
# Used by generate.py to pick today's "explainer" article: a real piece from a
# quality source that explains an interesting concept clearly. Evergreen is fine
# — it does NOT need to be recent — but it should feel new to the reader.
# No recency filter is applied to this pool (unlike the main news pool).
LEARNING_SOURCES = [
    {"name": "Harvard Business Review", "url": "https://feeds2.feedburner.com/harvardbusiness"},   # feedburner mirror works; feeds.hbr.org has SSL issues
    {"name": "The Guardian — Long Read", "url": "https://www.theguardian.com/news/series/the-long-read/rss"},
    {"name": "Aeon",                     "url": "https://aeon.co/feed.rss"},
    {"name": "Psyche",                   "url": "https://psyche.co/feed"},
    {"name": "Nautilus",                 "url": "https://nautil.us/feed/"},
    {"name": "The Atlantic — Ideas",     "url": "https://www.theatlantic.com/feed/channel/ideas/"},
    {"name": "MIT Sloan Review",         "url": "https://sloanreview.mit.edu/feed/"},
    {"name": "Longreads",                "url": "https://longreads.com/feed/"},                    # replaced Wharton (403)
    {"name": "The Conversation",         "url": "https://theconversation.com/articles.atom"},
    {"name": "Big Think",                "url": "https://bigthink.com/feed/"},
    {"name": "Farnam Street",            "url": "https://fs.blog/feed/"},
    {"name": "Undark",                   "url": "https://undark.org/feed/"},                       # science journalism / explainers
]

# ─── Learning domains (soft-preference rotation, by day-of-year mod len) ──────
# With real-article selection, these act as a *steering hint* for the AI: prefer
# an article touching today's domain if a good one exists; otherwise pick the
# best explainer available. Not a hard filter.
LEARNING_DOMAINS = [
    "behavioral economics",
    "physics",
    "evolutionary biology",
    "cognitive psychology",
    "philosophy of mind",
    "history of science",
    "political theory",
    "linguistics",
    "game theory",
    "information theory",
    "neuroscience",
    "climate science",
    "sociology",
    "mathematics",
    "philosophy of language",
    "systems thinking",
    "ancient history",
    "economics",
    "anthropology",
    "logic",
]

# ─── Sport widget config ──────────────────────────────────────────────────────
# Competitions tracked via football-data.org (free tier)
FOOTBALL_COMPETITIONS = ["PL", "BL1", "SA", "PD", "FL1", "CL", "MLS"]
# RapidAPI league IDs for SK/CZ via api-football
FOOTBALL_SK_LEAGUE_ID = 332
FOOTBALL_CZ_LEAGUE_ID = 345
# NHL API base (no key needed)
NHL_API_BASE = "https://api-web.nhle.com/v1"

# ─── Market snapshot tickers (for economy widget) ────────────────────────────
# Displayed in economy tab; sourced from RSS economic data fields
MARKET_TICKERS = ["EURUSD", "EURCZK", "SP500", "DAX", "PX", "BTCUSD"]

# ─── Convenience helpers ──────────────────────────────────────────────────────

def sources_for_category(cat: str) -> list[dict]:
    """Return all sources whose category matches `cat`."""
    return [s for s in SOURCES if s["category"] == cat]


def rss_sources() -> list[dict]:
    """Return all RSS/Atom sources (type == 'rss')."""
    return [s for s in SOURCES if s["type"] == "rss"]


def api_sources() -> list[dict]:
    """Return all non-RSS sources (Guardian, HN, sports APIs)."""
    return [s for s in SOURCES if s["type"] != "rss"]
