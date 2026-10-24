"""Shared palette, SVG helpers, a tiny pixel canvas and GitHub API access.

Standard library only, so the workflow needs no `pip install`.
"""
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# palette -------------------------------------------------------------------
BG0, PANEL = "#04070a", "#030a08"
FRAME, FRAME2 = "#0e3d2c", "#0f3a2c"
GREEN, TEAL, MINT = "#00FF9C", "#22D3EE", "#9BE7C4"
DIM, MUTED, TEXT = "#31514c", "#5b7d73", "#e6fff5"
YEL, VIOLET = "#F5C542", "#a78bfa"
RED_D, YEL_D, GRN_D = "#ff5f56", "#ffbd2e", "#27c93f"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def load_config():
    with open(os.path.join(ROOT, "config", "profile.json"), encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def tw(s, size):
    """Approximate width of monospace text (0.6 em per character)."""
    return len(s) * size * 0.6


def wrap(text, n):
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


def write(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print(f"wrote {os.path.relpath(path, ROOT)}  ({len(svg) / 1024:.1f} KB)")


def anim_pts(points):
    """[(t, v), ...] -> (values, keyTimes) strings for a SMIL <animate>."""
    pts_ = sorted(points)
    vals = ";".join(f"{v:g}" for _, v in pts_)
    keys = ";".join(f"{t:.4f}".rstrip("0").rstrip(".") or "0" for t, _ in pts_)
    return vals, keys


def window(k, n, fade=0.03):
    """Opacity keyframes for item k of n that is visible during its slot."""
    s, e = k / n, (k + 1) / n
    p = [(0, 0), (s, 0), (min(s + fade, e), 1), (max(e - fade, s), 1), (e, 0), (1, 0)]
    out = {}
    for t, v in p:
        out[round(t, 5)] = v
    return sorted(out.items())


# pixel canvas --------------------------------------------------------------
class Px:
    def __init__(self, w, h):
        self.w, self.h, self.c = w, h, {}

    def set(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.c[(x, y)] = col

    def rect(self, x, y, w, h, col):
        for j in range(h):
            for i in range(w):
                self.set(x + i, y + j, col)

    def line(self, x0, y0, x1, y1, col, t=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.rect(x0 - t // 2, y0 - t // 2, t, t, col)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, col):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * 0.6:
                    self.set(x, y, col)

    def ring(self, cx, cy, r, col, t=1):
        for y in range(cy - r - 1, cy + r + 2):
            for x in range(cx - r - 1, cx + r + 2):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if r - t / 2 <= d <= r + t / 2 + 0.2:
                    self.set(x, y, col)

    def art(self, x, y, rows, pal):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in pal:
                    self.set(x + i, y + j, pal[ch])

    def paths(self, s=10):
        """One <path> per colour, horizontal runs merged."""
        by = {}
        for (x, y), col in sorted(self.c.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            by.setdefault(col, []).append((x, y))
        out = []
        for col, cells in by.items():
            runs, run = [], None
            for x, y in cells:
                if run and run[1] == y and run[2] == x:
                    run[2] = x + 1
                else:
                    if run:
                        runs.append(run)
                    run = [x, y, x + 1]
            if run:
                runs.append(run)
            dd = "".join(f"M{a * s} {y * s}h{(b - a) * s}v{s}h{-(b - a) * s}z" for a, y, b in runs)
            out.append(f'<path fill="{col}" d="{dd}"/>')
        return "".join(out)


# GitHub API ------------------------------------------------------------------
def _headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "adnan-15-profile"}
    tok = os.environ.get("GITHUB_TOKEN", "")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def rest(url):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={**_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(out["errors"][0].get("message", "graphql error"))
    return out["data"]
