#!/usr/bin/env python3
"""Builds the assets that only change when config/profile.json changes (stdlib only):

  assets/hero-terminal.svg / -narrow.svg   terminal card shown beside the profile photo
  assets/tech-stack.svg / -narrow.svg      genuine brand icons, grouped, consistent tiles
  assets/sec-*.svg                         terminal-style section dividers
  assets/btn-*.svg                         footer buttons (GitHub + any link set in the config)

The profile photo is NOT part of any SVG. README.md shows it as a plain <img> pointing at
https://github.com/<handle>.png, which is the most reliable way to get a real photo onto GitHub
(no download step, no external image inside an SVG, updates itself when you change your avatar).

GitHub caches README images by URL. If you change a static asset's look, rename the file and the
README reference together (for example hero-terminal-v2.svg).
"""
import os
import random

from lib import (DIM, FRAME, FRAME2, GREEN, MINT, MUTED, ROOT, SANS, TEAL, TEXT, YEL, anim_pts, esc, load_config, tw, write)
from ui import chrome, icon_el, section, svg

A = os.path.join(ROOT, "assets")


# --------------------------------------------------------------------------- #
# hero terminal
# --------------------------------------------------------------------------- #
def host(u):
    return u.replace("https://", "").replace("http://", "").replace("mailto:", "").rstrip("/")


def rows_wide(cfg):
    L = cfg["links"]
    live = next((p["live"] for p in cfg["projects"] if p.get("live")), None)
    rows = [("Education", cfg["degree"], TEXT)]
    for g in cfg["tech_groups"]:
        rows.append((g["name"].split()[0].capitalize() if g["name"] != "backend + data" else "Backend", ", ".join(n for _, n in g["items"]), MINT))
    rows += [("Interests", ", ".join(cfg["interests"]), TEXT), ("Projects", ", ".join(p["title"] for p in cfg["projects"]), GREEN)]
    if live:
        rows.append(("Live", host(live), TEAL))
    for key, lab in (("github", "GitHub"), ("linkedin", "LinkedIn"), ("email", "Email"), ("portfolio", "Portfolio")):
        if L.get(key):
            rows.append((lab, host(L[key]), TEAL))
    return rows


def rows_narrow(cfg):
    L = cfg["links"]
    first = [p["title"] for p in cfg["projects"][:2]]
    more = len(cfg["projects"]) - 2
    rows = [("Education", cfg["degree"].replace("Data Science", "DS") if len(cfg["degree"]) > 28 else cfg["degree"], TEXT),
            ("Stack", "React, Python, Java, Django, FastAPI", MINT),
            ("Interests", "Full-stack, DSA, AI/ML", TEXT),
            ("Projects", ", ".join(first) + (f" +{more}" if more > 0 else ""), GREEN)]
    if L.get("github"):
        rows.append(("GitHub", host(L["github"]), TEAL))
    return rows


def kv(rows, x0, x1, y, step, size):
    out = ""
    for i, (k, v, col) in enumerate(rows):
        lx0, lx1 = x0 + tw(k, size) + 10, x1 - tw(v, size) - 10
        d, dur = i * .09, 2.4
        a, b = d / dur, (d + .4) / dur
        g = (f'<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{a:.4f};{b:.4f};1" dur="{dur}s" begin="0s" fill="freeze"/>'
             f'<text x="{x0}" y="{y}" font-size="{size}" fill="#4fd1a5">{esc(k)}</text>')
        if lx1 > lx0 + 14:
            g += (f'<line x1="{lx0:.0f}" y1="{y - 4}" x2="{lx1:.0f}" y2="{y - 4}" stroke="{DIM}" stroke-width="1.4" '
                  f'stroke-dasharray="1 5" stroke-linecap="round"/>')
        g += f'<text x="{x1}" y="{y}" text-anchor="end" font-size="{size}" fill="{col}">{esc(v)}</text></g>'
        out += g
        y += step
    return out, y


def code_rain(x, y, w, h):
    rnd = random.Random(7)
    cols, per, lh = int(w // 24), 3, 22
    out = ""
    for c in range(cols):
        pat = [rnd.choice("01") + " " + rnd.choice("01") for _ in range(per)]
        lines = "".join(f'<tspan x="{x + c * 24}" dy="{lh if i else 0}">{pat[i % per]}</tspan>' for i in range(int(h // lh) + per + 1))
        out += (f'<text x="{x + c * 24}" y="{y}" font-size="11" fill="{GREEN}" opacity="{rnd.choice([.07, .1, .14])}">{lines}'
                f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -{lh * per}" dur="{9 + c % 3}s" repeatCount="indefinite"/></text>')
    return (f'<mask id="rm"><rect x="{x}" y="{y - 14}" width="{w}" height="{h}" fill="url(#rf)"/></mask><g mask="url(#rm)">{out}</g>')


def build_terminal(cfg, narrow):
    W, H = (420, 330) if narrow else (1000, 438)
    handle = cfg["handle"]
    ch, bar = chrome(W, H, f"{handle} % ./profile.sh --live", narrow=narrow)
    defs = (f'<linearGradient id="rf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".3" stop-color="#fff"/>'
            f'<stop offset=".7" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="sc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset=".5" stop-color="{GREEN}" stop-opacity=".25"/>'
            f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>')
    if narrow:
        x0, x1, size, step = 22, W - 22, 13.5, 27
        body = (f'<text x="{x0}" y="{bar + 30}" font-size="12" fill="{DIM}">$ whoami</text>'
                f'<text x="{x0}" y="{bar + 64}" font-size="25" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(cfg["name"])}</text>'
                f'<text x="{x0}" y="{bar + 87}" font-size="13" font-family="{SANS}" fill="{MINT}">{esc(cfg["role"])}</text>')
        rows, ry = rows_narrow(cfg), bar + 124
    else:
        x0, x1, size, step = 34, W - 34, 15, 26
        body = (code_rain(640, bar + 30, 320, 96) +
                f'<text x="{x0}" y="{bar + 36}" font-size="13" fill="{DIM}">$ whoami</text>'
                f'<text x="{x0}" y="{bar + 80}" font-size="34" font-weight="700" font-family="{SANS}" fill="{TEXT}">{esc(cfg["name"])}</text>'
                f'<text x="{x0}" y="{bar + 108}" font-size="17" font-family="{SANS}" fill="{MINT}">{esc(cfg["role"])}</text>')
        rows, ry = rows_wide(cfg), bar + 150
    kvs, y_end = kv(rows, x0, x1, ry, step, size)
    cursor = (f'<text x="{x0}" y="{y_end + 14}" font-size="{size}" fill="{GREEN}">$</text>'
              f'<rect x="{x0 + 16}" y="{y_end + 2}" width="8" height="15" fill="{GREEN}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>')
    scan = (f'<rect x="1" y="{bar}" width="{W - 2}" height="2" fill="url(#sc)" opacity=".0"><animate attributeName="y" values="{bar};{H - 2}" dur="7s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.9;.9;0" keyTimes="0;.1;.9;1" dur="7s" repeatCount="indefinite"/></rect>')
    aria = f'{cfg["name"]}, {cfg["role"]}. {cfg["degree"]}.'
    return svg(W, H, aria, ch + body + kvs + cursor + scan, defs)


# --------------------------------------------------------------------------- #
# tech stack
# --------------------------------------------------------------------------- #
def build_tech(cfg, narrow):
    used = {t for p in cfg["projects"] for t in p.get("tech", [])}
    learning = set(cfg.get("learning", []))
    groups = cfg["tech_groups"]
    tile, gap, pad = (56, 14, 22) if narrow else (62, 18, 24)
    panels, x, y = [], 0, 0
    out = ""
    if narrow:
        W = 422
        pw = W - 2
        for g in groups:
            n = len(g["items"])
            per = min(n, 5)
            rows = -(-n // per)
            ph = 52 + rows * (tile + 34) + 6
            panels.append((1, y, pw, ph, g))
            y += ph + 14
        H = y - 14 + 30
    else:
        ws = []
        for g in groups:
            n = len(g["items"])
            ws.append(2 * pad + n * tile + (n - 1) * gap)
        W = int(sum(ws) + 16 * (len(groups) - 1)) + 2
        ph = 52 + tile + 34 + 6
        x = 1
        for g, w in zip(groups, ws):
            panels.append((x, 1, w, ph, g))
            x += w + 16
        H = ph + 32
    for px, py, pw_, ph_, g in panels:
        out += (f'<rect x="{px}" y="{py}" width="{pw_}" height="{ph_}" rx="12" fill="#040d0b" stroke="{FRAME2}" stroke-width="1.2"/>'
                f'<text x="{px + pad}" y="{py + 32}" font-size="13" fill="{TEAL}">{esc(g["name"])}/</text>')
        n = len(g["items"])
        per = min(n, 5) if narrow else n
        for i, (key, label) in enumerate(g["items"]):
            r, c = divmod(i, per)
            tx = px + pad + c * (tile + gap) + (0 if narrow else 0)
            ty = py + 46 + r * (tile + 34)
            out += (f'<rect x="{tx}" y="{ty}" width="{tile}" height="{tile}" rx="14" fill="#05120e" stroke="{FRAME}" stroke-width="1.2"/>'
                    f'<rect x="{tx + 1}" y="{ty + 1}" width="{tile - 2}" height="{tile - 2}" rx="13" fill="{GREEN}" fill-opacity=".035"/>'
                    + icon_el(key, tx + tile * .22, ty + tile * .22, tile * .56, MINT, .95)
                    + f'<text x="{tx + tile / 2}" y="{ty + tile + 18}" text-anchor="middle" font-size="{10.5 if narrow else 11}" font-family="{SANS}" fill="{MUTED}">{esc(label)}</text>')
            if key in learning:
                out += f'<circle cx="{tx + tile - 8}" cy="{ty + 8}" r="3.6" fill="none" stroke="{YEL}" stroke-width="1.4"/>'
            elif key in used:
                out += f'<circle cx="{tx + tile - 8}" cy="{ty + 8}" r="3.6" fill="{GREEN}"/>'
    leg = f'<circle cx="{W - 190 if not narrow else 12}" cy="{H - 10}" r="3.6" fill="{GREEN}"/>' \
          f'<text x="{W - 180 if not narrow else 22}" y="{H - 6}" font-size="10.5" font-family="{SANS}" fill="{MUTED}">used in a featured project</text>'
    if learning:
        leg += (f'<circle cx="{W - 14 if not narrow else 190}" cy="{H - 10}" r="3.6" fill="none" stroke="{YEL}" stroke-width="1.4"/>'
                f'<text x="{W - 6 if not narrow else 200}" y="{H - 6}" {"text-anchor=\"end\" " if not narrow else ""}font-size="10.5" font-family="{SANS}" fill="{MUTED}">learning</text>')
    label = "Technologies: " + "; ".join(f'{g["name"]}: ' + ", ".join(n for _, n in g["items"]) for g in groups)
    return svg(W, H, label, out + leg)


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
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="40" viewBox="0 0 {w} 40" font-family="ui-monospace,Menlo,Consolas,monospace" '
            f'role="img" aria-label="{label}"><title>{label}</title>'
            f'<g transform="translate(4 8) scale(.9)" fill="none" stroke="{TEAL}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[kind]}</g>'
            f'<text x="36" y="25" font-size="13" font-weight="700" letter-spacing="1.5" fill="{TEAL}">{label}</text>'
            f'<line x1="36" y1="31" x2="{w - 2}" y2="31" stroke="{TEAL}" stroke-opacity=".55" stroke-width="1.5"/></svg>')


def main():
    cfg = load_config()
    write(os.path.join(A, "hero-terminal.svg"), build_terminal(cfg, False))
    write(os.path.join(A, "hero-terminal-narrow.svg"), build_terminal(cfg, True))
    write(os.path.join(A, "tech-stack.svg"), build_tech(cfg, False))
    write(os.path.join(A, "tech-stack-narrow.svg"), build_tech(cfg, True))
    n_tech = sum(len(g["items"]) for g in cfg["tech_groups"])
    for name, args in (("projects", ("~/projects", "featured", f'{len(cfg["projects"])} projects')),
                       ("toolchain", ("~/toolchain", "stack", f"{n_tech} technologies")), ("contact", ("~/contact", "", ""))):
        write(os.path.join(A, f"sec-{name}.svg"), section(*args))
        write(os.path.join(A, f"sec-{name}-narrow.svg"), section(*args, w=420))
    for kind, label in (("github", "GITHUB"), ("linkedin", "LINKEDIN"), ("email", "EMAIL"), ("portfolio", "PORTFOLIO")):
        if cfg["links"].get(kind):
            write(os.path.join(A, f"btn-{kind}.svg"), build_button(kind, label))


if __name__ == "__main__":
    main()
