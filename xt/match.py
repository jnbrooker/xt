"""Fetch a WhoScored match and value every ball-progressing action with xT."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import soccerdata as sd
import socceraction.spadl as spadl
from socceraction import xthreat

ROOT = Path(__file__).resolve().parent.parent
GRID = ROOT / "data" / "xt_grid_12x8.json"  # Karun Singh's open 12x8 xT surface
LEAGUE = "ENG-Premier League"


def scraper(season: str) -> sd.WhoScored:
    # WhoScored blocks headless browsers, so a Chrome window flashes up while fetching
    return sd.WhoScored(leagues=LEAGUE, seasons=season, headless=False)


def schedule(season: str) -> pd.DataFrame:
    return scraper(season).read_schedule(force_cache=False).reset_index(drop=True)


def is_finished(row: pd.Series) -> bool:
    return str(row.get("elapsed", "")).upper() == "FT"


def has_started(row: pd.Series) -> bool:
    return pd.notna(row.get("home_score")) or is_finished(row)


def build_match(row: pd.Series, season: str) -> dict:
    """Return everything a match page needs, as plain JSON-able data."""
    game_id = int(row.game_id)
    live = not is_finished(row)
    actions = scraper(season).read_events(match_id=game_id, live=live, output_fmt="spadl")
    actions = spadl.add_names(actions)

    home_id = int(row.home_team_id)
    # xT assumes the acting team attacks left to right
    ltr = spadl.play_left_to_right(actions, home_id)
    model = xthreat.load_model(str(GRID))
    ltr["xt"] = model.rate(ltr)

    moves = ltr[ltr.xt.notna()].copy()
    moves["side"] = np.where(moves.team_id == home_id, "home", "away")
    moves["kind"] = np.where(moves.type_name == "dribble", "carry", "pass")
    moves["minute"] = (moves.time_seconds // 60 + np.where(moves.period_id == 2, 45, 0)).astype(int) + 1

    moves["xt_pass"] = moves.xt.where(moves.kind == "pass", 0.0)
    moves["xt_carry"] = moves.xt.where(moves.kind == "carry", 0.0)
    players = (
        moves.groupby(["player", "side"])
        .agg(xt=("xt", "sum"), xt_pass=("xt_pass", "sum"), xt_carry=("xt_carry", "sum"), moves=("xt", "size"))
        .reset_index()
        .sort_values("xt", ascending=False)
    )

    return {
        "id": game_id,
        "date": row.date.isoformat(),
        "home": row.home_team,
        "away": row.away_team,
        "home_score": None if pd.isna(row.home_score) else int(row.home_score),
        "away_score": None if pd.isna(row.away_score) else int(row.away_score),
        "elapsed": str(row.elapsed or ""),
        "finished": not live,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "xt": {side: round(float(moves.loc[moves.side == side, "xt"].sum()), 3) for side in ("home", "away")},
        "players": [
            {
                "name": p.player,
                "side": p.side,
                "xt": round(p.xt, 3) + 0.0,
                "xt_pass": round(p.xt_pass, 3) + 0.0,
                "xt_carry": round(p.xt_carry, 3) + 0.0,  # avoid "-0.000"
                "moves": int(p.moves),
            }
            for p in players.itertuples()
        ],
        # Coordinates stay left-to-right for the acting team; the page flips the away side
        "actions": [
            {
                "player": a.player,
                "side": a.side,
                "kind": a.kind,
                "minute": int(a.minute),
                "xt": round(a.xt, 4),
                "x0": round(a.start_x, 1),
                "y0": round(a.start_y, 1),
                "x1": round(a.end_x, 1),
                "y1": round(a.end_y, 1),
            }
            for a in moves.itertuples()
            if a.xt > 0
        ],
    }
