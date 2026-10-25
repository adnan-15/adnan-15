"""Design system shared by every generated SVG: one chrome, one palette, one set of dividers."""
import os
import re

from lib import (BG0, DIM, FONT, FRAME, FRAME2, GREEN, GRN_D, MINT, MUTED, ROOT, SANS, TEAL, TEXT,
                 YEL_D, RED_D, esc, tw)

ICON_DIR = os.path.join(ROOT, "assets", "icons")

DEFS = f'''<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset=".55" stop-color="#060e12"/><stop offset="1" stop-color="#04090c"/></linearGradient>
<radialGradient id="glowR" cx=".85" cy=".1" r=".7"><stop offset="0" stop-color="{GREEN}" stop-opacity=".09"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowB" cx=".1" cy="1" r=".6"><stop offset="0" stop-color="{TEAL}" stop-opacity=".06"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{GREEN}" stroke-opacity=".03"/></pattern>'''


def svg(w, h, aria, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" role="img" aria-label="{esc(aria)}"><title>{esc(aria)}</title>'
            f'<defs>{DEFS}{defs}</defs>{body}</svg>')


def chrome(w, h, title, status="LIVE", radius=14, narrow=False):
    """Terminal window: gradient body, faint grid, hairline border, three dots, centred title, status."""
    bar = 40 if narrow else 44
    cy = bar / 2
    fs = 11.5 if narrow else 13
    out = (f'<rect width="{w}" height="{h}" rx="{radius}" fill="url(#bg)"/>'
           f'<rect width="{w}" height="{h}" rx="{radius}" fill="url(#grid)"/>'
           f'<rect width="{w}" height="{h}" rx="{radius}" fill="url(#glowR)"/>'
           f'<rect width="{w}" height="{h}" rx="{radius}" fill="url(#glowB)"/>'
           f'<line x1="0" y1="{bar}" x2="{w}" y2="{bar}" stroke="{FRAME}" stroke-opacity=".7"/>'
           f'<circle cx="24" cy="{cy}" r="5.5" fill="{RED_D}"/><circle cx="43" cy="{cy}" r="5.5" fill="{YEL_D}"/>'
           f'<circle cx="62" cy="{cy}" r="5.5" fill="{GRN_D}"/>'
           f'<text x="{w / 2:g}" y="{cy + fs * .35:.1f}" text-anchor="middle" font-size="{fs}" fill="{MUTED}">{esc(title)}</text>')
    if status:
        out += (f'<circle cx="{w - 24 - tw(status, fs - 1.5) - 11:.0f}" cy="{cy}" r="3.4" fill="{GREEN}"><animate attributeName="opacity" values="1;.3;1" '
                f'dur="2.6s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".4 0 .6 1;.4 0 .6 1"/></circle>'
                f'<text x="{w - 24}" y="{cy + 4}" text-anchor="end" font-size="{fs - 1.5}" fill="{GREEN}">{esc(status)}</text>')
    out += f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{radius}" fill="none" stroke="{FRAME}" stroke-width="1.5"/>'
    return out, bar


def section(left, tag="", right="", w=1180):
    """Terminal-style section divider: `~/projects  featured ------------------ 4 projects`."""
    h = 44
    x = 6
    lw = tw(left, 16)
    t = f'<text x="{x}" y="28" font-size="16" font-weight="700" fill="{GREEN}">{esc(left)}</text>'
    xe = x + lw
    if tag:
        t += f'<text x="{xe + 14:.0f}" y="28" font-size="13" fill="{TEAL}">{esc(tag)}</text>'
        xe += 14 + tw(tag, 13)
    rw = tw(right, 12) + 6 if right else 0
    t += (f'<line x1="{xe + 16:.0f}" y1="23" x2="{w - rw - 14:.0f}" y2="23" stroke="url(#dl)" stroke-width="1.2"/>')
    if right:
        t += f'<text x="{w - 6}" y="27" text-anchor="end" font-size="12" fill="{MUTED}">{esc(right)}</text>'
    defs = (f'<linearGradient id="dl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{GREEN}" stop-opacity=".04"/></linearGradient>')
    return svg(w, h, f"{left} {tag} {right}".strip(), t, defs)


# technology icons -------------------------------------------------------------
_icon_cache = {}


def icon(key):
    """(viewBox, path d) of a genuine brand glyph from assets/icons/<key>.svg."""
    if key not in _icon_cache:
        t = open(os.path.join(ICON_DIR, f"{key}.svg"), encoding="utf-8").read()
        vb = re.search(r'viewBox="([^"]+)"', t).group(1)
        d = re.search(r'<path[^>]* d="([^"]+)"', t).group(1)
        _icon_cache[key] = (vb, d)
    return _icon_cache[key]


def icon_el(key, x, y, size, fill=MINT, opacity=.95):
    vb, d = icon(key)
    return (f'<svg x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet">'
            f'<path fill="{fill}" fill-opacity="{opacity}" d="{d}"/></svg>')


__all__ = ["svg", "chrome", "section", "icon_el", "SANS", "TEXT", "DIM", "FRAME2"]
