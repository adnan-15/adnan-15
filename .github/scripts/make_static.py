#!/usr/bin/env python3
"""Builds the assets that only change when config/profile.json changes:

  assets/hero.svg, assets/hero-narrow.svg   terminal hero (desktop / phone layout)
  assets/tagline.svg                        rotating one-line tagline
  assets/tech-stack.svg                     technology tiles
  assets/btn-*.svg                          footer link buttons

Run from the repo root:   python .github/scripts/make_static.py
Only the standard library is used.

GitHub serves README images through a cache (camo) keyed by URL. If you change
something visible, bump the file name AND the README reference together,
otherwise visitors keep seeing the first version that was ever fetched.
"""
import os
import random

from lib import (BG0, DIM, FONT, FRAME, GREEN, GRN_D, MINT, MUTED, PANEL, RED_D, ROOT,
                 TEAL, TEXT, YEL, YEL_D, Px, anim_pts, esc, load_config, tw, window, write)

A = os.path.join(ROOT, "assets")

# --------------------------------------------------------------------------- #
# pixel-art scenes for the VISUAL.MAP panel (44 x 47 cells, 10 px each)
# --------------------------------------------------------------------------- #
GW, GH, CELL = 44, 47, 10


def sparkles(p, seed, n=16):
    rnd = random.Random(seed)
    for _ in range(n):
        p.set(rnd.randrange(1, GW - 1), rnd.randrange(1, GH - 1), rnd.choice(["#14503f", "#1b6b55", "#0f3a2c"]))


def scene_code():
    p = Px(GW, GH)
    sparkles(p, 1)
    p.line(15, 11, 5, 24, "#ff6b6b", 3)
    p.line(5, 24, 15, 37, "#ff9f43", 3)
    p.line(29, 11, 39, 24, TEAL, 3)
    p.line(39, 24, 29, 37, "#3b82f6", 3)
    p.line(26, 8, 18, 40, GREEN, 3)
    return p


def scene_tree():
    p = Px(GW, GH)
    sparkles(p, 2)
    root, mid, leaf = (22, 9), [(11, 22), (33, 22)], [(5, 36), (17, 36), (27, 36), (39, 36)]
    edges = [(root, mid[0]), (root, mid[1]), (mid[0], leaf[0]), (mid[0], leaf[1]),
             (mid[1], leaf[2]), (mid[1], leaf[3])]
    hot = {(root, mid[0]), (mid[0], leaf[1])}
    for a, b in edges:
        p.line(*a, *b, GREEN if (a, b) in hot else "#1d6b52", 1)
    p.disc(*root, 3, GREEN)
    for m in mid:
        p.disc(*m, 3, GREEN if m == mid[0] else TEAL)
    for lf in leaf:
        p.disc(*lf, 3, GREEN if lf == leaf[1] else MINT)
    return p


def scene_net():
    p = Px(GW, GH)
    sparkles(p, 3)
    lay = [(6, [10, 19, 28, 37]), (22, [7, 16, 25, 34, 43]), (38, [14, 24, 34])]
    for (xa, ya), (xb, yb) in zip(lay, lay[1:]):
        for a in ya:
            for b in yb:
                p.line(xa, a, xb, b, "#134a3b", 1)
    p.line(6, 19, 22, 25, GREEN, 1)
    p.line(22, 25, 38, 24, GREEN, 1)
    cols = [TEAL, GREEN, YEL]
    for (x, ys), c in zip(lay, cols):
        for y in ys:
            p.disc(x, y, 2, c)
    return p


def scene_cup():
    p = Px(GW, GH)
    sparkles(p, 4)
    p.ring(35, 30, 5, "#ED8B00", 2)
    for y in range(22, 40):
        k = (y - 22) // 6
        p.rect(11 + k, y, 21 - 2 * k, 1, "#ED8B00")
        p.rect(29 - k, y, 3, 1, "#b96a00")
    p.rect(10, 21, 23, 1, "#ffb347")
    p.rect(12, 22, 19, 1, "#5a2d0c")
    p.rect(6, 40, 32, 2, "#1b8a73")
    p.rect(10, 42, 24, 1, "#0f5a4a")
    for x0 in (16, 22, 28):
        for i in range(13):
            p.set(x0 + (1 if (i // 3) % 2 else 0), 18 - i, MINT if i < 7 else "#3a8d78")
    return p


SCENES = [("web / full-stack", scene_code), ("data structures + algorithms", scene_tree),
          ("ai / machine learning", scene_net), ("java", scene_cup)]
LOOP = 20.0  # seconds for the four scenes


def scene_layers(ox, oy, sc):
    out = []
    n = len(SCENES)
    for k, (_, fn) in enumerate(SCENES):
        v, t = anim_pts(window(k, n, 0.03))
        base = 1 if k == 0 else 0
        out.append(
            f'<g transform="translate({ox:g} {oy:g}) scale({sc:g})" opacity="{base}">'
            f'<animate attributeName="opacity" values="{v}" keyTimes="{t}" dur="{LOOP:g}s" repeatCount="indefinite"/>'
            f'<g filter="url(#glow)">{fn().paths(CELL)}</g>'
            f'<rect width="{GW * CELL}" height="{GH * CELL}" fill="url(#pg)"/></g>')
    return "".join(out)


def caption_layers(x, y):
    out = []
    n = len(SCENES)
    for k, (cap, _) in enumerate(SCENES):
        v, t = anim_pts(window(k, n, 0.03))
        out.append(
            f'<text x="{x}" y="{y}" font-size="13" fill="{TEAL}" opacity="{1 if k == 0 else 0}">&gt; {esc(cap)}'
            f'<animate attributeName="opacity" values="{v}" keyTimes="{t}" dur="{LOOP:g}s" repeatCount="indefinite"/></text>')
    return "".join(out)


# --------------------------------------------------------------------------- #
# key / value rows
# --------------------------------------------------------------------------- #
def strip_scheme(u):
    return u.replace("https://", "").replace("http://", "").replace("mailto:", "").rstrip("/")


def profile_rows(cfg):
    L = cfg["links"]
    rows = [
        ("kv", "Subject", cfg["name"], TEXT),
        ("kv", "Role", "B.Tech student", GREEN),
        ("kv", "Degree", cfg["degree"], GREEN),
        ("kv", "Handle", "@" + cfg["handle"], TEXT),
        ("kv", "Status", "Studying + building", TEXT),
        ("gap",),
        ("kv", "Core.Lang", "Java, Python, JavaScript", MINT),
        ("kv", "Core.Frontend", "React, Tailwind CSS, HTML, CSS", MINT),
        ("kv", "Core.Backend", "Django, FastAPI", MINT),
        ("kv", "Core.Data", "PostgreSQL", MINT),
        ("kv", "Core.Tools", "Git, GitHub", MINT),
        ("kv", "Core.Focus", "Full-stack, DSA, AI/ML", MINT),
        ("kv", "Ships", ", ".join(p["title"] for p in cfg["projects"]), GREEN),
        ("gap",),
        ("head", "- Contact"),
    ]
    if L.get("github"):
        rows.append(("kv", "Grid.GitHub", strip_scheme(L["github"]), TEAL))
    if L.get("linkedin"):
        rows.append(("kv", "Grid.LinkedIn", strip_scheme(L["linkedin"]), TEAL))
    if L.get("email"):
        rows.append(("kv", "Grid.Email", strip_scheme(L["email"]), TEAL))
    if L.get("portfolio"):
        rows.append(("kv", "Grid.Portfolio", strip_scheme(L["portfolio"]), TEAL))
    return rows


def render_rows(rows, x0, x1, y, step, size):
    out, i = [], 0
    for r in rows:
        if r[0] == "gap":
            y += step * 0.6
            continue
        if r[0] == "head":
            out.append(f'<text x="{x0}" y="{y}" font-size="{size - 2}" fill="{DIM}">{esc(r[1])} '
                       f'{"." * 6}</text>')
            y += step
            continue
        _, k, v, vc = r
        lx0, lx1 = x0 + tw(k, size) + 10, x1 - tw(v, size) - 10
        d = i * 0.08
        dur = 2.6
        a, b = d / dur, (d + 0.35) / dur
        g = (f'<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{a:.4f};{b:.4f};1" '
             f'dur="{dur}s" begin="0s" fill="freeze"/>'
             f'<text x="{x0}" y="{y}" fill="#4fd1a5">{esc(k)}</text>')
        if lx1 > lx0 + 14:
            g += (f'<line x1="{lx0:.0f}" y1="{y - 4}" x2="{lx1:.0f}" y2="{y - 4}" stroke="{DIM}" '
                  f'stroke-width="1.4" stroke-dasharray="1 5" stroke-linecap="round"/>')
        g += f'<text x="{x1}" y="{y}" text-anchor="end" fill="{vc}">{esc(v)}</text></g>'
        out.append(g)
        y += step
        i += 1
    return "".join(out), y


# --------------------------------------------------------------------------- #
# hero
# --------------------------------------------------------------------------- #
def hero_defs(w, h):
    return f'''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset=".55" stop-color="#060e12"/><stop offset="1" stop-color="#04090c"/></linearGradient>
  <radialGradient id="gA" cx=".78" cy=".5" r=".55"><stop offset="0" stop-color="{GREEN}" stop-opacity=".10"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
  <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse"><path d="M34 0H0V34" fill="none" stroke="{GREEN}" stroke-opacity=".035"/></pattern>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#7fffd4" fill-opacity=".03"/></pattern>
  <pattern id="pg" width="{CELL}" height="{CELL}" patternUnits="userSpaceOnUse"><path d="M{CELL} 0V{CELL}H0" fill="none" stroke="{PANEL}" stroke-width="1.8"/></pattern>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b"/><feComponentTransfer in="b" result="b2"><feFuncA type="linear" slope=".55"/></feComponentTransfer><feMerge><feMergeNode in="b2"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>'''


def chrome(w, h, title, narrow):
    r = 16
    dots = (f'<circle cx="28" cy="{22 if narrow else 26}" r="5.5" fill="{RED_D}"/>'
            f'<circle cx="48" cy="{22 if narrow else 26}" r="5.5" fill="{YEL_D}"/>'
            f'<circle cx="68" cy="{22 if narrow else 26}" r="5.5" fill="{GRN_D}"/>')
    ty = 26 if narrow else 31
    return (f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#bg)"/>'
            f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#grid)"/>'
            f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#gA)"/>'
            f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{r}" fill="none" stroke="{FRAME}" stroke-width="1.5"/>'
            f'{dots}<text x="{w / 2:g}" y="{ty}" text-anchor="middle" font-size="{12 if narrow else 13}" fill="{MUTED}">{esc(title)}</text>')


def live_badge(x, y, size):
    return (f'<circle cx="{x - 44}" cy="{y - 4}" r="3.5" fill="{GREEN}"><animate attributeName="opacity" '
            f'values="1;.25;1" dur="2.4s" repeatCount="indefinite"/></circle>'
            f'<text x="{x}" y="{y}" text-anchor="end" font-size="{size}" fill="{GREEN}">LIVE</text>')


def build_hero(cfg, narrow):
    rows = profile_rows(cfg)
    title = f'{cfg["handle"]} % ./profile.sh --live'
    handle_txt = f'github.com/{cfg["handle"]}'
    if not narrow:
        w, px, py, pw, ph = 1180, 39, 92, 440, 470
        cap_h = 52
        x0, x1 = 520, 1140
        size, step = 15, 26
        body = chrome(w, 650, title, False)
        body += f'<text x="{px}" y="82" font-size="11" fill="{DIM}">VISUAL.MAP</text>'
        body += f'<text x="{x0}" y="82" font-size="11" fill="{DIM}">SYSTEM.INFO</text>' + live_badge(x1, 82, 11)
        panel_h = ph + cap_h
        sc, ox, oy = 1.0, px, py
        pill_y, prompt_y, rows_y = 100, 172, 204
        h = 650
    else:
        w, px, py, pw = 560, 20, 74, 520
        cap_h = 50
        sc = 0.62
        sw, sh = GW * CELL * sc, GH * CELL * sc
        ph = 300
        panel_h = ph + cap_h
        ox, oy = px + (pw - sw) / 2, py + (ph - sh) / 2
        x0, x1 = 24, 536
        size, step = 14, 25
        body = ""  # the window chrome is added once the final height is known
        pill_y = py + panel_h + 52
        prompt_y, rows_y = pill_y + 56, pill_y + 86
        h = 0
    # visual panel ----------------------------------------------------------
    panel = (f'<rect x="{px}" y="{py}" width="{pw}" height="{panel_h}" rx="8" fill="{PANEL}" stroke="{GREEN}" '
             f'stroke-opacity=".55" stroke-width="1.3"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="{panel_h}" rx="8" fill="url(#scan)"/>'
             f'<clipPath id="pc"><rect x="{px}" y="{py}" width="{pw}" height="{panel_h}" rx="8"/></clipPath>'
             f'<g clip-path="url(#pc)">{scene_layers(ox, oy, sc)}'
             f'<rect x="{px}" y="{py + panel_h - cap_h}" width="{pw}" height="{cap_h}" fill="#02110c" fill-opacity=".92"/>'
             f'<line x1="{px}" y1="{py + panel_h - cap_h}" x2="{px + pw}" y2="{py + panel_h - cap_h}" stroke="{GREEN}" stroke-opacity=".25"/></g>'
             f'<text x="{px + 16}" y="{py + panel_h - cap_h + 19}" font-size="10" fill="{DIM}">TOOLCHAIN.SCAN</text>'
             + caption_layers(px + 16, py + panel_h - 13))
    # info column -----------------------------------------------------------
    pill_w = tw(handle_txt, 13) + 30
    info = (f'<rect x="{x0}" y="{pill_y}" width="{pill_w:.0f}" height="26" rx="6" fill="#052a1c" stroke="#0f6a45"/>'
            f'<text x="{x0 + 14}" y="{pill_y + 18}" font-size="13" fill="{MINT}">{esc(handle_txt)}</text>'
            f'<text x="{x0}" y="{prompt_y}" font-size="{size - 1}" fill="{DIM}">$ whoami --verbose</text>')
    rows_svg, y_end = render_rows(rows, x0, x1, rows_y, step, size)
    cur_y = y_end + 6
    cursor = (f'<rect x="{x0}" y="{cur_y}" width="8" height="15" fill="{GREEN}"><animate attributeName="opacity" '
              f'values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>')
    if narrow:
        h = int(cur_y + 15 + 28)
        head = chrome(w, h, title, True)
        head += f'<text x="{px}" y="{py - 8}" font-size="10" fill="{DIM}">VISUAL.MAP</text>'
        head += f'<text x="{x0}" y="{pill_y - 12}" font-size="10" fill="{DIM}">SYSTEM.INFO</text>' + live_badge(x1, pill_y - 12, 10)
        body = head
    aria = (f'{cfg["name"]}: B.Tech Computer Science Engineering student specializing in AI and Data Science. '
            f'Animated terminal card with pixel art and profile details.')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" role="img" aria-label="{esc(aria)}">'
            f'<title>{esc(aria)}</title>{hero_defs(w, h)}{body}{panel}{info}{rows_svg}{cursor}</svg>')


# --------------------------------------------------------------------------- #
# tagline
# --------------------------------------------------------------------------- #
def build_tagline(cfg):
    lines = [f'// B.Tech CSE, specializing in AI and Data Science',
             '// full-stack web, DSA, AI and machine learning',
             '// building ' + ", ".join(p["title"] for p in cfg["projects"][:-1]) + " and " + cfg["projects"][-1]["title"]]
    n = len(lines)
    t = ""
    for k, s in enumerate(lines):
        v, kt = anim_pts(window(k, n, 0.05))
        t += (f'<text x="410" y="26" text-anchor="middle" font-size="16" fill="{MINT}" opacity="{1 if k == 0 else 0}">{esc(s)}'
              f'<animate attributeName="opacity" values="{v}" keyTimes="{kt}" dur="12s" repeatCount="indefinite"/></text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="820" height="44" viewBox="0 0 820 44" font-family="{FONT}" '
            f'role="img" aria-label="{esc("; ".join(lines))}"><title>{esc("; ".join(lines))}</title>{t}</svg>')


# --------------------------------------------------------------------------- #
# tech stack
# --------------------------------------------------------------------------- #
TECH = [("HTML", "<>", "#E34F26"), ("CSS", "{}", "#2d9cdb"), ("JavaScript", "JS", "#F7DF1E"),
        ("React", "Re", "#61DAFB"), ("Tailwind CSS", "Tw", "#38BDF8"), ("Java", "Jv", "#ED8B00"),
        ("Python", "Py", "#FFD43B"), ("Django", "Dj", "#44B78B"), ("FastAPI", "FA", "#05C3A8"),
        ("PostgreSQL", "Pg", "#6f9fd8"), ("Git", "git", "#F05032"), ("GitHub", "GH", "#e6edf3")]


def build_tech():
    tile, gx, gy, per = 72, 26, 24, 6
    w = per * tile + (per - 1) * gx + 48
    rows = (len(TECH) + per - 1) // per
    h = rows * (tile + 34) + (rows - 1) * gy + 16
    out = ""
    for i, (name, mono, col) in enumerate(TECH):
        r, c = divmod(i, per)
        x = 24 + c * (tile + gx)
        y = 8 + r * (tile + 34 + gy)
        size = 24 if len(mono) < 3 else 20
        out += (f'<g><rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="14" fill="#06120f" stroke="{col}" '
                f'stroke-opacity=".55" stroke-width="1.4"/>'
                f'<rect x="{x + 1}" y="{y + 1}" width="{tile - 2}" height="{tile - 2}" rx="13" fill="{col}" fill-opacity=".07"/>'
                f'<text x="{x + tile / 2}" y="{y + tile / 2 + size * 0.35:.1f}" text-anchor="middle" font-size="{size}" '
                f'font-weight="700" fill="{col}">{esc(mono)}</text>'
                f'<text x="{x + tile / 2}" y="{y + tile + 20}" text-anchor="middle" font-size="11" fill="{MUTED}">{esc(name)}</text></g>')
    label = "Technologies: " + ", ".join(t[0] for t in TECH)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>{out}</svg>')


# --------------------------------------------------------------------------- #
# footer buttons
# --------------------------------------------------------------------------- #
ICONS = {
    "github": '<circle cx="8" cy="5.5" r="2.4"/><circle cx="8" cy="18.5" r="2.4"/><circle cx="17" cy="9" r="2.4"/><path d="M8 8v8M17 11.4c0 3.6-3.5 3.8-9 4.4"/>',
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10.5V16M8 7.6v.01M12 16v-5.5M12 12.8c0-1.6 1-2.4 2.3-2.4 1.5 0 2.2 1 2.2 2.6V16"/>',
    "email": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 7l8.5 6.5L20.5 7"/>',
    "portfolio": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
}


def build_button(kind, label):
    w = int(52 + tw(label, 13) + (len(label) - 1) * 1.5)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="40" viewBox="0 0 {w} 40" font-family="{FONT}" '
            f'role="img" aria-label="{label}"><title>{label}</title>'
            f'<g transform="translate(4 8) scale(.9)" fill="none" stroke="{TEAL}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[kind]}</g>'
            f'<text x="36" y="25" font-size="13" font-weight="700" letter-spacing="1.5" fill="{TEAL}">{label}</text>'
            f'<line x1="36" y1="31" x2="{w - 2}" y2="31" stroke="{TEAL}" stroke-opacity=".55" stroke-width="1.5"/></svg>')


def main():
    cfg = load_config()
    write(os.path.join(A, "hero.svg"), build_hero(cfg, narrow=False))
    write(os.path.join(A, "hero-narrow.svg"), build_hero(cfg, narrow=True))
    write(os.path.join(A, "tagline.svg"), build_tagline(cfg))
    write(os.path.join(A, "tech-stack.svg"), build_tech())
    for kind, label in (("github", "GITHUB"), ("linkedin", "LINKEDIN"), ("email", "EMAIL"), ("portfolio", "PORTFOLIO")):
        write(os.path.join(A, f"btn-{kind}.svg"), build_button(kind, label))


if __name__ == "__main__":
    main()
