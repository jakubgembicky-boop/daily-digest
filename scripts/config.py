"""
Central configuration for the Daily Digest Claude Routine.

Claude handles all categorisation, clustering, scoring and summarisation —
so the old pipeline constants (scoring weights, Groq models, etc.) are gone.
What remains is the source registry, category metadata, and widget settings.
"""

# ─── User profile (passed to Claude for relevance tuning) ─────────────────────
USER_PROFILE = (
    "MBA student at INSEAD; Slovak national living in Central Europe; "
    "HR/CHRO professional and consultant; interested in AI and tech trends, "
    "health optimisation, global geopolitics, Central European affairs, "
    "leadership, and behavioural science."
)

# ─── Categories ───────────────────────────────────────────────────────────────
CATEGORIES: dict[str, dict] = {
    "slovakia": {"label": "Slovakia",          "emoji": "🇸🇰", "accent": "#0080C7", "lang": "sk"},
    "czechia":  {"label": "Czechia",           "emoji": "🇨🇿", "accent": "#B45309", "lang": "cs"},
    "europe":   {"label": "Europe & Defence",  "emoji": "🇪🇺", "accent": "#003399", "lang": "en"},
    "war":      {"label": "War & Conflict",    "emoji": "🔴",  "accent": "#CC2222", "lang": "en"},
    "sport":    {"label": "Sport",             "emoji": "🏆",  "accent": "#1DB954", "lang": "en"},
    "global":   {"label": "Global",           "emoji": "🌍",  "accent": "#F59E0B", "lang": "en"},
    "tech":     {"label": "Tech",              "emoji": "💻",  "accent": "#7C3AED", "lang": "en"},
    "ai":       {"label": "AI",                "emoji": "🤖",  "accent": "#8B5CF6", "lang": "en"},
    "economy":  {"label": "Economy & Finance", "emoji": "📈",  "accent": "#6B7280", "lang": "en"},
    "hr":       {"label": "HR & Management",   "emoji": "👥",  "accent": "#0891B2", "lang": "en"},
    "health":   {"label": "Health & Lifestyle","emoji": "🏃",  "accent": "#059669", "lang": "en"},
}

# PWA tab order (Today is synthetic — first tab, not a category)
TAB_ORDER = [
    "slovakia", "czechia", "europe", "war",
    "sport", "global", "tech", "ai",
    "economy", "hr", "health",
]

# ─── Sources ──────────────────────────────────────────────────────────────────
# paid_partner  : Denník N / NYT / FT / The Athletic
#                 Always preferred as the primary source for a story.
# paywall_only  : Paywalled sources we are NOT partners with (WSJ, Economist…).
#                 Use as secondary only; skip if a free source covers the topic.
# lang          : "sk" and "cs" content must NEVER be translated.

SOURCES: list[dict] = [

    # ── Slovakia ──────────────────────────────────────────────────────────────
    {"name": "Denník N",        "url": "https://dennikn.sk/feed/",
     "category": "slovakia", "type": "rss", "paid_partner": True,  "paywall_only": False, "lang": "sk"},
    {"name": "Aktuality.sk",    "url": "https://www.aktuality.sk/rss/",
     "category": "slovakia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "sk"},
    {"name": "TASR.sk",         "url": "https://www.tasr.sk/rss.aspx",
     "category": "slovakia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "sk"},
    {"name": "TA3",             "url": "https://www.ta3.com/rss/all.rss",
     "category": "slovakia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "sk"},
    {"name": "Pravda.sk",       "url": "https://spravy.pravda.sk/rss/xml/",
     "category": "slovakia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "sk"},

    # ── Czechia ───────────────────────────────────────────────────────────────
    {"name": "ČT24",            "url": "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy",
     "category": "czechia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "cs"},
    {"name": "iROZHLAS.cz",     "url": "https://www.irozhlas.cz/rss/irozhlas",
     "category": "czechia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "cs"},
    {"name": "iDnes.cz",        "url": "https://servis.idnes.cz/rss.aspx",
     "category": "czechia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "cs"},
    {"name": "Novinky.cz",      "url": "https://www.novinky.cz/rss2/",
     "category": "czechia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "cs"},
    {"name": "Aktuálně.cz",     "url": "https://aktualne.cz/rss/",
     "category": "czechia", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "cs"},

    # ── Europe & Defence ──────────────────────────────────────────────────────
    {"name": "BBC Europe",       "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "EUobserver",       "url": "https://euobserver.com/rss",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Politico Europe",  "url": "https://www.politico.eu/feed/",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Deutsche Welle",   "url": "https://rss.dw.com/rdf/rss-en-eu",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Defense News",     "url": "https://www.defensenews.com/arc/outboundfeeds/rss/",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "War on the Rocks", "url": "https://warontherocks.com/feed",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Breaking Defense", "url": "https://breakingdefense.com/feed/",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Der Spiegel Intl", "url": "https://www.spiegel.de/international/index.rss",
     "category": "europe", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Guardian",     "url": None,
     "category": "europe", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"section": "world", "q": "europe"}},

    # ── War & Conflict ────────────────────────────────────────────────────────
    {"name": "Ukrainska Pravda", "url": "https://www.pravda.com.ua/eng/rss/view_news/",
     "category": "war", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "RFE/RL Ukraine",   "url": "https://www.rferl.org/api/zrqotpumit",
     "category": "war", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "AP World",         "url": "https://apnews.com/apf-intlnews?format=rss",
     "category": "war", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Guardian",     "url": None,
     "category": "war", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"q": "ukraine OR russia OR conflict OR war", "section": "world"}},

    # ── Sport ─────────────────────────────────────────────────────────────────
    {"name": "BBC Sport",        "url": "https://feeds.bbci.co.uk/sport/rss.xml",
     "category": "sport", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "BBC Football",     "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
     "category": "sport", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "BBC Tennis",       "url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
     "category": "sport", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Sky Sports",       "url": "https://www.skysports.com/rss/12040",
     "category": "sport", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Guardian",     "url": None,
     "category": "sport", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"section": "sport"}},

    # ── Global ────────────────────────────────────────────────────────────────
    {"name": "BBC World",        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Al Jazeera",       "url": "https://www.aljazeera.com/xml/rss/all.xml",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "AP Top News",      "url": "https://apnews.com/apf-topnews?format=rss",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "AP International", "url": "https://apnews.com/apf-intlnews?format=rss",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "NYT World",        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
     "category": "global", "type": "rss", "paid_partner": True,  "paywall_only": False, "lang": "en"},
    {"name": "NYT US",           "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
     "category": "global", "type": "rss", "paid_partner": True,  "paywall_only": False, "lang": "en"},
    {"name": "FT World",         "url": "https://www.ft.com/rss/home/international",
     "category": "global", "type": "rss", "paid_partner": True,  "paywall_only": False, "lang": "en"},
    {"name": "WSJ World",        "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": True,  "lang": "en"},
    {"name": "The Atlantic",     "url": "https://www.theatlantic.com/feed/all/",
     "category": "global", "type": "rss", "paid_partner": False, "paywall_only": True,  "lang": "en"},
    {"name": "The Guardian",     "url": None,
     "category": "global", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"section": "world,politics", "page-size": 12}},

    # ── Economy & Finance ─────────────────────────────────────────────────────
    {"name": "Bloomberg",        "url": "https://feeds.bloomberg.com/markets/news.rss",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": True,  "lang": "en"},
    {"name": "AP Business",      "url": "https://apnews.com/apf-business?format=rss",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "CNBC",             "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "MarketWatch",      "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Project Syndicate","url": "https://www.project-syndicate.org/rss",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Emerging Europe",  "url": "https://emerging-europe.com/feed/",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Hospodárske noviny","url": "https://hn.hnonline.sk/rss",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "sk"},
    {"name": "WSJ Markets",      "url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": True,  "lang": "en"},
    {"name": "The Economist",    "url": "https://www.economist.com/business/rss.xml",
     "category": "economy", "type": "rss", "paid_partner": False, "paywall_only": True,  "lang": "en"},

    # ── Tech ──────────────────────────────────────────────────────────────────
    {"name": "Hacker News",      "url": None,
     "category": "tech", "type": "hackernews", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"min_score": 100}},
    {"name": "The Verge",        "url": "https://www.theverge.com/rss/index.xml",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Ars Technica",     "url": "https://feeds.arstechnica.com/arstechnica/index",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Wired",            "url": "https://www.wired.com/feed/rss",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Engadget",         "url": "https://www.engadget.com/rss.xml",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "TechCrunch",       "url": "https://techcrunch.com/feed/",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Register",     "url": "https://www.theregister.com/headlines.atom",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "CNET",             "url": "https://www.cnet.com/rss/news/",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Tom's Hardware",   "url": "https://www.tomshardware.com/feeds/all",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "9to5Mac",          "url": "https://9to5mac.com/feed/",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Android Authority","url": "https://www.androidauthority.com/feed/",
     "category": "tech", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Guardian Tech",    "url": None,
     "category": "tech", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"section": "technology"}},

    # ── AI ────────────────────────────────────────────────────────────────────
    {"name": "VentureBeat AI",   "url": "https://venturebeat.com/category/ai/feed/",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "MIT Tech Review AI","url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Gradient",     "url": "https://thegradient.pub/rss/",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "DeepMind Blog",    "url": "https://deepmind.google/blog/rss.xml",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Last Week in AI",  "url": "https://lastweekin.ai/feed",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "The Verge AI",     "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
     "category": "ai", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},

    # ── HR & Management ───────────────────────────────────────────────────────
    {"name": "HR Dive",          "url": "https://www.hrdive.com/feeds/news/",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Harvard Business Review","url": "https://feeds2.feedburner.com/harvardbusiness",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "MIT Sloan",        "url": "https://sloanreview.mit.edu/feed/",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "McKinsey Insights","url": "https://www.mckinsey.com/rss/",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Strategy+Business","url": "https://www.strategy-business.com/rss",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Fast Company",     "url": "https://www.fastcompany.com/rss",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Inc. Magazine",    "url": "https://www.inc.com/rss/",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Guardian Careers", "url": "https://www.theguardian.com/money/work-and-careers/rss",
     "category": "hr", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},

    # ── Health & Lifestyle ────────────────────────────────────────────────────
    {"name": "BBC Health",       "url": "https://feeds.bbci.co.uk/news/health/rss.xml",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "BBC Science",      "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Peter Attia",      "url": "https://peterattiamd.com/feed/",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Outside Online",   "url": "https://www.outsideonline.com/feed/",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Men's Health",     "url": "https://www.menshealth.com/rss/",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Psychology Today", "url": "https://www.psychologytoday.com/us/front/feed",
     "category": "health", "type": "rss", "paid_partner": False, "paywall_only": False, "lang": "en"},
    {"name": "Guardian Science", "url": None,
     "category": "health", "type": "guardian", "paid_partner": False, "paywall_only": False, "lang": "en",
     "params": {"section": "science"}},
]

# ─── Trending config ──────────────────────────────────────────────────────────
TRENDING_SUBREDDITS = ["worldnews", "europe", "technology", "economics", "sports"]
TRENDING_TOP_N      = 15    # top N posts per subreddit per day
# Keywords that indicate a story is relevant to Europe or the US
TRENDING_GEO_KEYWORDS = [
    "europe", "eu ", "european", "nato", "brussels",
    "us ", "usa", "united states", "american", "washington",
    "uk ", "britain", "british", "london",
    "germany", "france", "italy", "spain", "poland", "ukraine",
    "russia", "slovakia", "czech", "hungary", "sweden", "finland",
    "norway", "denmark", "netherlands", "belgium", "austria",
]
TRENDING_WILDCARD_MIN_SCORE = 500  # min Reddit score for wildcard slot

# ─── Sport & Market widget config ────────────────────────────────────────────
FOOTBALL_COMPETITIONS  = ["PL", "BL1", "SA", "PD", "FL1", "CL", "MLS"]
NHL_API_BASE           = "https://api-web.nhle.com/v1"
MARKET_TICKERS         = ["EURUSD", "EURCZK", "SP500", "DAX", "PX", "BTCUSD"]
MARKET_DROP_ALERT_PCT  = -1.5   # percentage drop that triggers "!" alert

# ─── Convenience helpers ──────────────────────────────────────────────────────
def rss_sources() -> list[dict]:
    return [s for s in SOURCES if s["type"] == "rss" and s.get("url")]

def guardian_sources() -> list[dict]:
    return [s for s in SOURCES if s["type"] == "guardian"]

def hackernews_sources() -> list[dict]:
    return [s for s in SOURCES if s["type"] == "hackernews"]

def article_sources() -> list[dict]:
    return [s for s in SOURCES if s["type"] in ("rss", "guardian", "hackernews")]
