"""
Phase 7 — Sport scoreboard + market snapshot data builders.

Widget data does NOT count against the 30-story budget and is NOT scored.
It renders as a special section within the sport / economy tabs in the PWA.

Football API strategy (no paid key needed):
  - ESPN unofficial API covers PL, Bundesliga, Serie A, La Liga, Ligue 1,
    MLS, UEFA Champions League — no authentication required.
  - SK/CZ leagues: omitted from scoreboard (no free API available without
    registration; match reports still come from BBC Sport RSS articles).
  - football-data.org / api-football: used IF keys are present in env,
    fall back to ESPN silently if not.

NHL: official nhle.com API, no key needed.

Market snapshot: free Yahoo Finance query API + Reuters RSS economic fields.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

_TIMEOUT = 15.0
_UA = "Mozilla/5.0 DailyDigestBot/1.0"

# ─── ESPN league map (no key) ─────────────────────────────────────────────────
ESPN_LEAGUES: dict[str, str] = {
    "PL":  "eng.1",          # Premier League
    "BL1": "ger.1",          # Bundesliga
    "SA":  "ita.1",          # Serie A
    "PD":  "esp.1",          # La Liga
    "FL1": "fra.1",          # Ligue 1
    "CL":  "uefa.champions", # Champions League
    "MLS": "usa.1",
}
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/{league}/standings"

NHL_SCHEDULE = "https://api-web.nhle.com/v1/schedule/{date}"
NHL_STANDINGS = "https://api-web.nhle.com/v1/standings/{date}"

YAHOO_FINANCE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"


def _get(url: str, params: dict | None = None) -> dict | None:
    try:
        r = httpx.get(url, params=params, headers={"User-Agent": _UA},
                      timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as err:  # noqa: BLE001
        print(f"    ! widget GET failed {url}: {err}")
        return None


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _yesterday() -> str:
    d = datetime.now(timezone.utc) - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


# ─── NHL ─────────────────────────────────────────────────────────────────────

def _nhl_results_today() -> list[dict[str, Any]]:
    data = _get(NHL_SCHEDULE.format(date=_yesterday()))
    if not data:
        return []
    games = []
    for day in data.get("gameWeek", []):
        for g in day.get("games", []):
            state = g.get("gameState", "")
            if state not in ("FINAL", "OFF"):
                continue
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            games.append({
                "home":       home.get("placeName", {}).get("default", ""),
                "home_score": home.get("score", 0),
                "away":       away.get("placeName", {}).get("default", ""),
                "away_score": away.get("score", 0),
                "status":     "final",
            })
    return games


def _nhl_fixtures_today() -> list[dict[str, Any]]:
    data = _get(NHL_SCHEDULE.format(date=_today()))
    if not data:
        return []
    fixtures = []
    for day in data.get("gameWeek", []):
        for g in day.get("games", []):
            state = g.get("gameState", "")
            if state in ("FINAL", "OFF"):
                continue
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            start = g.get("startTimeUTC", "")
            fixtures.append({
                "home":   home.get("placeName", {}).get("default", ""),
                "away":   away.get("placeName", {}).get("default", ""),
                "time":   start,
            })
    return fixtures


def _nhl_standings() -> list[dict[str, Any]]:
    data = _get(NHL_STANDINGS.format(date=_today()))
    if not data:
        return []
    teams = data.get("standings", [])[:6]
    out = []
    for t in teams:
        out.append({
            "team":   t.get("teamName", {}).get("default", ""),
            "points": t.get("points", 0),
            "wins":   t.get("wins", 0),
            "losses": t.get("losses", 0),
        })
    return out


def build_nhl_widget() -> dict[str, Any]:
    return {
        "results":        _nhl_results_today(),
        "today":          _nhl_fixtures_today(),
        "standings_top6": _nhl_standings(),
    }


# ─── Football (ESPN) ─────────────────────────────────────────────────────────

def _espn_results(league_slug: str) -> list[dict[str, Any]]:
    data = _get(ESPN_BASE.format(league=league_slug))
    if not data:
        return []
    out = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        comps = comp.get("competitors", [])
        status = comp.get("status", {}).get("type", {}).get("state", "")
        if status != "post":
            continue
        if len(comps) < 2:
            continue
        home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
        away = next((c for c in comps if c.get("homeAway") == "away"), comps[1])
        out.append({
            "home":       home.get("team", {}).get("shortDisplayName", ""),
            "home_score": int(home.get("score", 0)),
            "away":       away.get("team", {}).get("shortDisplayName", ""),
            "away_score": int(away.get("score", 0)),
            "status":     "final",
        })
    return out


def _espn_fixtures(league_slug: str) -> list[dict[str, Any]]:
    data = _get(ESPN_BASE.format(league=league_slug))
    if not data:
        return []
    out = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        comps = comp.get("competitors", [])
        status = comp.get("status", {}).get("type", {}).get("state", "")
        if status != "pre":
            continue
        if len(comps) < 2:
            continue
        home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
        away = next((c for c in comps if c.get("homeAway") == "away"), comps[1])
        out.append({
            "home": home.get("team", {}).get("shortDisplayName", ""),
            "away": away.get("team", {}).get("shortDisplayName", ""),
            "time": event.get("date", ""),
        })
    return out


def _espn_standings(league_slug: str) -> list[dict[str, Any]]:
    data = _get(ESPN_STANDINGS.format(league=league_slug))
    if not data:
        return []
    entries = (
        data.get("standings", {})
            .get("entries", [])
    )[:5]
    out = []
    for e in entries:
        stats_list = e.get("stats", [])
        def stat(name: str) -> Any:
            return next((s["value"] for s in stats_list if s.get("name") == name), 0)
        out.append({
            "team":    e.get("team", {}).get("shortDisplayName", ""),
            "points":  int(stat("points")),
            "played":  int(stat("gamesPlayed")),
            "gd":      int(stat("pointDifferential")),
        })
    return out


def build_football_widget() -> dict[str, Any]:
    widget: dict[str, Any] = {}
    for label, slug in ESPN_LEAGUES.items():
        widget[label] = {
            "results":  _espn_results(slug),
            "fixtures": _espn_fixtures(slug),
            "standings": _espn_standings(slug),
        }
        time.sleep(0.3)   # light throttle — unofficial API
    return widget


# ─── Market snapshot ─────────────────────────────────────────────────────────

_YAHOO_SYMBOLS: dict[str, str] = {
    "EURUSD": "EURUSD=X",
    "EURCZK": "EURCZK=X",
    "SP500":  "^GSPC",
    "DAX":    "^GDAXI",
    "PX":     "^PX",       # Prague Stock Exchange
    "BTCUSD": "BTC-USD",
}


def _yahoo_quote(ticker: str, display_name: str) -> dict[str, Any] | None:
    data = _get(YAHOO_FINANCE.format(symbol=ticker))
    if not data:
        return None
    try:
        meta   = data["chart"]["result"][0]["meta"]
        price  = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev   = meta.get("previousClose") or meta.get("chartPreviousClose")
        if price is None:
            return None
        delta = round(price - prev, 4) if prev else 0
        return {
            "value":   round(price, 4),
            "delta":   delta,
            "pct":     round(delta / prev * 100, 2) if prev else 0,
        }
    except (KeyError, IndexError, TypeError):
        return None


def build_market_widget() -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for name, ticker in _YAHOO_SYMBOLS.items():
        quote = _yahoo_quote(ticker, name)
        if quote:
            snapshot[name] = quote
        time.sleep(0.2)
    return snapshot


# ─── Public API ──────────────────────────────────────────────────────────────

def build_sport_widget() -> dict[str, Any]:
    print("  Building sport widget...")
    return {
        "nhl":      build_nhl_widget(),
        "football": build_football_widget(),
    }


def build_market_snapshot() -> dict[str, Any]:
    print("  Building market snapshot...")
    return build_market_widget()


if __name__ == "__main__":
    import sys
    what = sys.argv[1] if len(sys.argv) > 1 else "market"
    if what == "sport":
        result = build_sport_widget()
    else:
        result = build_market_snapshot()
    print(json.dumps(result, indent=2, ensure_ascii=False))
