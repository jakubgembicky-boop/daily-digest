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
from dateutil import parser as dateparser

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

# International tournaments, checked in priority order. When one of these is
# actively running, it REPLACES the club leagues in the scoreboard (club
# competitions are on their summer break during major international tournaments).
ESPN_TOURNAMENTS: list[tuple[str, str]] = [
    ("fifa.world",        "FIFA World Cup"),
    ("uefa.euro",         "UEFA Euro"),
    ("conmebol.america",  "Copa América"),
    ("fifa.wwc",          "FIFA Women's World Cup"),
]
# A tournament counts as "active" if it has a match within this window of today.
_TOURNAMENT_LOOKBACK_DAYS = 3
_TOURNAMENT_LOOKAHEAD_DAYS = 12

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
                "date":       (g.get("gameDate") or g.get("startTimeUTC", ""))[:10],
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
                "date":   (g.get("gameDate") or start)[:10],
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

def _team_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team", {})
    return (team.get("shortDisplayName")
            or team.get("displayName")
            or team.get("abbreviation")
            or "")


def _parse_espn_scoreboard(
    data: dict | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split one ESPN scoreboard payload into finished results + upcoming fixtures.

    Returns (results, fixtures). Each result/fixture carries a `date`
    (YYYY-MM-DD); fixtures also carry an ISO `time` so the PWA can show when a
    match is/was played.
    """
    results: list[dict[str, Any]] = []
    fixtures: list[dict[str, Any]] = []
    if not data:
        return results, fixtures

    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        comps = comp.get("competitors", [])
        if len(comps) < 2:
            continue
        state = comp.get("status", {}).get("type", {}).get("state", "")
        iso = event.get("date", "") or comp.get("date", "")
        day = iso[:10] if iso else ""
        home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
        away = next((c for c in comps if c.get("homeAway") == "away"), comps[1])

        if state == "post":
            results.append({
                "date":       day,
                "home":       _team_name(home),
                "home_score": int(home.get("score", 0) or 0),
                "away":       _team_name(away),
                "away_score": int(away.get("score", 0) or 0),
                "status":     "final",
            })
        elif state in ("pre", "in"):
            fixtures.append({
                "date":   day,
                "time":   iso,
                "home":   _team_name(home),
                "away":   _team_name(away),
                "live":   state == "in",
            })
    return results, fixtures


def _event_within_window(data: dict | None) -> bool:
    """True if the payload has any match within the active-tournament window."""
    if not data:
        return False
    now = datetime.now(timezone.utc)
    lo = now - timedelta(days=_TOURNAMENT_LOOKBACK_DAYS)
    hi = now + timedelta(days=_TOURNAMENT_LOOKAHEAD_DAYS)
    for event in data.get("events", []):
        iso = event.get("date", "")
        if not iso:
            continue
        try:
            dt = dateparser.parse(iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if lo <= dt <= hi:
            return True
    return False


def _active_tournament() -> tuple[str, str, dict] | None:
    """Return (slug, display_name, raw_payload) for an active tournament, else None."""
    for slug, name in ESPN_TOURNAMENTS:
        data = _get(ESPN_BASE.format(league=slug))
        time.sleep(0.3)
        if _event_within_window(data):
            return slug, name, data
    return None


def build_football_widget() -> dict[str, Any]:
    """Football scoreboard.

    During a major international tournament (e.g. the World Cup), the domestic
    club leagues are on break, so we show the tournament instead. Otherwise we
    show the club leagues and silently drop any that are off-season (no recent
    results AND no upcoming fixtures).
    """
    tour = _active_tournament()
    if tour:
        slug, name, data = tour
        results, fixtures = _parse_espn_scoreboard(data)
        print(f"    tournament mode: {name} "
              f"({len(results)} results, {len(fixtures)} fixtures)")
        return {
            "mode":        "tournament",
            "competition": name,
            "sections": [{
                "code":     slug,
                "name":     name,
                "results":  results[:12],
                "fixtures": fixtures[:12],
            }],
        }

    sections: list[dict[str, Any]] = []
    for label, slug in ESPN_LEAGUES.items():
        results, fixtures = _parse_espn_scoreboard(_get(ESPN_BASE.format(league=slug)))
        time.sleep(0.3)   # light throttle — unofficial API
        if not results and not fixtures:
            continue      # league on break — don't show an empty card
        sections.append({
            "code":     label,
            "name":     label,
            "results":  results[:5],
            "fixtures": fixtures[:5],
        })
    return {"mode": "leagues", "sections": sections}


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
