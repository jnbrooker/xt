"""Team colours, with a fallback to the next kit colour when two teams clash."""

# Preference order: main home colour, then secondary / traditional away colours
KITS = {
    "Arsenal": ["#EF0107", "#FFFFFF", "#063672"],
    "Aston Villa": ["#670E36", "#95BFE5"],
    "Bournemouth": ["#DA291C", "#000000"],
    "Brentford": ["#E30613", "#FFFFFF", "#FFB81C"],
    "Brighton": ["#0057B8", "#FFFFFF", "#FFCD00"],
    "Chelsea": ["#034694", "#FFFFFF", "#DBA111"],
    "Coventry": ["#59CBE8", "#FFFFFF", "#1D2A4A"],
    "Crystal Palace": ["#1B458F", "#C4122E"],
    "Everton": ["#003399", "#FFFFFF", "#F5A623"],
    "Fulham": ["#FFFFFF", "#000000", "#CC0000"],
    "Hull": ["#F5A12D", "#000000"],
    "Ipswich": ["#0044A9", "#FFFFFF", "#DE2027"],
    "Leeds": ["#FFFFFF", "#1D428A", "#FFCD00"],
    "Liverpool": ["#C8102E", "#FFFFFF", "#00B2A9"],
    "Manchester City": ["#6CABDD", "#1C2C5B"],
    "Manchester United": ["#DA291C", "#000000", "#FFFFFF"],
    "Newcastle": ["#241F20", "#FFFFFF", "#41B6E6"],
    "Nottingham Forest": ["#DD0000", "#FFFFFF"],
    "Sunderland": ["#EB172B", "#FFFFFF", "#211E1E"],
    "Tottenham": ["#FFFFFF", "#132257"],
}
DEFAULT = {"home": ["#2563EB"], "away": ["#EA580C"]}

# Page backgrounds the colours must stand out against (match style.css)
BACKGROUNDS = {"light": "#FAFAF9", "dark": "#141413"}
MIN_CONTRAST = 2.5  # enough to see a line or dot, not body text
MIN_DISTANCE = 45  # CIE76 delta E; below this two colours read as the same


def _rgb(hex_: str) -> tuple[float, float, float]:
    return tuple(int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_: str) -> float:
    r, g, b = map(_linear, _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _lab(hex_: str) -> tuple[float, float, float]:
    r, g, b = map(_linear, _rgb(hex_))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _distance(a: str, b: str) -> float:
    return sum((p - q) ** 2 for p, q in zip(_lab(a), _lab(b))) ** 0.5


def _mix(a: str, b: str, t: float) -> str:
    return "#" + "".join(f"{round(255 * (p + (q - p) * t)):02X}" for p, q in zip(_rgb(a), _rgb(b)))


def _saturated(hex_: str) -> bool:
    return max(_rgb(hex_)) - min(_rgb(hex_)) > 0.15


def _visible(c: str, bg: str) -> str | None:
    """The colour itself, a lightened version of it on a dark page, or None if it won't show."""
    if _contrast(c, bg) >= MIN_CONTRAST:
        return c
    # Dark kits (navy, claret) stay recognisable when lifted towards white; black just turns grey
    if _luminance(bg) < 0.1 and _saturated(c):
        for t in (0.2, 0.3, 0.4, 0.5):
            if _contrast(lifted := _mix(c, "#FFFFFF", t), bg) >= MIN_CONTRAST:
                return lifted
    return None


def _pick(options: list[str], bg: str, avoid: str | None = None) -> str | None:
    for c in options:
        v = _visible(c, bg)
        if v and (avoid is None or _distance(v, avoid) >= MIN_DISTANCE):
            return v
    return None


def match_colours(home: str, away: str) -> dict[str, dict[str, str]]:
    """Return {"light": {"home": .., "away": ..}, "dark": {...}}.

    The home side keeps its first visible colour; the away side switches kit if it clashes.
    """
    home_kit = KITS.get(home, DEFAULT["home"])
    away_kit = KITS.get(away, DEFAULT["away"])
    out = {}
    for mode, bg in BACKGROUNDS.items():
        h = _pick(home_kit, bg) or _pick(DEFAULT["home"], bg)
        a = _pick(away_kit, bg, avoid=h) or _pick(DEFAULT["away"] + DEFAULT["home"], bg, avoid=h)
        out[mode] = {"home": h, "away": a}
    return out


def css_vars(home: str, away: str) -> str:
    """Inline style setting --home and --away for both colour schemes."""
    c = match_colours(home, away)
    return ";".join(f'--{s}:light-dark({c["light"][s]},{c["dark"][s]})' for s in ("home", "away"))
