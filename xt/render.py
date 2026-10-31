"""Turn saved match JSON into a tiny static site in docs/ (GitHub Pages-ready)."""

import json
from datetime import datetime
from html import escape
from pathlib import Path
from shutil import copytree

from xt.colours import css_vars

ROOT = Path(__file__).resolve().parent.parent
MATCHES = ROOT / "data" / "matches"
SITE = ROOT / "docs"

CSS = """
:root{color-scheme:light dark;--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--line:#e7e5e4;--card:#fff;--home:#2563eb;--away:#ea580c;--pitch:#f5f5f4}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#f5f5f4;--muted:#a8a29e;--line:#2e2c2a;--card:#1c1b19;--home:#60a5fa;--away:#fb923c;--pitch:#1c1b19}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:32px 16px 64px}
a{color:inherit}
.back{color:var(--muted);text-decoration:none;font-size:14px}
h1{font-size:28px;font-weight:600;margin:12px 0 2px;letter-spacing:-.01em}
.score{font-variant-numeric:tabular-nums}
.meta{color:var(--muted);font-size:14px;margin:0 0 24px}
.live{color:#dc2626;font-weight:600}
.bar{display:flex;height:6px;border-radius:3px;overflow:hidden;margin:6px 0 4px}
.bar span:first-child{background:var(--home)}.bar span:last-child{background:var(--away)}
.split{display:flex;justify-content:space-between;font-size:14px;font-variant-numeric:tabular-nums}
.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin:28px 0 8px}
svg.pitch{width:100%;height:auto;display:block;background:var(--pitch);border:1px solid var(--line);border-radius:8px}
.pitch .ln{fill:none;stroke:var(--line);stroke-width:.35}
.hint{color:var(--muted);font-size:13px;margin-top:6px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{text-align:right;font-weight:500;color:var(--muted);font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line)}
td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--line)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td:first-child,th:first-child{color:var(--muted);width:28px}
tbody tr{cursor:pointer}tbody tr:hover,tbody tr.on{background:var(--card)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
.home{background:var(--home)}.away{background:var(--away)}
.num-muted{color:var(--muted)}
.list a{display:flex;justify-content:space-between;gap:12px;padding:14px 0;border-bottom:1px solid var(--line);text-decoration:none}
.list .xt{color:var(--muted);font-size:13px;white-space:nowrap}
@media (max-width:560px){.hide-sm{display:none}}
"""

PITCH_JS = """
const D = JSON.parse(document.getElementById('data').textContent);
const svg = document.querySelector('svg.pitch'), arrows = document.getElementById('arrows');
const ns = 'http://www.w3.org/2000/svg';
function draw(player) {
  arrows.replaceChildren();
  let acts = player ? D.filter(a => a.player === player) : D.slice().sort((a, b) => b.xt - a.xt).slice(0, 25);
  const max = Math.max(...D.map(a => a.xt), 0.01);
  for (const a of acts) {
    // home attacks right; away actions are flipped so they attack left
    const f = a.side === 'away';
    const [x0, y0, x1, y1] = f ? [105 - a.x0, a.y0, 105 - a.x1, a.y1] : [a.x0, 68 - a.y0, a.x1, 68 - a.y1];
    const l = document.createElementNS(ns, 'line');
    Object.entries({x1: x0, y1: y0, x2: x1, y2: y1, stroke: `var(--${a.side})`,
      'stroke-width': 0.35 + 1.1 * a.xt / max, 'stroke-opacity': 0.35 + 0.65 * a.xt / max,
      'stroke-linecap': 'round', 'marker-end': `url(#tip-${a.side})`,
      'stroke-dasharray': a.kind === 'carry' ? '1 0.8' : ''}).forEach(([k, v]) => l.setAttribute(k, v));
    const t = document.createElementNS(ns, 'title');
    t.textContent = `${a.player} · ${a.kind} · ${a.minute}' · +${a.xt.toFixed(3)} xT`;
    l.append(t); arrows.append(l);
  }
  document.getElementById('hint').textContent = player
    ? `${player}: ${acts.length} threat-adding moves · click again to reset`
    : 'Top 25 threat-adding moves · solid = pass, dashed = carry · click a player to filter';
}
let current = null;
document.querySelectorAll('tbody tr').forEach(tr => tr.addEventListener('click', () => {
  current = current === tr.dataset.player ? null : tr.dataset.player;
  document.querySelectorAll('tbody tr').forEach(r => r.classList.toggle('on', r.dataset.player === current));
  draw(current);
}));
draw(null);
"""

PITCH_SVG = """<svg class="pitch" viewBox="-2 -2 109 72" role="img" aria-label="Pitch with xT moves">
<defs>{tips}</defs>
<g class="ln"><rect x="0" y="0" width="105" height="68"/><line x1="52.5" y1="0" x2="52.5" y2="68"/>
<circle cx="52.5" cy="34" r="9.15"/><rect x="0" y="13.84" width="16.5" height="40.32"/><rect x="88.5" y="13.84" width="16.5" height="40.32"/>
<rect x="0" y="24.84" width="5.5" height="18.32"/><rect x="99.5" y="24.84" width="5.5" height="18.32"/></g>
<g id="arrows"></g></svg>"""

TIP = '<marker id="tip-{s}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="3" markerHeight="3" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="var(--{s})"/></marker>'


def page(title: str, body: str, depth: int = 0, style: str = "", refresh: bool = False) -> str:
    up = "../" * depth
    meta = '<meta http-equiv="refresh" content="120">' if refresh else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{meta}
<meta name="theme-color" content="#fafaf9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141413" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="xT">
<link rel="manifest" href="{up}manifest.webmanifest"><link rel="apple-touch-icon" href="{up}icon-180.png">
<link rel="icon" href="{up}icon-192.png"><title>{escape(title)}</title><link rel="stylesheet" href="{up}style.css"></head>
<body><main style="{style}">{body}</main></body></html>"""


def score(m: dict) -> str:
    if m["home_score"] is None:
        return "v"
    return f'<span class="score">{m["home_score"]}–{m["away_score"]}</span>'


def status(m: dict) -> str:
    if m["finished"]:
        return "Full time"
    return f'<span class="live">● Live {escape(m["elapsed"])}</span>' if m["elapsed"] else "Not started"


def when(m: dict) -> str:
    return datetime.fromisoformat(m["date"]).strftime("%a %d %b %Y")


def match_page(m: dict) -> str:
    h, a = m["xt"]["home"], m["xt"]["away"]
    pos_h, pos_a = max(h, 0), max(a, 0)
    share = 50 if pos_h + pos_a == 0 else round(100 * pos_h / (pos_h + pos_a))
    rows = "".join(
        f'<tr data-player="{escape(p["name"])}"><td>{i}</td>'
        f'<td><span class="dot {p["side"]}"></span>{escape(p["name"])}</td>'
        f'<td><b>{p["xt"]:.3f}</b></td><td class="hide-sm num-muted">{p["xt_pass"]:.3f}</td>'
        f'<td class="hide-sm num-muted">{p["xt_carry"]:.3f}</td><td class="num-muted">{p["moves"]}</td></tr>'
        for i, p in enumerate(m["players"], 1)
    )
    tips = TIP.format(s="home") + TIP.format(s="away")
    body = f"""<a class="back" href="../index.html">← All matches</a>
<h1>{escape(m["home"])} {score(m)} {escape(m["away"])}</h1>
<p class="meta">{when(m)} · {status(m)} · updated {m["updated"][11:16]} UTC</p>
<div class="label">Expected threat</div>
<div class="split"><span><span class="dot home"></span>{escape(m["home"])} <b>{h:.2f}</b></span><span><b>{a:.2f}</b> {escape(m["away"])}<span class="dot away" style="margin:0 0 0 8px"></span></span></div>
<div class="bar"><span style="width:{share}%"></span><span style="width:{100 - share}%"></span></div>
<div class="label">Moves</div>
{PITCH_SVG.format(tips=tips)}
<div class="hint" id="hint"></div>
<div class="label">Players</div>
<table><thead><tr><th>#</th><th>Player</th><th>xT</th><th class="hide-sm">Pass</th><th class="hide-sm">Carry</th><th>Moves</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="hint">xT from successful passes and carries, using Karun Singh's open 12×8 grid via socceraction. Event data: WhoScored.</p>
<script type="application/json" id="data">{json.dumps(m["actions"]).replace("</", "<\\/")}</script>
<script>{PITCH_JS}</script>"""
    return page(f'{m["home"]} v {m["away"]} · xT', body, depth=1,
                style=css_vars(m["home"], m["away"]), refresh=not m["finished"])


def index_page(matches: list[dict]) -> str:
    items = "".join(
        f'<a href="matches/{m["id"]}.html" style="{css_vars(m["home"], m["away"])}">'
        f'<span><span class="dot home"></span>{escape(m["home"])} {score(m)} {escape(m["away"])}'
        f'<span class="dot away" style="margin:0 0 0 8px"></span>'
        f'<br><span class="meta">{when(m)} · {status(m)}</span></span>'
        f'<span class="xt">xT {m["xt"]["home"]:.2f} – {m["xt"]["away"]:.2f}</span></a>'
        for m in matches
    )
    body = f'<h1>xT</h1><p class="meta">Expected threat by match</p><div class="list">{items or "<p>No matches yet.</p>"}</div>'
    return page("xT", body)


def render_all() -> None:
    (SITE / "matches").mkdir(parents=True, exist_ok=True)
    matches = [json.loads(p.read_text(encoding="utf-8")) for p in MATCHES.glob("*.json")]
    matches.sort(key=lambda m: m["date"], reverse=True)
    for m in matches:
        (SITE / "matches" / f'{m["id"]}.html').write_text(match_page(m), encoding="utf-8")
    (SITE / "index.html").write_text(index_page(matches), encoding="utf-8")
    (SITE / "style.css").write_text(CSS.strip(), encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    copytree(Path(__file__).parent / "static", SITE, dirs_exist_ok=True)
