#!/usr/bin/env python3
"""Builds the assets that depend on live GitHub data, into assets/generated/:

  stats.svg / stats-narrow.svg      three headline metrics, gauge, language bar
  runner.svg                        contribution grid with a pixel runner
  proj-<slug>.svg / -narrow.svg     project cards (desktop landscape / phone portrait)
  proj-more.svg / -narrow.svg       "all repositories" card

Data comes from the GitHub GraphQL + REST APIs for the user in config/profile.json.
Nothing is estimated: a value that cannot be fetched is drawn as "n/a".

  python .github/scripts/make_stats.py            # real data (needs network; GITHUB_TOKEN optional)
  python .github/scripts/make_stats.py --demo     # SYNTHETIC data into ./preview/ for design QA only

Failure policy: if the API is unreachable and an asset already exists, the existing
file is left untouched, so a flaky run never replaces good numbers with "n/a".
"""
import math
import os
import random
import sys
from datetime import date

from lib import (BG0, DIM, FONT, FRAME, FRAME2, GREEN, MINT, MUTED, PANEL, ROOT, TEAL, TEXT,
                 VIOLET, YEL, Px, anim_pts, esc, graphql, load_config, rest, tw, wrap, write)

OUT_DIR = os.path.join(ROOT, "assets", "generated")

GQL = """query($login:String!){user(login:$login){
  repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){totalCount}
  contributionsCollection{totalCommitContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def collect(cfg):
    """Returns a dict; any field that could not be fetched is None."""
    user = cfg["handle"]
    d = {"total": None, "commits": None, "repos": None, "weeks": None, "first": None,
         "active": None, "per_active": None, "langs": None, "repo_langs": {}, "demo": False}
    try:
        u = graphql(GQL, {"login": user})["user"]
        cc = u["contributionsCollection"]
        cal = cc["contributionCalendar"]
        weeks, days = [], []
        for w in cal["weeks"]:
            col = [None] * 7
            for x in w["contributionDays"]:
                col[x["weekday"]] = x["contributionCount"]
                days.append(x)
            weeks.append(col)
        days.sort(key=lambda x: x["date"])
        d.update(total=cal["totalContributions"], commits=cc["totalCommitContributions"],
                 repos=u["repositories"]["totalCount"], weeks=weeks,
                 first=days[0]["date"] if days else None)
        d["active"] = sum(1 for x in days if x["contributionCount"] > 0)
        d["per_active"] = round(d["total"] / d["active"], 1) if d["active"] else None
    except Exception as e:  # noqa: BLE001 - report and carry on
        print("warning: contribution data unavailable:", e)
    try:
        repos = rest(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner")
        own = [r for r in repos if not r.get("fork")]
        want = {p["repo"] for p in cfg["projects"] if p.get("repo")}
        totals = {}
        for r in own:
            try:
                got = rest(r["languages_url"])
            except Exception:  # noqa: BLE001
                continue
            for k, b in got.items():
                totals[k] = totals.get(k, 0) + b
            if r["name"] in want and got:
                s = sum(got.values())
                d["repo_langs"][r["name"]] = [(k, 100 * b / s) for k, b in
                                              sorted(got.items(), key=lambda kv: -kv[1])]
        s = sum(totals.values())
        d["langs"] = [(k, 100 * b / s) for k, b in sorted(totals.items(), key=lambda kv: -kv[1])] if s else []
    except Exception as e:  # noqa: BLE001
        print("warning: language data unavailable:", e)
    return d


def demo_data(cfg):
    """SYNTHETIC numbers. Used only by --demo for layout QA; never written to assets/."""
    rnd = random.Random(11)
    weeks = [[None] * 7 for _ in range(53)]
    for w in range(53):
        for dd in range(7):
            if w == 52 and dd > 3:
                continue
            weeks[w][dd] = rnd.choice([0, 0, 0, 1, 2, 3, 5, 9]) if rnd.random() < 0.55 else 0
    flat = [c for w in weeks for c in w if c is not None]
    total, active = sum(flat), sum(1 for c in flat if c)
    return {"total": total, "commits": int(total * .8), "repos": 7, "weeks": weeks, "first": "2000-01-01",
            "active": active, "per_active": round(total / active, 1),
            "langs": [("LangA", 46.0), ("LangB", 28.0), ("LangC", 17.0), ("LangD", 9.0)],
            "repo_langs": {}, "demo": True}


def complete(d):
    return all(d[k] is not None for k in ("total", "repos", "weeks", "langs"))


# --------------------------------------------------------------------------- #
# stats panel
# --------------------------------------------------------------------------- #
def na(v, fmt=str):
    return fmt(v) if v is not None else "n/a"


def gauge(cx, cy, r, frac, num, size):
    C = 2 * math.pi * r
    f = 0 if frac is None else max(0.0, min(1.0, frac))
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#12332b" stroke-width="5"/>'
            + (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#arc)" stroke-width="5" stroke-linecap="round" '
               f'stroke-dasharray="{f * C:.1f} {C:.1f}" transform="rotate(-90 {cx} {cy})">'
               f'<animate attributeName="stroke-dasharray" values="0 {C:.1f};{f * C:.1f} {C:.1f}" dur="1.6s" begin="0s" '
               f'fill="freeze" calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1"/></circle>' if f > 0 else '')
            +
            f'<text x="{cx}" y="{cy + size * .35:.1f}" text-anchor="middle" font-size="{size}" font-weight="700" '
            f'fill="{TEXT if num != "n/a" else MUTED}">{esc(num)}</text>')


def metric(cx, y, num, label, sub, size, lsize, ssize):
    col = TEXT if num != "n/a" else MUTED
    return (f'<text x="{cx}" y="{y}" text-anchor="middle" font-size="{size}" font-weight="700" fill="{col}">{esc(num)}</text>'
            f'<text x="{cx}" y="{y + size * .45 + 12:.0f}" text-anchor="middle" font-size="{lsize}" font-weight="700" fill="{TEXT}">{esc(label)}</text>'
            f'<text x="{cx}" y="{y + size * .45 + 12 + ssize + 8:.0f}" text-anchor="middle" font-size="{ssize}" fill="{MUTED}">{esc(sub)}</text>')


ICON_STAR = '<path d="M8 1.5l1.9 4 4.3.5-3.2 3 .9 4.3L8 11.1 4.1 13.3 5 9 1.8 6l4.3-.5z"/>'
ICON_CLOCK = '<circle cx="8" cy="8" r="6.3"/><path d="M8 4.5V8l2.4 1.6"/>'
ICON_CAL = '<rect x="2" y="3" width="12" height="11" rx="2"/><path d="M2 6.5h12M5.5 1.5v3M10.5 1.5v3"/>'


def sub_panel(x, y, w, h, title, tsize):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#040d0b" stroke="{FRAME2}" stroke-width="1.2"/>'
            f'<text x="{x + 26}" y="{y + 38}" font-size="{tsize}" font-weight="700" fill="{TEXT}">{esc(title)}</text>')


LANG_COL = [MINT, TEAL, YEL, VIOLET, GREEN]


def lang_block(d, x, y, w, narrow):
    out = ""
    langs = d["langs"]
    bx, bw = x + 26, w - 52
    if langs is None:
        return out + f'<text x="{bx}" y="{y + 20}" font-size="13" fill="{MUTED}">n/a (language data unavailable)</text>'
    if not langs:
        return out + f'<text x="{bx}" y="{y + 20}" font-size="13" fill="{MUTED}">no language data yet</text>'
    top = langs[:4]
    rest_p = 100 - sum(p for _, p in top)
    segs = top + ([("other", rest_p)] if rest_p > 0.5 else [])
    out += f'<rect x="{bx}" y="{y}" width="{bw}" height="10" rx="5" fill="#12332b"/><clipPath id="lb"><rect x="{bx}" y="{y}" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#lb)">'
    cx = bx
    for i, (name, p) in enumerate(segs):
        sw = bw * p / 100
        col = LANG_COL[i] if name != "other" else DIM
        out += (f'<rect x="{cx:.1f}" y="{y}" width="{max(sw - 2, 1):.1f}" height="10" fill="{col}">'
                f'<animate attributeName="width" values="0;{max(sw - 2, 1):.1f}" dur="1.4s" begin="0s" fill="freeze" '
                f'calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1"/></rect>')
        cx += sw
    out += "</g>"
    ly, step = y + 36, (24 if narrow else 28)
    for i, (name, p) in enumerate(segs):
        col = LANG_COL[i] if name != "other" else DIM
        out += (f'<circle cx="{bx + 5}" cy="{ly - 4}" r="4.5" fill="{col}"/>'
                f'<text x="{bx + 18}" y="{ly}" font-size="13" fill="{TEXT}">{esc(name)}</text>'
                f'<text x="{bx + bw}" y="{ly}" text-anchor="end" font-size="13" fill="{MUTED}">{p:.1f}%</text>')
        ly += step
    return out


def build_stats(d, cfg, narrow):
    ok = d["total"] is not None
    frac = (d["commits"] / d["total"]) if (d["commits"] is not None and d["total"]) else None
    rng = f'{d["first"]} to present' if d["first"] and not d["demo"] else ("demo data" if d["demo"] else "unavailable")
    if not narrow:
        w, h = 1180, 484
        cols = (197, 590, 983)
        body = metric(cols[0], 108, na(d["total"]), "Total Contributions", rng, 46, 15, 11)
        body += gauge(590, 96, 48, frac, na(d["commits"]), 32)
        body += (f'<text x="590" y="172" text-anchor="middle" font-size="15" font-weight="700" fill="{TEXT}">Commits, last 12 months</text>')
        body += metric(cols[2], 108, na(d["repos"]), "Public Repositories", "owned, not forks", 46, 15, 11)
        body += (f'<line x1="393" y1="58" x2="393" y2="170" stroke="{FRAME}"/><line x1="787" y1="58" x2="787" y2="170" stroke="{FRAME}"/>'
                 f'<line x1="60" y1="204" x2="1120" y2="204" stroke="{FRAME2}"/>')
        py, ph, lx, lw, rx_, rw = 228, 220, 40, 530, 610, 530
        row_y, row_step, lang_y = 312, 44, 292
    else:
        w, h = 560, 640
        cols = (93, 280, 467)
        body = metric(cols[0], 78, na(d["total"]), "Total", "contributions", 28, 12, 10)
        body += gauge(280, 66, 34, frac, na(d["commits"]), 22)
        body += f'<text x="280" y="124" text-anchor="middle" font-size="12" font-weight="700" fill="{TEXT}">Commits, 12 mo</text>'
        body += metric(cols[2], 78, na(d["repos"]), "Public", "repositories", 28, 12, 10)
        body += (f'<line x1="187" y1="40" x2="187" y2="124" stroke="{FRAME}"/><line x1="373" y1="40" x2="373" y2="124" stroke="{FRAME}"/>'
                 f'<line x1="30" y1="152" x2="530" y2="152" stroke="{FRAME2}"/>')
        py, ph, lx, lw, rx_, rw = 176, 190, 20, 520, 20, 520
        row_y, row_step, lang_y = 238, 36, 0
    # left panel
    stats = [(ICON_STAR, "Top Language", (d["langs"][0][0] if d["langs"] else None)),
             (ICON_CAL, "Active Days", d["active"]),
             (ICON_CLOCK, "Contributions / Active Day", d["per_active"])]
    body += sub_panel(lx, py, lw, ph, f'{cfg["handle"]}\'s GitHub Stats', 16 if not narrow else 15)
    yy = row_y if not narrow else py + 76
    for ic, lab, val in stats:
        vtxt = "n/a" if val is None else str(val)
        body += (f'<g transform="translate({lx + 26} {yy - 14})" fill="none" stroke="{MINT}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{ic}</g>'
                 f'<text x="{lx + 54}" y="{yy}" font-size="{14 if not narrow else 13}" fill="{TEXT}">{esc(lab)}</text>'
                 f'<text x="{lx + lw - 26}" y="{yy}" text-anchor="end" font-size="{14 if not narrow else 13}" font-weight="700" '
                 f'fill="{TEXT if val is not None else MUTED}">{esc(vtxt)}</text>')
        yy += row_step
    # right panel
    if narrow:
        py2 = py + ph + 20
        ph2 = 640 - py2 - 24
    else:
        py2, ph2 = py, ph
    body += sub_panel(rx_, py2, rw, ph2, "Most Used Languages", 16 if not narrow else 15)
    body += lang_block(d, rx_, py2 + 66, rw, narrow)
    demo = (f'<text x="{w - 24}" y="26" text-anchor="end" font-size="11" fill="{YEL}">DEMO DATA, NOT REAL</text>' if d["demo"] else "")
    aria = (f'GitHub statistics for {cfg["handle"]}: ' +
            ("; ".join(f"{k} {v}" for k, v in (("total contributions", d["total"]), ("commits", d["commits"]),
                                                ("public repositories", d["repos"]), ("active days", d["active"])) if v is not None)
             or "data unavailable"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img" '
            f'aria-label="{esc(aria)}"><title>{esc(aria)}</title><defs>'
            f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="#05110d"/></linearGradient>'
            f'<linearGradient id="arc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{MINT}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>'
            f'<radialGradient id="gl" cx=".5" cy="1" r=".7"><stop offset="0" stop-color="{GREEN}" stop-opacity=".10"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>'
            f'</defs><rect width="{w}" height="{h}" rx="16" fill="url(#bg)"/><rect width="{w}" height="{h}" rx="16" fill="url(#gl)"/>'
            f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="16" fill="none" stroke="{FRAME}" stroke-width="1.5"/>'
            f'{demo}{body}</svg>')


# --------------------------------------------------------------------------- #
# contribution runner
# --------------------------------------------------------------------------- #
LV = ["#0c1f1b", "#0f4f40", "#11916f", "#2ee6a6", YEL]
PAL = {"c": TEAL, "s": "#f1c9a5", "k": "#0b1512", "h": "#2ee6a6", "d": "#14a37a", "p": "#1d3557", "y": YEL}
HEAD = ["...cccc...", "..cccccc..", "..ccccccc.", "..ssssks..", "...ssss..."]
LEGS = {
    "A": ["..dhhhhd..", ".shhhhhh..", "s.hhhhhhs.", "..hhhhhh..", "..pppppp..", "..pp..pp..", ".pp....pp.", ".yy.....yy"],
    "P": ["..dhhhhd..", "..hhhhhh..", ".shhhhhhs.", "..hhhhhh..", "..pppppp..", "..pp..pp..", "..pp..pp..", "..yy..yy.."],
    "B": ["..dhhhhd..", "..hhhhhhs.", ".shhhhhh.s", "..hhhhhh..", "..pppppp..", "..pp..pp..", "..pp...pp.", ".yy.....yy"],
}


def sprite(frame, s):
    p = Px(10, 13)
    p.art(0, 0, HEAD + LEGS[frame], PAL)
    return p.paths(s)


def levels(weeks):
    vals = sorted(c for w in weeks for c in w if c)
    if not vals:
        return lambda c: 0
    q = [vals[min(int(len(vals) * f), len(vals) - 1)] for f in (.25, .5, .75)]
    return lambda c: 0 if not c else 1 + sum(c > t for t in q)


def build_runner(d, cfg):
    weeks = d["weeks"] or [[0] * 7 for _ in range(53)]
    lv = levels(weeks)
    W, H, cell, gap = 1180, 424, 14, 6
    pitch = cell + gap
    cols = len(weeks)
    gw = cols * pitch - gap
    x0, y0, ground = (W - gw) / 2, 92, 364
    T, S = 18.0, 5
    xs, xe = x0 + cell / 2, x0 + gw - cell / 2
    cells, glow = [], []
    for i, w in enumerate(weeks):
        for j, c in enumerate(w):
            if c is None:
                continue
            x, y = x0 + i * pitch, y0 + j * pitch
            L = lv(c)
            cells.append(f'<rect x="{x:.0f}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LV[L]}"/>')
            if L:
                f = min(max((x + cell / 2 - xs) / (xe - xs), 0.002), 0.998)
                a = max(f - 0.006, 0.0005)
                b = min(f + 0.05, 0.9995)
                v, k = anim_pts([(0, 0), (a, 0), (f, 0.9), (b, 0), (1, 0)])
                glow.append(f'<rect x="{x:.0f}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="#eafff6" opacity="0">'
                            f'<animate attributeName="opacity" values="{v}" keyTimes="{k}" dur="{T:g}s" repeatCount="indefinite"/></rect>')
    rnd = random.Random(5)
    stars = "".join(f'<rect x="{rnd.randrange(30, W - 30)}" y="{rnd.randrange(236, 330)}" width="2" height="2" fill="{MINT}" opacity="{rnd.choice([.15, .25, .4])}"/>'
                    for _ in range(46))
    fr = ""
    seq = ["A", "P", "B", "P"]
    for k, name in enumerate(seq):
        vals = ";".join("1" if i == k else "0" for i in range(4))
        fr += (f'<g opacity="{1 if k == 0 else 0}"><animate attributeName="opacity" values="{vals}" keyTimes="0;.25;.5;.75" '
               f'calcMode="discrete" dur=".56s" repeatCount="indefinite"/>{sprite(name, S)}</g>')
    sy = ground - 13 * S
    runner = (f'<g transform="translate({xs - 5 * S:.0f} {sy})"><animateTransform attributeName="transform" type="translate" '
              f'values="{xs - 5 * S:.0f} {sy};{xe - 5 * S:.0f} {sy}" keyTimes="0;1" dur="{T:g}s" repeatCount="indefinite"/>'
              f'<ellipse cx="{5 * S}" cy="{13 * S + 2}" rx="{5 * S}" ry="3" fill="#000" opacity=".45"/>{fr}</g>')
    total = "n/a" if d["total"] is None else str(d["total"])
    note = ("" if d["weeks"] else
            f'<text x="{W / 2}" y="{y0 + 7 * pitch + 34}" text-anchor="middle" font-size="14" fill="{MUTED}">contribution data unavailable, the workflow fills this grid</text>')
    demo = (f'<text x="{W - 24}" y="30" text-anchor="end" font-size="11" fill="{YEL}">DEMO DATA, NOT REAL</text>' if d["demo"] else "")
    aria = (f'Contribution grid for the last 12 months with a pixel runner. Total contributions: {total}.')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" '
            f'aria-label="{esc(aria)}"><title>{esc(aria)}</title><defs>'
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05090c"/><stop offset="1" stop-color="#05120e"/></linearGradient>'
            f'<filter id="gg" x="-10%" y="-400%" width="120%" height="900%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
            f'<rect width="{W}" height="{H}" rx="14" fill="url(#sky)"/>{stars}'
            f'<circle cx="{x0 + 7:.0f}" cy="46" r="7" fill="{YEL}"/><circle cx="{x0 + 7:.0f}" cy="46" r="3" fill="none" stroke="#9a7416" stroke-width="1.4"/>'
            f'<text x="{x0 + 24:.0f}" y="52" font-size="17" fill="{TEXT}">x {total}</text>'
            f'<text x="{x0 + gw:.0f}" y="52" text-anchor="end" font-size="11" fill="{MUTED}">contributions, last 12 months</text>'
            f'{demo}{"".join(cells)}{note}{"".join(glow)}'
            f'<rect x="0" y="{ground}" width="{W}" height="{H - ground}" fill="#04120e"/>'
            f'<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{GREEN}" stroke-width="3" filter="url(#gg)" opacity=".8"/>'
            f'<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{GREEN}" stroke-width="2"/>{runner}'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="none" stroke="{FRAME}" stroke-width="1.5"/></svg>')


# --------------------------------------------------------------------------- #
# project cards
# --------------------------------------------------------------------------- #
def art_skymart():
    stripes = "".join(f'<rect x="{62 + i * 12.67:.2f}" y="78" width="12.67" height="14" fill="{"#ef4444" if i % 2 == 0 else "#fff7ed"}"/>'
                      f'<circle cx="{62 + i * 12.67 + 6.33:.2f}" cy="92" r="6.33" fill="{"#ef4444" if i % 2 == 0 else "#fff7ed"}"/>' for i in range(6))
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2563eb"/><stop offset=".6" stop-color="#8b5cf6"/>'
            '<stop offset="1" stop-color="#f472b6"/></linearGradient></defs><rect width="200" height="190" fill="url(#a)"/>'
            '<g fill="#fff" opacity=".85"><rect x="18" y="38" width="36" height="8"/><rect x="26" y="31" width="20" height="8"/>'
            '<rect x="142" y="56" width="32" height="7"/><rect x="150" y="49" width="16" height="7"/></g>'
            '<g fill="#fff"><rect x="120" y="30" width="2" height="2"/><rect x="40" y="62" width="2" height="2"/><rect x="170" y="30" width="2" height="2"/></g>'
            '<rect x="0" y="146" width="200" height="44" fill="#1e1b4b"/><rect x="0" y="146" width="200" height="3" fill="#a78bfa" opacity=".6"/>'
            '<rect x="62" y="92" width="76" height="54" fill="#fef3c7"/>' + stripes +
            '<rect x="92" y="114" width="16" height="32" rx="2" fill="#7c3aed"/><rect x="68" y="104" width="18" height="18" rx="2" fill="#bae6fd"/>'
            '<rect x="114" y="104" width="18" height="18" rx="2" fill="#bae6fd"/><rect x="76" y="62" width="48" height="13" rx="3" fill="#111827"/>'
            '<text x="100" y="72.5" text-anchor="middle" font-size="9.5" font-weight="700" fill="#fde047">SKYMART</text>'
            '<g fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M148 108h7l5 22h22l4-15h-29"/>'
            '<circle cx="162" cy="137" r="2.6"/><circle cx="178" cy="137" r="2.6"/></g>'
            '<g><rect x="22" y="104" width="18" height="18" fill="#f59e0b" stroke="#b45309" stroke-width="1.5"/><rect x="29" y="104" width="4" height="18" fill="#fde68a"/></g>')


def art_fintrack():
    bars = "".join(f'<rect x="{34 + i * 26}" y="{140 - h}" width="18" height="{h}" rx="3" fill="{c}"/>'
                   for i, (h, c) in enumerate([(34, MINT), (52, TEAL), (40, MINT), (70, TEAL), (58, YEL)]))
    pts_ = [(43, 98), (69, 84), (95, 92), (121, 66), (147, 74), (173, 50)]
    line = " ".join(f"{x},{y}" for x, y in pts_)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{YEL}"/>' for x, y in pts_)
    C = 2 * math.pi * 14
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1f2a"/><stop offset="1" stop-color="#0f3d3a"/></linearGradient></defs>'
            '<rect width="200" height="190" fill="url(#a)"/><g stroke="#1b4a45" stroke-width="1"><line x1="20" y1="60" x2="190" y2="60"/><line x1="20" y1="100" x2="190" y2="100"/>'
            '<line x1="20" y1="140" x2="190" y2="140"/></g>' + bars +
            f'<polyline points="{line}" fill="none" stroke="{YEL}" stroke-width="2.5" stroke-linejoin="round"/>{dots}'
            f'<g transform="translate(38 36) rotate(-90)" fill="none" stroke-width="6"><circle r="14" stroke="#12332b"/>'
            f'<circle r="14" stroke="{GREEN}" stroke-dasharray="{C * .55:.1f} {C:.1f}"/><circle r="14" stroke="{YEL}" stroke-dasharray="{C * .25:.1f} {C:.1f}" stroke-dashoffset="{-C * .58:.1f}"/></g>'
            '<g><ellipse cx="160" cy="158" rx="16" ry="6" fill="#b45309"/><ellipse cx="160" cy="153" rx="16" ry="6" fill="#f59e0b"/>'
            '<ellipse cx="160" cy="148" rx="16" ry="6" fill="#fcd34d"/><text x="160" y="151" text-anchor="middle" font-size="8" font-weight="700" fill="#92400e">$</text></g>')


def art_fluent():
    bars = "".join(f'<rect x="{46 + i * 11}" y="{165 - h / 2}" width="6" height="{h}" rx="3" fill="#fff" opacity=".85"/>'
                   for i, h in enumerate([8, 18, 28, 14, 34, 22, 12, 26, 10]))
    return ('<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset=".55" stop-color="#7c3aed"/>'
            '<stop offset="1" stop-color="#f0abfc"/></linearGradient></defs><rect width="200" height="190" fill="url(#a)"/>'
            '<g><rect x="26" y="52" width="76" height="38" rx="12" fill="#fff"/><path d="M40 88l-4 12 16-12z" fill="#fff"/>'
            '<text x="64" y="77" text-anchor="middle" font-size="15" font-weight="700" fill="#4c1d95">Hi!</text></g>'
            '<g><rect x="92" y="98" width="82" height="36" rx="12" fill="#a7f3d0"/><path d="M160 132l6 11-18-11z" fill="#a7f3d0"/>'
            '<circle cx="119" cy="116" r="4" fill="#064e3b"/><circle cx="133" cy="116" r="4" fill="#064e3b"/><circle cx="147" cy="116" r="4" fill="#064e3b"/></g>'
            '<g fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"><rect x="152" y="30" width="12" height="20" rx="6" fill="#fff" stroke="none"/>'
            '<path d="M147 44a11 11 0 0 0 22 0M158 55v7"/></g>' + bars)


def art_more():
    return (f'<rect width="200" height="190" fill="#03120d"/><g fill="{DIM}" opacity=".5"><rect x="0" y="0" width="200" height="1"/></g>'
            f'<g font-size="13" font-family="{FONT}"><text x="22" y="76" fill="{GREEN}">$ ls ~/repos</text><text x="22" y="98" fill="{MINT}">--all</text>'
            f'<text x="22" y="132" fill="{TEAL}">$ _</text></g><rect x="52" y="121" width="8" height="14" fill="{GREEN}"><animate attributeName="opacity" '
            f'values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>'
            f'<g fill="none" stroke="{GREEN}" stroke-opacity=".5" stroke-width="2"><path d="M150 54l-20 20 20 20M170 54l20 20-20 20" transform="translate(6 6)"/></g>')


ART = {"skymart": art_skymart, "fintrack-pro": art_fintrack, "fluent-ai": art_fluent, "more": art_more}


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


def ring_for(proj, d, cx, cy, r, csize):
    langs = d["repo_langs"].get(proj.get("repo") or "")
    if langs:
        cols = [YEL, TEAL, VIOLET]
        sl = [(p / 100, cols[i]) for i, (_, p) in enumerate(langs[:3])]
        left = 100 - sum(p for _, p in langs[:3])
        if left > 0.5:
            sl.append((left / 100, DIM))
        return ring(cx, cy, r, sl, f"{langs[0][1]:.0f}%", SHORT.get(langs[0][0], langs[0][0][:6].lower()), csize), \
            ", ".join(f"{k} {p:.0f}%" for k, p in langs[:3])
    n = max(len(proj["tags"]), 1)
    return ring(cx, cy, r, [(1 / n, GREEN)] * n, str(n), "tech", csize), "stack: " + ", ".join(proj["tags"])


def tags_svg(tags, x, y, max_x, size, h, step_y):
    out, cx = "", x
    for t in tags:
        w = len(t) * size * 0.6 + 14
        if cx + w > max_x and cx > x:
            cx, y = x, y + step_y
        out += (f'<rect x="{cx:.0f}" y="{y}" width="{w:.0f}" height="{h}" rx="4" fill="#07211a" stroke="#0f5a45"/>'
                f'<text x="{cx + w / 2:.0f}" y="{y + h * .7:.0f}" text-anchor="middle" font-size="{size}" fill="{MINT}">{esc(t)}</text>')
        cx += w + 6
    return out


def build_card(proj, d, narrow):
    slug = proj["slug"]
    art = ART[slug]()
    if narrow:
        W, H, ah = 260, 300, 118
        oy = {"skymart": 54, "fintrack-pro": 42, "fluent-ai": 50, "more": 52}[slug]
        art_el = (f'<svg x="0" y="0" width="{W}" height="{ah}" viewBox="0 {oy} 200 {200 * ah / W:.1f}" preserveAspectRatio="xMidYMid slice">{art}</svg>')
        art_clip = f'<clipPath id="ac"><path d="M0 {ah}V12a12 12 0 0 1 12-12H{W - 12}a12 12 0 0 1 12 12V{ah}z"/></clipPath>'
        tx = 18
    else:
        W, H, aw = 520, 190, 200
        art_el = f'<svg x="0" y="0" width="{aw}" height="{H}" viewBox="0 0 200 190">{art}</svg>'
        art_clip = f'<clipPath id="ac"><path d="M0 12a12 12 0 0 1 12-12H{aw}V{H}H12a12 12 0 0 1-12-12z"/></clipPath>'
        tx = 220
    # ring + tooltip text
    if slug == "more":
        rr = 22 if narrow else 30
        cx, cy = (222, 262) if narrow else (462, 98)
        val = "n/a" if d["repos"] is None else str(d["repos"])
        ring_svg = ring(cx, cy, rr, [(1.0, TEAL)] if d["repos"] is not None else [], val, "repos", 15 if not narrow else 13)
        tip = ""
    else:
        rr = 22 if narrow else 30
        cx, cy = (222, 262) if narrow else (462, 98)
        ring_svg, tip = ring_for(proj, d, cx, cy, rr, 14 if not narrow else 12)
    title_w = tw(proj["title"], 22 if not narrow else 18)
    if not narrow:
        dl = wrap(proj["blurb"], 26)[:3]
        t = (f'<circle cx="{tx + 3}" cy="32" r="3" fill="{GREEN}"/><text x="{tx + 12}" y="36" font-size="10.5" fill="{MUTED}">{esc(proj["label"])}</text>'
             f'<text x="{tx}" y="72" font-size="22" font-weight="700" fill="{TEXT}">{esc(proj["title"])}</text>'
             f'<rect x="{tx + title_w + 2:.0f}" y="66" width="11" height="3.5" fill="{GREEN}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>'
             + "".join(f'<text x="{tx}" y="{94 + i * 16}" font-size="12.5" fill="{MINT}">{esc(l)}</text>' for i, l in enumerate(dl))
             + tags_svg(proj["tags"], tx, 142, 498, 10.5, 20, 26)
             + f'<text x="{W - 22}" y="{H - 14}" text-anchor="end" font-size="9.5" fill="{DIM}">{esc(proj["category"])}</text>')
    else:
        dl = wrap(proj["blurb"], 30)[:3]
        t = (f'<circle cx="{tx + 3}" cy="{ah + 22}" r="3" fill="{GREEN}"/><text x="{tx + 12}" y="{ah + 26}" font-size="9.5" fill="{MUTED}">{esc(proj["label"])}</text>'
             f'<text x="{tx}" y="{ah + 52}" font-size="18" font-weight="700" fill="{TEXT}">{esc(proj["title"])}</text>'
             f'<rect x="{tx + title_w + 2:.0f}" y="{ah + 47}" width="9" height="3" fill="{GREEN}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>'
             + "".join(f'<text x="{tx}" y="{ah + 72 + i * 15}" font-size="11" fill="{MINT}">{esc(l)}</text>' for i, l in enumerate(dl))
             + tags_svg(proj["tags"], tx, 228, 188, 10, 18, 24)
             + f'<text x="{tx}" y="{H - 14}" font-size="9" fill="{DIM}">{esc(proj["category"])}</text>')
    aria = f'{proj["title"]}: {proj["blurb"]}. ' + (tip or "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" '
            f'aria-label="{esc(aria)}"><title>{esc(aria)}</title><defs>{art_clip}'
            f'<clipPath id="cc"><rect width="{W}" height="{H}" rx="12"/></clipPath>'
            f'<linearGradient id="cb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#041510"/><stop offset="1" stop-color="#030c09"/></linearGradient></defs>'
            f'<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="url(#cb)"/><g clip-path="url(#ac)">{art_el}</g>{t}{ring_svg}</g>'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="12" fill="none" stroke="{FRAME2}" stroke-width="1.5"/></svg>')


# --------------------------------------------------------------------------- #
def targets(cfg, d):
    t = {"stats.svg": lambda: build_stats(d, cfg, False), "stats-narrow.svg": lambda: build_stats(d, cfg, True),
         "runner.svg": lambda: build_runner(d, cfg)}
    more = {"slug": "more", "title": "More", "blurb": "every public repository, in one place", "category": "all repos",
            "label": f'github.com/{cfg["handle"]}', "tags": ["github"], "repo": None}
    for p in cfg["projects"] + [more]:
        t[f'proj-{p["slug"]}.svg'] = (lambda p=p: build_card(p, d, False))
        t[f'proj-{p["slug"]}-narrow.svg'] = (lambda p=p: build_card(p, d, True))
    return t


def main():
    cfg = load_config()
    demo = "--demo" in sys.argv
    if demo:
        d, out = demo_data(cfg), os.path.join(ROOT, "preview")
    else:
        d, out = collect(cfg), OUT_DIR
    ok = demo or complete(d)
    for name, make in targets(cfg, d).items():
        path = os.path.join(out, name)
        if not ok and os.path.exists(path):
            print(f"kept existing {os.path.relpath(path, ROOT)} (data incomplete this run)")
            continue
        write(path, make())
    if not ok:
        print("note: data was incomplete; see warnings above. Existing assets were kept as they were.")


if __name__ == "__main__":
    main()
