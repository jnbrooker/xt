"""Build xT match pages.

    python build.py 1983629          one match by WhoScored id
    python build.py --today          every Premier League match today that has kicked off
    python build.py --today --watch 120   keep refreshing live matches every 2 minutes
    python build.py --render         rebuild pages from saved data only

Add --push to commit and push the pages after each build, so GitHub Pages updates.
"""

import argparse
import json
import subprocess
import time
from datetime import date, datetime

from xt.match import ROOT, build_match, has_started, is_finished, schedule
from xt.render import MATCHES, render_all


def publish() -> None:
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, check=True)
    git("add", "data", "docs")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    git("commit", "-q", "-m", f"Update xT pages {datetime.now():%Y-%m-%d %H:%M}")
    git("push", "-q")
    print("  pushed")


def save(m: dict) -> None:
    MATCHES.mkdir(parents=True, exist_ok=True)
    (MATCHES / f'{m["id"]}.json').write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(f'  {m["home"]} {m["home_score"]}-{m["away_score"]} {m["away"]}  xT {m["xt"]["home"]:.2f}-{m["xt"]["away"]:.2f}')


def run(args) -> bool:
    """Build the requested matches; return True if any are still live."""
    sched = schedule(args.season)
    if args.today:
        rows = sched[sched.date.dt.date == date.today()]
        rows = rows[rows.apply(has_started, axis=1)]
    else:
        rows = sched[sched.game_id.isin(args.ids)]
    if rows.empty:
        print("No matching matches found.")
    for _, row in rows.iterrows():
        save(build_match(row, args.season))
    render_all()
    if args.push:
        publish()
    return any(not is_finished(r) for _, r in rows.iterrows())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ids", nargs="*", type=int, help="WhoScored match ids")
    p.add_argument("--today", action="store_true")
    p.add_argument("--season", default="2627", help="soccerdata season code, e.g. 2627")
    p.add_argument("--watch", type=int, metavar="SECONDS", help="rebuild live matches on an interval")
    p.add_argument("--render", action="store_true")
    p.add_argument("--push", action="store_true", help="commit and push docs/ and data/ after building")
    args = p.parse_args()

    if args.render:
        render_all()
        if args.push:
            publish()
        return
    if not (args.ids or args.today):
        p.error("give match ids or --today")
    while run(args) and args.watch:
        time.sleep(args.watch)
    print("Pages in docs/")


if __name__ == "__main__":
    main()
