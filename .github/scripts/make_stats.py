#!/usr/bin/env python3
"""Builds the panels that depend on live GitHub data, into assets/generated/.

  stats.svg / stats-narrow.svg           headline metrics, gauge, facts, language bar
  contributions.svg                      real contribution grid + animated runner
  proj-<slug>.svg / -narrow.svg          project cards (landscape on desktop, portrait on phones)
  resolved.json                          which public repo each project matched (used for README links)

  python .github/scripts/make_stats.py             real data (network; GITHUB_TOKEN recommended)
  python .github/scripts/make_stats.py --pending   compact "not fetched yet" state, no network
  python .github/scripts/make_stats.py --demo      SYNTHETIC data into ./preview/ for layout QA only

Rules this script follows:
  * Only data returned by GitHub is ever drawn. A metric that could not be fetched is omitted.
  * If nothing at all could be fetched the script exits 1, so the workflow run is visibly red
    and existing files are left alone. A broken run can no longer pass for a good one.
  * Partial data produces a partial (but complete-looking) dashboard plus a warning annotation.
"""
import json
import math
import os
import random
import sys
from datetime import date, timedelta

from gh_data import collect, stars_total, streaks, to_weeks
from lib import (DIM, FRAME, FRAME2, GREEN, MINT, MUTED, PANEL, ROOT, SANS, TEAL, TEXT, VIOLET, YEL,
                 anim_pts, esc, load_config, note, tw, wrap, write, write_summary)
from ui import chrome, svg

OUT_DIR = os.path.join(ROOT, "assets", "generated")
LV = ["#0c1d19", "#0f4a3a", "#12805f", "#1fd18f", GREEN]
LANG_COL = [MINT, TEAL, YEL, VIOLET, GREEN]


# --------------------------------------------------------------------------- #
# view model
# --------------------------------------------------------------------------- #
def view(d, cfg):
    """Everything the stats panel may show, each either a verified value or absent."""
    cal = d.get("cal")
    days = cal["days"] if cal else None
    active = sum(1 for v in days.values() if v > 0) if days else None
    best, cur = d["streak"] if d.get("streak") else (None, None)
    pub = None
    if d.get("user") and d["user"].get("public_repos") is not None:
        pub = d["user"]["public_repos"]
    elif d.get("repos") is not None:
        pub = len(d["repos"])
    stars = stars_total(d.get("repos"))
    foll = d["user"]["followers"] if d.get("user") else None
    return {
        "contributions": cal["total"] if cal else None,
        "commits": d.get("commits"),
        "repos": pub,
        "active": active,
        "per_active": round(cal["total"] / active, 1) if cal and active else None,
        "best": best,
        "cur": cur,
        "stars": stars if stars else None,        # a zero is true but not worth a headline
        "followers": foll if foll else None,
        "since": d["user"]["since"] if d.get("user") else None,
        "top_lang": d["langs"][0][0] if d.get("langs") else None,
        "range": f'{min(days)} to {max(days)}' if days else None,
    }


HEAD_ORDER = [("contributions", "Contributions", "last 12 months"), ("commits", "Commits", "last 12 months"),
              ("repos", "Public Repositories", "on GitHub"), ("active", "Active Days", "last 12 months"),
              ("stars", "Stars Earned", "across own repos"), ("followers", "Followers", "on GitHub")]
FACT_ORDER = [("top_lang", "Top Language", "star"), ("active", "Active Days", "cal"),
              ("per_active", "Contributions / Active Day", "clock"), ("best", "Longest Streak (days)", "flame"),
              ("cur", "Current Streak (days)", "flame"), ("stars", "Stars Earned", "star"),
              ("followers", "Followers", "user"), ("since", "On GitHub Since", "cal"), ("repos", "Public Repositories", "repo")]
ICONS = {
    "star": '<path d="M8 1.5l1.9 4 4.3.5-3.2 3 .9 4.3L8 11.1 4.1 13.3 5 9 1.8 6l4.3-.5z"/>',
    "clock": '<circle cx="8" cy="8" r="6.3"/><path d="M8 4.5V8l2.4 1.6"/>',
    "cal": '<rect x="2" y="3" width="12" height="11" rx="2"/><path d="M2 6.5h12M5.5 1.5v3M10.5 1.5v3"/>',
    "flame": '<path d="M8 1.5c.5 2.5 3.5 3.7 3.5 7A3.5 3.5 0 0 1 8 12a3.5 3.5 0 0 1-3.5-3.5c0-1.4.7-2.2 1.3-3 .2 1 .8 1.4 1.2 1.4C7 5.3 7.3 3.2 8 1.5z"/>',
    "user": '<circle cx="8" cy="5.5" r="2.7"/><path d="M2.8 14c.4-2.8 2.5-4.2 5.2-4.2s4.8 1.4 5.2 4.2"/>',
    "repo": '<path d="M3 2.5h8.5a1.5 1.5 0 0 1 1.5 1.5v9H4.5A1.5 1.5 0 0 1 3 11.5z"/><path d="M3 11.5A1.5 1.5 0 0 1 4.5 10H13"/>',
}


def fmt(v):
    return f"{v:,}" if isinstance(v, int) else str(v)


# --------------------------------------------------------------------------- #
# stats panel
# --------------------------------------------------------------------------- #
def gauge(cx, cy, r, frac, num, size):
    C = 2 * math.pi * r
    f = max(0.0, min(1.0, frac or 0))
    arc = ""
    if f > 0:
        arc = (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#arc)" stroke-width="5" stroke-linecap="round" '
               f'stroke-dasharray="{f * C:.1f} {C:.1f}" transform="rotate(-90 {cx} {cy})">'
               f'<animate attributeName="stroke-dasharray" values="0 {C:.1f};{f * C:.1f} {C:.1f}" dur="1.8s" begin="0s" fill="freeze" '
               f'calcMode="spline" keySplines=".22 .61 .36 1" keyTimes="0;1"/></circle>')
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#12332b" stroke-width="5"/>{arc}'
            f'<text x="{cx}" y="{cy + size * .35:.1f}" text-anchor="middle" font-size="{size}" font-weight="700" fill="{TEXT}">{esc(num)}</text>')


def tile(cx, y, num, label, sub, size, lsize, ssize, frac=None, gauge_r=44):
    if frac is not None:
        gy = y - size * .35 - 6
        top = gauge(cx, gy, gauge_r, frac, num, size * .72)
        ly = gy + gauge_r + 28
    else:
        top = f'<text x="{cx}" y="{y}" text-anchor="middle" font-size="{size}" font-weight="700" fill="{TEXT}">{esc(num)}</text>'
        ly = y + size * .45 + 14
    return (top + f'<text x="{cx}" y="{ly:.0f}" text-anchor="middle" font-size="{lsize}" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(label)}</text>'
            f'<text x="{cx}" y="{ly + ssize + 6:.0f}" text-anchor="middle" font-size="{ssize}" fill="{MUTED}">{esc(sub)}</text>')


def panel(x, y, w, h, title, size=16):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#040d0b" stroke="{FRAME2}" stroke-width="1.2"/>'
            f'<text x="{x + 26}" y="{y + 38}" font-size="{size}" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(title)}</text>')


def lang_block(langs, x, y, w, step):
    bx, bw = x + 26, w - 52
    top = langs[:4]
    rest = 100 - sum(p for _, p in top)
    segs = top + ([("other", rest)] if rest > 0.5 else [])
    out = (f'<clipPath id="lb"><rect x="{bx}" y="{y}" width="{bw}" height="10" rx="5"/></clipPath>'
           f'<rect x="{bx}" y="{y}" width="{bw}" height="10" rx="5" fill="#12332b"/><g clip-path="url(#lb)">')
    cx = bx
    for i, (name, p) in enumerate(segs):
        sw = bw * p / 100
        col = LANG_COL[i] if name != "other" else DIM
        wv = max(sw - 2, 1)
        out += (f'<rect x="{cx:.1f}" y="{y}" width="{wv:.1f}" height="10" fill="{col}"><animate attributeName="width" '
                f'values="0;{wv:.1f}" dur="1.6s" begin="0s" fill="freeze" calcMode="spline" keySplines=".22 .61 .36 1" keyTimes="0;1"/></rect>')
        cx += sw
    out += "</g>"
    ly = y + 38
    for i, (name, p) in enumerate(segs):
        col = LANG_COL[i] if name != "other" else DIM
        out += (f'<circle cx="{bx + 5}" cy="{ly - 4}" r="4.5" fill="{col}"/>'
                f'<text x="{bx + 18}" y="{ly}" font-size="13.5" font-family="{SANS}" fill="{TEXT}">{esc(name)}</text>'
                f'<text x="{bx + bw}" y="{ly}" text-anchor="end" font-size="13" fill="{MUTED}">{p:.1f}%</text>')
        ly += step
    return out, 38 + len(segs) * step


def _panel_body(kind, x, y, w, h, facts, m, langs, cfg, step_f, step_l, narrow):
    if kind == "facts":
        out = panel(x, y, w, h, f'{cfg["handle"]}\'s GitHub Stats', 16 if not narrow else 15)
        yy = y + 78
        for k, lab, ic in facts:
            out += (f'<g transform="translate({x + 26} {yy - 14})" fill="none" stroke="{MINT}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{ICONS[ic]}</g>'
                    f'<text x="{x + 54}" y="{yy}" font-size="14" font-family="{SANS}" fill="{TEXT}">{esc(lab)}</text>'
                    f'<text x="{x + w - 26}" y="{yy}" text-anchor="end" font-size="14" font-weight="700" fill="{TEXT}">{esc(fmt(m[k]))}</text>')
            yy += step_f
        return out
    out = panel(x, y, w, h, "Most Used Languages", 16 if not narrow else 15)
    body, _ = lang_block(langs, x, y + 62, w, step_l)
    return out + body


def build_stats(m, langs, cfg, narrow, demo=False):
    heads = [(k, l, s) for k, l, s in HEAD_ORDER if m.get(k) is not None][:3]
    if not heads:
        return None
    shown = {k for k, _, _ in heads}
    facts = [(k, l, ic) for k, l, ic in FACT_ORDER if m.get(k) is not None and k not in shown][:4]
    n = len(heads)
    W = 560 if narrow else 1180
    title = f'{cfg["handle"]} % gh-stats --last-12-months'
    bar = 40 if narrow else 44
    body = ""
    gx = [W * (2 * i + 1) / (2 * n) for i in range(n)]
    ty = bar + (92 if not narrow else 80)
    size, ls, ss = (46, 15, 11) if not narrow else (28, 12, 9.5)
    for i, (k, lab, sub) in enumerate(heads):
        f = None
        if k == "commits" and m.get("contributions"):
            f = min(1.0, m["commits"] / m["contributions"])
        if k == "contributions" and m.get("range") and not demo and not narrow:
            sub = m["range"].replace(" to ", "  to  ")
        body += tile(gx[i], ty, fmt(m[k]), lab, sub, size, ls, ss, f, 44 if not narrow else 30)
        if i:
            xd = (gx[i - 1] + gx[i]) / 2
            body += f'<line x1="{xd:.0f}" y1="{bar + 24}" x2="{xd:.0f}" y2="{bar + (148 if not narrow else 122)}" stroke="{FRAME}"/>'
    y = bar + (176 if not narrow else 140)
    panels = (["facts"] if facts else []) + (["langs"] if langs else [])
    if not panels:
        H = y
    else:
        body += f'<line x1="{W * .05:.0f}" y1="{y}" x2="{W * .95:.0f}" y2="{y}" stroke="{FRAME2}"/>'
        y += 24
        step_f, step_l = (42, 28) if not narrow else (36, 24)
        hf = 62 + len(facts) * step_f
        hl = 62 + (38 + (len(langs[:4]) + (1 if 100 - sum(p for _, p in langs[:4]) > .5 else 0)) * step_l if langs else 0) + 14
        if narrow:
            cy = y
            for p in panels:
                h_ = hf if p == "facts" else hl
                body += _panel_body(p, 20, cy, W - 40, h_, facts, m, langs, cfg, step_f, step_l, narrow)
                cy += h_ + 18
            H = cy - 18 + 22
        else:
            ph = max(hf if facts else 0, hl if langs else 0)
            gap = 30
            if len(panels) == 2:
                w = (W - 80 - gap) / 2
                xs = [40, 40 + w + gap]
            else:
                w, xs = 540, [(W - 540) / 2]
            for p, x in zip(panels, xs):
                body += _panel_body(p, x, y, w, ph, facts, m, langs, cfg, step_f, step_l, narrow)
            H = y + ph + 26
    ch, _ = chrome(W, H, title, narrow=narrow)
    demo_t = f'<text x="{W / 2}" y="{H - 10}" text-anchor="middle" font-size="10.5" fill="{YEL}">DEMO DATA, NOT REAL</text>' if demo else ""
    aria = f'GitHub statistics for {cfg["handle"]}: ' + ", ".join(f'{l.lower()} {fmt(m[k])}' for k, l, _ in heads)
    defs = (f'<linearGradient id="arc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{MINT}"/>'
            f'<stop offset="1" stop-color="{TEAL}"/></linearGradient>')
    return svg(W, H, aria, ch + body + demo_t, defs)


def build_stats_pending(cfg, narrow=False):
    """Verified, config-derived summary shown only until the first successful workflow run."""
    W = 560 if narrow else 1180
    items = [(str(len(cfg["projects"])), "Featured Projects"),
             (str(sum(len(g["items"]) for g in cfg["tech_groups"])), "Technologies"),
             ("B.Tech", cfg["degree"].replace("B.Tech ", ""))]
    H = 190 if narrow else 214
    ch, bar = chrome(W, H, f'{cfg["handle"]} % gh-stats --pending', status="PENDING", narrow=narrow)
    body = ""
    for i, (num, lab) in enumerate(items):
        cx = W * (2 * i + 1) / 6
        body += tile(cx, bar + (70 if narrow else 76), num, lab, "from profile" if narrow else "from profile config",
                     (26 if narrow else 40), (11.5 if narrow else 14), (9.5 if narrow else 10.5))
        if i:
            xd = W * i / 3
            body += f'<line x1="{xd:.0f}" y1="{bar + 20}" x2="{xd:.0f}" y2="{bar + (96 if narrow else 112)}" stroke="{FRAME}"/>'
    msg = "Live GitHub numbers appear after the first workflow run." if narrow else \
        'Live GitHub numbers appear after the first successful run of the "Refresh profile assets" workflow.'
    body += f'<text x="{W / 2}" y="{H - 18}" text-anchor="middle" font-size="{11 if narrow else 12.5}" font-family="{SANS}" fill="{MUTED}">{msg}</text>'
    return svg(W, H, "Profile summary. Live GitHub statistics appear after the first workflow run.", ch + body)


# --------------------------------------------------------------------------- #
# contribution scene
# --------------------------------------------------------------------------- #
def level_fn(days):
    vals = sorted(v for v in days.values() if v > 0)
    if not vals:
        return lambda c: 0
    q = [vals[min(int(len(vals) * f), len(vals) - 1)] for f in (.25, .5, .75)]
    return lambda c: 0 if not c else 1 + sum(c > t for t in q)


SPL = "0.37 0 0.63 1"


def spl(n):
    return ";".join([SPL] * n)


def rot(vals, keys, dur, begin=0.0):
    v = ";".join(f"{a} 0 0" for a in vals)
    k = ";".join(f"{t:g}" for t in keys)
    return (f'<animateTransform attributeName="transform" type="rotate" values="{v}" keyTimes="{k}" calcMode="spline" '
            f'keySplines="{spl(len(vals) - 1)}" dur="{dur}s" begin="{begin:g}s" repeatCount="indefinite"/>')


def runner_group():
    """Vector pixel-style runner. Origin = feet on the ground. Limbs swing on joints with eased keyframes."""
    D, K = 0.72, [0, .25, .5, .75, 1]

    def leg(color, shoe, begin):
        thigh = rot([-34, 2, 30, 4, -34], K, D, begin)
        shin = rot([14, 8, 42, 88, 14], K, D, begin)
        return (f'<g transform="translate(0 -30)"><g>{thigh}<rect x="-3.5" y="-1" width="7" height="16" rx="2" fill="{color}"/>'
                f'<g transform="translate(0 14)"><g>{shin}<rect x="-3" y="-1" width="6" height="15" rx="2" fill="{color}"/>'
                f'<rect x="-3" y="12" width="11" height="5" rx="2" fill="{shoe}"/></g></g></g></g>')

    def arm(color, begin):
        up = rot([36, -4, -38, -4, 36], K, D, begin)
        fore = rot([-48, -70, -40, -20, -48], K, D, begin)
        return (f'<g transform="translate(1 -53)"><g>{up}<rect x="-2.5" y="-1" width="5" height="12" rx="2" fill="{color}"/>'
                f'<g transform="translate(0 10)"><g>{fore}<rect x="-2.2" y="-1" width="4.4" height="11" rx="2" fill="{color}"/>'
                f'<rect x="-2.4" y="8" width="4.8" height="4" rx="2" fill="#f1c9a5"/></g></g></g></g>')

    bob = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" keyTimes="0;.5;1" calcMode="spline" '
           f'keySplines="{spl(2)}" dur="{D / 2}s" repeatCount="indefinite"/>')
    return (f'<ellipse cx="0" cy="2" rx="17" ry="3.2" fill="#000" opacity=".45"/>'
            f'<g>{bob}{leg("#14507f", "#0c2236", -D / 2)}{arm("#14a37a", 0)}'
            f'<rect x="-8" y="-58" width="16" height="30" rx="4" fill="#2ee6a6"/><rect x="-8" y="-34" width="16" height="6" rx="3" fill="#14a37a"/>'
            f'{leg("#1d3557", YEL, 0)}'
            f'<rect x="-8" y="-76" width="16" height="17" rx="4" fill="#f1c9a5"/><rect x="-9.5" y="-79" width="19" height="8" rx="3" fill="{TEAL}"/>'
            f'<rect x="3" y="-73" width="12" height="3.5" rx="1.5" fill="{TEAL}"/><rect x="3.2" y="-66" width="2.6" height="3.4" rx="1" fill="#0b1512"/>'
            f'{arm("#2ee6a6", -D / 2)}</g>')


def build_contrib(m, d, cfg, demo=False):
    days = d["cal"]["days"]
    weeks = d["weeks"]
    lv = level_fn(days)
    W, cell, gap = 1180, 14, 6
    pitch = cell + gap
    cols = len(weeks)
    gw = cols * pitch - gap
    x0 = (W - gw) / 2
    bar = 44
    y0 = bar + 54
    grid_bottom = y0 + 7 * pitch - gap
    ground = grid_bottom + 112
    H = ground + 52
    T = 22.0
    xs, xe = x0 + cell / 2, x0 + gw - cell / 2
    U0, U1 = .045, .955
    cells, glow = [], []
    for i, w in enumerate(weeks):
        for j, c in enumerate(w):
            if c is None:
                continue
            x, y = x0 + i * pitch, y0 + j * pitch
            L = lv(c)
            cells.append(f'<rect x="{x:.0f}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LV[L]}"/>')
            if L:
                u = U0 + (U1 - U0) * ((x + cell / 2 - xs) / (xe - xs))
                a, b = max(u - .05, .0005), min(u + .06, .9995)
                v, k = anim_pts([(0, 0), (a, 0), (u, .9), (b, 0), (1, 0)])
                glow.append(f'<rect x="{x:.0f}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="#eafff6" opacity="0">'
                            f'<animate attributeName="opacity" values="{v}" keyTimes="{k}" dur="{T:g}s" repeatCount="indefinite"/></rect>')
    rnd = random.Random(5)
    sy0, sy1 = grid_bottom + 8, ground - 16
    stars = "".join(f'<circle cx="{rnd.randrange(24, W - 24)}" cy="{rnd.randrange(sy0, sy1)}" r="1.1" fill="{MINT}" opacity="{rnd.choice([.12, .2, .32])}"/>' for _ in range(46))
    twinkle = "".join(
        f'<circle cx="{rnd.randrange(60, W - 60)}" cy="{rnd.randrange(sy0, sy1)}" r="1.5" fill="#fff" opacity=".1">'
        f'<animate attributeName="opacity" values=".08;.55;.08" dur="{rnd.uniform(3.5, 6):.1f}s" begin="{rnd.uniform(0, 4):.1f}s" repeatCount="indefinite" '
        f'calcMode="spline" keyTimes="0;.5;1" keySplines="{spl(2)}"/></circle>' for _ in range(7))
    move = f'values="{xs:.1f} {ground};{xs:.1f} {ground};{xe:.1f} {ground};{xe:.1f} {ground}" keyTimes="0;{U0};{U1};1"'
    fade = f'values="0;1;1;0" keyTimes="0;{U0};{U1};1"'
    dust = "".join(
        f'<circle cx="-8" cy="-3" r="2" fill="{MINT}" opacity="0"><animateTransform attributeName="transform" type="translate" '
        f'values="0 0;-26 -7" dur="0.8s" begin="{i * .27:.2f}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.55;0" '
        f'dur="0.8s" begin="{i * .27:.2f}s" repeatCount="indefinite"/></circle>' for i in range(3))
    bh = ground - grid_bottom - 82
    beam = f'<rect x="{-pitch / 2}" y="{-(ground - grid_bottom) + 2:.0f}" width="{pitch}" height="{bh:.0f}" fill="url(#beam)"/>'
    runner = (f'<g><animateTransform attributeName="transform" type="translate" {move} dur="{T:g}s" repeatCount="indefinite"/>'
              f'<g opacity="0"><animate attributeName="opacity" {fade} dur="{T:g}s" repeatCount="indefinite"/>{beam}{dust}{runner_group()}</g></g>')
    best, cur = d["streak"]
    foot = f'{m["active"]} active days   longest streak {best}   current streak {cur}'
    total = fmt(m["contributions"])
    lx = W - x0 - 150
    legend = "".join(f'<rect x="{lx + 38 + i * 19:.0f}" y="{bar + 20}" width="13" height="13" rx="3" fill="{LV[i]}"/>' for i in range(5))
    demo_t = f'<text x="{W - 24}" y="{H - 14}" text-anchor="end" font-size="10.5" fill="{YEL}">DEMO DATA, NOT REAL</text>' if demo else ""
    ch, _ = chrome(W, H, f'{cfg["handle"]} % git log --graph --since="12 months ago"', status="SYNCED" if not demo else "DEMO")
    defs = (f'<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{GREEN}" stop-opacity=".16"/></linearGradient>'
            f'<filter id="gg" x="-5%" y="-600%" width="110%" height="1300%"><feGaussianBlur stdDeviation="4"/></filter>')
    body = (f'{stars}{twinkle}'
            f'<circle cx="{x0 + 7:.0f}" cy="{bar + 27}" r="7" fill="{GREEN}"/><circle cx="{x0 + 7:.0f}" cy="{bar + 27}" r="3" fill="{PANEL}"/>'
            f'<text x="{x0 + 24:.0f}" y="{bar + 33}" font-size="17" font-weight="700" fill="{TEXT}">{total}</text>'
            f'<text x="{x0 + 30 + tw(total, 17):.0f}" y="{bar + 32}" font-size="12.5" font-family="{SANS}" fill="{MUTED}">contributions in the last year</text>'
            f'<text x="{lx + 30:.0f}" y="{bar + 31}" text-anchor="end" font-size="11" fill="{MUTED}">less</text>'
            f'{legend}<text x="{lx + 38 + 5 * 19 + 4:.0f}" y="{bar + 31}" font-size="11" fill="{MUTED}">more</text>'
            f'{"".join(cells)}{"".join(glow)}'
            f'<rect x="0" y="{ground}" width="{W}" height="{H - ground}" fill="#04120e"/>'
            f'<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{GREEN}" stroke-width="3" filter="url(#gg)" opacity=".7"/>'
            f'<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{GREEN}" stroke-width="1.6"/>{runner}'
            f'<text x="{x0:.0f}" y="{ground + 33}" font-size="12.5" fill="{MUTED}">{esc(foot)}</text>{demo_t}')
    aria = f'Contribution grid for the last 12 months with a runner crossing it. {m["contributions"]} contributions, {m["active"]} active days.'
    return svg(W, H, aria, ch + body, defs)


def build_contrib_pending(cfg):
    W, H = 1180, 124
    ch, bar = chrome(W, H, f'{cfg["handle"]} % git log --graph --since="12 months ago"', status="PENDING")
    t = (f'<text x="{W / 2}" y="{bar + 40}" text-anchor="middle" font-size="14.5" font-family="{SANS}" fill="{MINT}">Contribution graph</text>'
         f'<text x="{W / 2}" y="{bar + 62}" text-anchor="middle" font-size="12.5" font-family="{SANS}" fill="{MUTED}">'
         f'Generated from real GitHub activity by the "Refresh profile assets" workflow.</text>')
    return svg(W, H, "Contribution graph, generated by the workflow from real GitHub activity.", ch + t)


# --------------------------------------------------------------------------- #
# project cards
# --------------------------------------------------------------------------- #
def art_skymart():
    stripes = "".join(f'<rect x="{62 + i * 12.67:.2f}" y="78" width="12.67" height="14" fill="{"#ef4444" if i % 2 == 0 else "#fff7ed"}"/>'
                      f'<circle cx="{62 + i * 12.67 + 6.33:.2f}" cy="92" r="6.33" fill="{"#ef4444" if i % 2 == 0 else "#fff7ed"}"/>' for i in range(6))
    drift = ('<animateTransform attributeName="transform" type="translate" values="0 0;9 0;0 0" keyTimes="0;.5;1" dur="14s" '
             f'repeatCount="indefinite" calcMode="spline" keySplines="{spl(2)}"/>')
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2563eb"/><stop offset=".6" stop-color="#8b5cf6"/>'
            '<stop offset="1" stop-color="#f472b6"/></linearGradient></defs><rect width="200" height="190" fill="url(#a)"/>'
            f'<g fill="#fff" opacity=".85">{drift}<rect x="18" y="38" width="36" height="8"/><rect x="26" y="31" width="20" height="8"/>'
            '<rect x="142" y="56" width="32" height="7"/><rect x="150" y="49" width="16" height="7"/></g>'
            '<g fill="#fff"><rect x="120" y="30" width="2" height="2"/><rect x="40" y="62" width="2" height="2"/><rect x="170" y="30" width="2" height="2"/></g>'
            '<rect x="0" y="146" width="200" height="44" fill="#1e1b4b"/><rect x="0" y="146" width="200" height="3" fill="#a78bfa" opacity=".6"/>'
            '<rect x="62" y="92" width="76" height="54" fill="#fef3c7"/>' + stripes +
            '<rect x="92" y="114" width="16" height="32" rx="2" fill="#7c3aed"/><rect x="68" y="104" width="18" height="18" rx="2" fill="#bae6fd"/>'
            '<rect x="114" y="104" width="18" height="18" rx="2" fill="#bae6fd"/><rect x="76" y="62" width="48" height="13" rx="3" fill="#111827"/>'
            '<text x="100" y="72.5" text-anchor="middle" font-size="9.5" font-weight="700" fill="#fde047">SKYMART</text>'
            '<g fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M148 108h7l5 22h22l4-15h-29"/>'
            '<circle cx="162" cy="137" r="2.6"/><circle cx="178" cy="137" r="2.6"/></g>'
            '<g><rect x="22" y="104" width="18" height="18" fill="#f59e0b" stroke="#b45309" stroke-width="1.5"/><rect x="29" y="104" width="4" height="18" fill="#fde68a"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -4;0 0" keyTimes="0;.5;1" dur="3.6s" repeatCount="indefinite" calcMode="spline" keySplines="{spl(2)}"/></g>')


def art_fintrack():
    ease = 'calcMode="spline" keyTimes="0;1" keySplines=".22 .61 .36 1"'
    bars = "".join(f'<rect x="{34 + i * 26}" y="{140 - h}" width="18" height="{h}" rx="3" fill="{c}">'
                   f'<animate attributeName="height" values="0;{h}" dur="1.2s" begin="{i * .12:.2f}s" fill="freeze" {ease}/>'
                   f'<animate attributeName="y" values="140;{140 - h}" dur="1.2s" begin="{i * .12:.2f}s" fill="freeze" {ease}/></rect>'
                   for i, (h, c) in enumerate([(34, MINT), (52, TEAL), (40, MINT), (70, TEAL), (58, GREEN)]))
    pts_ = [(43, 98), (69, 84), (95, 92), (121, 66), (147, 74), (173, 50)]
    line = " ".join(f"{x},{y}" for x, y in pts_)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{YEL}"/>' for x, y in pts_)
    C = 2 * math.pi * 14
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1f2a"/><stop offset="1" stop-color="#0f3d3a"/></linearGradient></defs>'
            '<rect width="200" height="190" fill="url(#a)"/><g stroke="#1b4a45" stroke-width="1"><line x1="20" y1="60" x2="190" y2="60"/><line x1="20" y1="100" x2="190" y2="100"/>'
            '<line x1="20" y1="140" x2="190" y2="140"/></g>' + bars +
            f'<polyline points="{line}" fill="none" stroke="{YEL}" stroke-width="2.5" stroke-linejoin="round" stroke-dasharray="240" stroke-dashoffset="0">'
            f'<animate attributeName="stroke-dashoffset" values="240;0" dur="1.6s" begin=".3s" fill="freeze" {ease}/></polyline>{dots}'
            f'<g transform="translate(38 36) rotate(-90)" fill="none" stroke-width="6"><circle r="14" stroke="#12332b"/>'
            f'<circle r="14" stroke="{GREEN}" stroke-dasharray="{C * .55:.1f} {C:.1f}"/><circle r="14" stroke="{YEL}" stroke-dasharray="{C * .25:.1f} {C:.1f}" stroke-dashoffset="{-C * .58:.1f}"/></g>'
            '<g><ellipse cx="160" cy="158" rx="16" ry="6" fill="#b45309"/><ellipse cx="160" cy="153" rx="16" ry="6" fill="#f59e0b"/>'
            '<ellipse cx="160" cy="148" rx="16" ry="6" fill="#fcd34d"/><text x="160" y="151" text-anchor="middle" font-size="8" font-weight="700" fill="#92400e">$</text></g>')


def art_fluent():
    hs = [8, 18, 28, 14, 34, 22, 12, 26, 10]
    bars = ""
    sp = f'calcMode="spline" keyTimes="0;.5;1" keySplines="{spl(2)}"'
    for i, h in enumerate(hs):
        h2 = hs[(i + 4) % len(hs)]
        bars += (f'<rect x="{46 + i * 11}" y="{165 - h / 2}" width="6" height="{h}" rx="3" fill="#fff" opacity=".85">'
                 f'<animate attributeName="height" values="{h};{h2};{h}" dur="2.4s" begin="{i * .1:.1f}s" repeatCount="indefinite" {sp}/>'
                 f'<animate attributeName="y" values="{165 - h / 2};{165 - h2 / 2};{165 - h / 2}" dur="2.4s" begin="{i * .1:.1f}s" repeatCount="indefinite" {sp}/></rect>')
    dots = "".join(f'<circle cx="{119 + 14 * i}" cy="116" r="4" fill="#064e3b"><animate attributeName="opacity" values=".35;1;.35" dur="1.5s" begin="{i * .25:.2f}s" repeatCount="indefinite"/></circle>' for i in range(3))
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset=".55" stop-color="#7c3aed"/>'
            '<stop offset="1" stop-color="#f0abfc"/></linearGradient></defs><rect width="200" height="190" fill="url(#a)"/>'
            '<g><rect x="26" y="52" width="76" height="38" rx="12" fill="#fff"/><path d="M40 88l-4 12 16-12z" fill="#fff"/>'
            '<text x="64" y="77" text-anchor="middle" font-size="15" font-weight="700" fill="#4c1d95">Hi!</text></g>'
            f'<g><rect x="92" y="98" width="82" height="36" rx="12" fill="#a7f3d0"/><path d="M160 132l6 11-18-11z" fill="#a7f3d0"/>{dots}</g>'
            '<g fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"><rect x="152" y="30" width="12" height="20" rx="6" fill="#fff" stroke="none"/>'
            '<path d="M147 44a11 11 0 0 0 22 0M158 55v7"/></g>' + bars)


def art_sentinel():
    sp = f'calcMode="spline" keyTimes="0;.5;1" keySplines="{spl(2)}"'
    blips = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{c}"><animate attributeName="r" values="2.5;5;2.5" dur="{dd}s" repeatCount="indefinite" {sp}/>'
                    f'<animate attributeName="opacity" values="1;.35;1" dur="{dd}s" repeatCount="indefinite"/></circle>'
                    for x, y, c, dd in ((60, 70, "#fbbf24", 2.8), (146, 112, "#f87171", 3.3), (150, 58, "#fbbf24", 2.4)))
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a1628"/><stop offset="1" stop-color="#0e3a3f"/></linearGradient>'
            f'<linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/><stop offset="1" stop-color="{TEAL}" stop-opacity=".4"/></linearGradient></defs>'
            '<rect width="200" height="190" fill="url(#a)"/>'
            '<g fill="none" stroke="#1b5f66" stroke-width="1"><circle cx="100" cy="95" r="26"/><circle cx="100" cy="95" r="52"/><circle cx="100" cy="95" r="78"/>'
            '<path d="M22 95h156M100 17v156"/></g>'
            '<g transform="translate(100 95)"><path d="M0 0L78 0A78 78 0 0 0 55 -55z" fill="url(#sw)">'
            '<animateTransform attributeName="transform" type="rotate" values="0;360" dur="7s" repeatCount="indefinite"/></path></g>' + blips +
            f'<path d="M100 56L130 67V93C130 113 117 126 100 134C83 126 70 113 70 93V67Z" fill="#0b2531" stroke="{TEAL}" stroke-width="3"/>'
            f'<g><rect x="86" y="96" width="7" height="14" rx="1.5" fill="{MINT}"/><rect x="96.5" y="86" width="7" height="24" rx="1.5" fill="{MINT}"/>'
            f'<rect x="107" y="78" width="7" height="32" rx="1.5" fill="#f87171"/></g>')


ART = {"skymart": art_skymart, "fintrack-pro": art_fintrack, "fluent-ai": art_fluent, "mplads-sentinel-ai": art_sentinel}
NARROW_OY = {"skymart": 54, "fintrack-pro": 42, "fluent-ai": 50, "mplads-sentinel-ai": 50}


def ring(cx, cy, r, slices, center, sub, csize):
    C = 2 * math.pi * r
    out = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#12332b" stroke-width="5"/>'
    cum = 0.0
    for frac, col in slices:
        seg = max(frac * C - 2.5, 1)
        out += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="5" stroke-dasharray="{seg:.2f} {C:.2f}" '
                f'stroke-dashoffset="{-cum * C:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        cum += frac
    return (out + f'<text x="{cx}" y="{cy + csize * .2:.1f}" text-anchor="middle" font-size="{csize}" font-weight="700" fill="{TEXT}">{esc(center)}</text>'
            f'<text x="{cx}" y="{cy + csize * .2 + 11:.1f}" text-anchor="middle" font-size="8.5" fill="{MUTED}">{esc(sub)}</text>')


SHORT = {"JavaScript": "js", "TypeScript": "ts", "Python": "py", "Jupyter Notebook": "ipynb"}


def ring_for(proj, langs, cx, cy, r, csize):
    if langs:
        cols = [YEL, TEAL, VIOLET]
        sl = [(p / 100, cols[i]) for i, (_, p) in enumerate(langs[:3])]
        left = 100 - sum(p for _, p in langs[:3])
        if left > 0.5:
            sl.append((left / 100, DIM))
        return (ring(cx, cy, r, sl, f"{langs[0][1]:.0f}%", SHORT.get(langs[0][0], langs[0][0][:6].lower()), csize),
                ", ".join(f"{k} {p:.0f}%" for k, p in langs[:3]))
    n = max(len(proj["tags"]), 1)
    return ring(cx, cy, r, [(1 / n, GREEN)] * n, str(n), "tech", csize), "stack: " + ", ".join(proj["tags"])


def tags_svg(tags, x, y, max_x, size, h, step_y):
    out, cx = "", x
    for t in tags:
        w = len(t) * size * 0.6 + 14
        if cx + w > max_x and cx > x:
            cx, y = x, y + step_y
        out += (f'<rect x="{cx:.0f}" y="{y}" width="{w:.0f}" height="{h}" rx="5" fill="#07211a" stroke="#0f5a45"/>'
                f'<text x="{cx + w / 2:.0f}" y="{y + h * .7:.0f}" text-anchor="middle" font-size="{size}" fill="{MINT}">{esc(t)}</text>')
        cx += w + 6
    return out


def top_label(proj, info, handle):
    if proj.get("live"):
        return proj["live"].replace("https://", "").replace("http://", "").rstrip("/"), True
    if info:
        return f'{handle}/{info["name"]}', False
    return proj["category"], False


def build_card(proj, info, langs, handle, narrow):
    slug = proj["slug"]
    art = ART[slug]()
    label, is_live = top_label(proj, info, handle)
    if narrow:
        W, H, ah = 260, 304, 118
        oy = NARROW_OY[slug]
        art_el = f'<svg x="0" y="0" width="{W}" height="{ah}" viewBox="0 {oy} 200 {200 * ah / W:.1f}" preserveAspectRatio="xMidYMid slice">{art}</svg>'
        art_clip = f'<clipPath id="ac"><path d="M0 {ah}V12a12 12 0 0 1 12-12H{W - 12}a12 12 0 0 1 12 12V{ah}z"/></clipPath>'
        tx, rr, cx, cy, cs = 18, 22, 222, 266, 12
        chip_x, chip_y = W - 66, ah + 10
    else:
        W, H, aw = 520, 196, 200
        art_el = f'<svg x="0" y="0" width="{aw}" height="{H}" viewBox="0 0 200 190" preserveAspectRatio="xMidYMid slice">{art}</svg>'
        art_clip = f'<clipPath id="ac"><path d="M0 12a12 12 0 0 1 12-12H{aw}V{H}H12a12 12 0 0 1-12-12z"/></clipPath>'
        tx, rr, cx, cy, cs = 220, 30, 462, 104, 14
        chip_x, chip_y = W - 70, 14
    ring_svg, tip = ring_for(proj, langs, cx, cy, rr, cs)
    lim = 34 if not narrow else 30
    lab = label if len(label) <= lim else label[:lim - 3] + "..."
    chip = ""
    if is_live:
        chip = (f'<rect x="{chip_x}" y="{chip_y}" width="52" height="18" rx="9" fill="#052a1c" stroke="#0f6a45"/>'
                f'<circle cx="{chip_x + 13}" cy="{chip_y + 9}" r="3" fill="{GREEN}"><animate attributeName="opacity" values="1;.3;1" dur="2.4s" repeatCount="indefinite"/></circle>'
                f'<text x="{chip_x + 35}" y="{chip_y + 12.5}" text-anchor="middle" font-size="9.5" fill="{GREEN}">LIVE</text>')
    tsz = (21 if len(proj["title"]) <= 14 else 18) if not narrow else (18 if len(proj["title"]) <= 14 else 16)
    cat = "" if lab == proj["category"] else proj["category"]
    if not narrow:
        dl = wrap(proj["blurb"], 30)[:3]
        t = (f'<text x="{tx}" y="38" font-size="10.5" fill="{MUTED}">{esc(lab)}</text>'
             f'<text x="{tx}" y="72" font-size="{tsz}" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(proj["title"])}</text>'
             + "".join(f'<text x="{tx}" y="{95 + i * 16}" font-size="12.5" font-family="{SANS}" fill="{MINT}">{esc(l)}</text>' for i, l in enumerate(dl))
             + tags_svg(proj["tags"], tx, 148, 498, 10.5, 20, 26)
             + f'<text x="{W - 22}" y="{H - 12}" text-anchor="end" font-size="9.5" fill="{DIM}">{esc(cat)}</text>')
    else:
        dl = wrap(proj["blurb"], 32)[:3]
        t = (f'<text x="{tx}" y="{ah + 26}" font-size="9.5" fill="{MUTED}">{esc(lab)}</text>'
             f'<text x="{tx}" y="{ah + 52}" font-size="{tsz}" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(proj["title"])}</text>'
             + "".join(f'<text x="{tx}" y="{ah + 72 + i * 15}" font-size="11.5" font-family="{SANS}" fill="{MINT}">{esc(l)}</text>' for i, l in enumerate(dl))
             + tags_svg(proj["tags"], tx, 234, 188, 10, 18, 24)
             + f'<text x="{tx}" y="{H - 14}" font-size="9" fill="{DIM}">{esc(cat)}</text>')
    aria = f'{proj["title"]}: {proj["blurb"]}. {tip}'
    body = (f'<clipPath id="cc"><rect width="{W}" height="{H}" rx="12"/></clipPath>{art_clip}'
            f'<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="url(#cb)"/><g clip-path="url(#ac)">{art_el}</g>{t}{chip}{ring_svg}</g>'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="12" fill="none" stroke="{FRAME2}" stroke-width="1.5"/>')
    defs = '<linearGradient id="cb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#041510"/><stop offset="1" stop-color="#030c09"/></linearGradient>'
    return svg(W, H, aria, body, defs)


# --------------------------------------------------------------------------- #
# demo + orchestration
# --------------------------------------------------------------------------- #
def demo_data(cfg):
    """SYNTHETIC numbers for layout QA only. Written to ./preview/, never to assets/."""
    rnd = random.Random(11)
    end = date(2026, 10, 24)
    days = {}
    for i in range(365):
        dd = end - timedelta(days=364 - i)
        days[dd.isoformat()] = rnd.choice([1, 2, 3, 5, 8, 12]) if rnd.random() < .45 else 0
    tot = sum(days.values())
    resolved = {p["slug"]: {"name": p["slug"], "url": f'https://github.com/{cfg["handle"]}/{p["slug"]}', "homepage": None, "langs_url": "", "why": "demo"} for p in cfg["projects"]}
    return {"user": {"public_repos": 9, "followers": 4, "since": "2023"}, "cal": {"days": days, "total": tot, "commits": int(tot * .7), "source": "demo"},
            "weeks": to_weeks(days), "commits": int(tot * .7), "repos": [{"stargazers_count": 3, "fork": False}], "streak": streaks(days),
            "langs": [("JavaScript", 46.0), ("Python", 28.0), ("CSS", 17.0), ("HTML", 9.0)], "resolved": resolved,
            "repo_langs": {"skymart": [("JavaScript", 70.0), ("CSS", 25.0), ("HTML", 5.0)]}, "ok_any": True}


def render_all(d, cfg, out, demo=False, pending=False):
    h = cfg["handle"]
    m = view(d, cfg) if not pending else {}
    langs = d.get("langs") if not pending else None
    wide = None if pending else build_stats(m, langs, cfg, False, demo)
    if wide:
        write(os.path.join(out, "stats.svg"), wide)
        write(os.path.join(out, "stats-narrow.svg"), build_stats(m, langs, cfg, True, demo))
    else:
        if not pending:
            note("warning", "no headline metrics available; wrote the compact summary panel instead")
        write(os.path.join(out, "stats.svg"), build_stats_pending(cfg))
        write(os.path.join(out, "stats-narrow.svg"), build_stats_pending(cfg, True))
    if not pending and d.get("weeks"):
        write(os.path.join(out, "contributions.svg"), build_contrib(m, d, cfg, demo))
    else:
        if not pending:
            note("warning", "no contribution calendar available; wrote the compact placeholder instead")
        write(os.path.join(out, "contributions.svg"), build_contrib_pending(cfg))
    for p in cfg["projects"]:
        info = None if pending else d.get("resolved", {}).get(p["slug"])
        langs_p = None if pending else d.get("repo_langs", {}).get(p["slug"])
        write(os.path.join(out, f'proj-{p["slug"]}.svg'), build_card(p, info, langs_p, h, False))
        write(os.path.join(out, f'proj-{p["slug"]}-narrow.svg'), build_card(p, info, langs_p, h, True))
    if not demo:
        resolved = {} if pending else {k: {"name": v["name"], "url": v["url"]} for k, v in d.get("resolved", {}).items()}
        write(os.path.join(out, "resolved.json"), json.dumps(resolved, indent=2) + "\n")


def main():
    cfg = load_config()
    if "--demo" in sys.argv:
        render_all(demo_data(cfg), cfg, os.path.join(ROOT, "preview"), demo=True)
        return 0
    if "--pending" in sys.argv:
        render_all({}, cfg, OUT_DIR, pending=True)
        return 0
    d = collect(cfg)
    if not d["ok_any"]:
        note("error", "GitHub returned no data at all (see the warnings above). Existing assets were NOT modified. "
                      "Fix the cause (token, rate limit, username, network) and re-run the workflow.")
        write_summary()
        return 1
    render_all(d, cfg, OUT_DIR)
    write_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
