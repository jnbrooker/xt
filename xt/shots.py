"""Shots, goals and (Opta) xG from FotMob's public match API."""

import json
from datetime import datetime
from urllib.request import Request, urlopen

API = "https://www.fotmob.com/api/data"
PREMIER_LEAGUE = 47


def _get(path: str) -> dict:
    req = Request(f"{API}/{path}", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as r:
        return json.load(r)


def _same_team(whoscored: str, fotmob: str) -> bool:
    # "Brighton" vs "Brighton & Hove Albion", "Tottenham" vs "Tottenham Hotspur", ...
    return set(whoscored.lower().split()) <= set(fotmob.lower().split())


def find_match(kickoff: datetime, home: str, away: str) -> int | None:
    day = _get(f"matches?date={kickoff:%Y%m%d}")
    for league in day.get("leagues", []):
        if league.get("primaryId") != PREMIER_LEAGUE:
            continue
        for m in league["matches"]:
            if _same_team(home, m["home"]["longName"]) and _same_team(away, m["away"]["longName"]):
                return m["id"]
    return None


def fotmob_match(kickoff: datetime, home: str, away: str) -> dict | None:
    """Live score, clock and every shot (side, Opta event id, player, xG, goal).

    FotMob's scoreboard runs ahead of WhoScored's, so pages prefer it. Returns None if
    FotMob can't be reached or the match isn't found, so pages fall back to WhoScored.
    """
    try:
        fotmob_id = find_match(kickoff, home, away)
        if fotmob_id is None:
            return None
        details = _get(f"matchDetails?matchId={fotmob_id}")
    except (OSError, ValueError, KeyError):
        return None
    teams, status = details["header"]["teams"], details["header"]["status"]
    home_id = teams[0]["id"]
    shotmap = details.get("content", {}).get("shotmap") or {}
    # liveTime.short looks like "80‎’‎"; keep just "80'" (or "HT")
    clock = (status.get("liveTime") or {}).get("short", "").replace("‎", "").replace("’", "'")
    return {
        "home_score": teams[0].get("score"),
        "away_score": teams[1].get("score"),
        "elapsed": "FT" if status.get("finished") else clock,
        "finished": bool(status.get("finished")),
        "shots": _shots(shotmap, home_id),
    }


def _shots(shotmap: dict, home_id: int) -> list[dict]:
    return [
        {
            "event_id": s["id"],
            "player": s["playerName"],
            "side": "home" if s["teamId"] == home_id else "away",
            "xg": s.get("expectedGoals") or 0.0,
            "goal": s["eventType"] == "Goal" and not s.get("isOwnGoal"),
            "own_goal": bool(s.get("isOwnGoal")),
        }
        for s in shotmap.get("shots", [])
    ]
