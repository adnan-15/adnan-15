"""Collects every number the profile shows, from real GitHub data only.

Sources, in order of preference, per metric:

  contribution calendar   GraphQL (needs a token)  ->  public contributions page (no token)
  commits, last 12 months GraphQL                  ->  commit search API
  repositories            REST /users/{u}/repos
  profile facts           REST /users/{u}

Every failure is recorded with its exact cause (bad token, rate limit, parse error...) via
lib.note(), becomes a workflow annotation, and leaves that metric as None. Nothing is
estimated, and no placeholder is ever substituted for a failed request.
"""
import re
from datetime import date, datetime, timedelta

from lib import FetchError, graphql, html, norm, note, rest

GQL = """query($login:String!){user(login:$login){
  contributionsCollection{totalCommitContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""


# --------------------------------------------------------------------------- #
# contribution calendar
# --------------------------------------------------------------------------- #
def calendar_graphql(user):
    u = graphql(GQL, {"login": user})["user"]
    if u is None:
        raise FetchError(f"GraphQL: user '{user}' not found (check config handle)")
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = {}
    for w in cal["weeks"]:
        for x in w["contributionDays"]:
            days[x["date"]] = x["contributionCount"]
    return {"days": days, "total": cal["totalContributions"], "commits": cc["totalCommitContributions"],
            "source": "graphql"}


def parse_contributions_html(text):
    """Parse github.com/users/<u>/contributions. Order-independent: cells and tooltips are joined by id."""
    cells = {}
    for m in re.finditer(r"<td\b([^>]*ContributionCalendar-day[^>]*)>", text):
        a = m.group(1)
        d, i = re.search(r'data-date="([\d-]+)"', a), re.search(r'\bid="([^"]+)"', a)
        if d and i:
            cells[i.group(1)] = d.group(1)
    if not cells:
        raise FetchError("contributions page: no calendar cells found (markup changed?)")
    counts = {}
    for m in re.finditer(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>\s*([^<]*?)\s*</tool-tip>', text):
        cid, label = m.group(1), m.group(2)
        if cid not in cells:
            continue
        n = re.match(r"([\d,]+)\s+contribution", label)
        counts[cells[cid]] = int(n.group(1).replace(",", "")) if n else (0 if label.lower().startswith("no contributions") else None)
    days = {d: counts.get(d) for d in cells.values()}
    if any(v is None for v in days.values()):
        raise FetchError("contributions page: could not read every day's count (markup changed?)")
    total = sum(days.values())
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", text)
    if m and int(m.group(1).replace(",", "")) != total:
        raise FetchError(f"contributions page: day counts add up to {total} but the page says {m.group(1)}")
    return days, total


def calendar_scrape(user):
    days, total = parse_contributions_html(html(f"https://github.com/users/{user}/contributions"))
    return {"days": days, "total": total, "commits": None, "source": "contributions page"}


def to_weeks(days):
    """{iso date: count} -> list of 7-slots columns (Sunday first), None where the date does not exist."""
    ds = sorted(days)
    first = date.fromisoformat(ds[0])
    lead = (first.weekday() + 1) % 7  # Monday=0 -> Sunday-first index
    weeks, col = [], [None] * lead
    for d in ds:
        col.append(days[d])
        if len(col) == 7:
            weeks.append(col)
            col = []
    if col:
        weeks.append(col + [None] * (7 - len(col)))
    return weeks


def streaks(days):
    ds = sorted(days)
    best = run = 0
    for d in ds:
        run = run + 1 if days[d] > 0 else 0
        best = max(best, run)
    cur = 0
    for d in reversed(ds):
        if days[d] > 0:
            cur += 1
        elif cur or d != ds[-1]:
            break
    return best, cur


# --------------------------------------------------------------------------- #
# repositories
# --------------------------------------------------------------------------- #
def list_repos(user):
    out, page = [], 1
    while True:
        batch = rest(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&sort=pushed&page={page}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def resolve_projects(cfg, repos):
    """Match each configured project to a real public repository. Never guesses between candidates."""
    res, taken = {}, set()
    for p in cfg["projects"]:
        pick, why = None, ""
        if p.get("repo"):
            hit = [r for r in repos if r["name"].lower() == p["repo"].lower()]
            if hit:
                pick, why = hit[0], "configured repo"
            else:
                note("warning", f'{p["title"]}: configured repo "{p["repo"]}" is not among {cfg["handle"]}\'s public repos')
        else:
            live = (p.get("live") or "").rstrip("/").lower()
            cands = []
            if live:
                cands = [r for r in repos if (r.get("homepage") or "").rstrip("/").lower() == live]
                why = "homepage matches live URL"
            if not cands:
                keys = [norm(k) for k in p.get("match", []) + [p["title"]] if len(norm(k)) >= 5]
                cands = [r for r in repos if r["name"] not in taken and any(k in norm(r["name"]) or (len(norm(r["name"])) >= 5 and norm(r["name"]) in k) for k in keys)]
                why = "repo name matches title"
            exact = [r for r in cands if norm(r["name"]) == norm(p["title"])]
            cands = exact or cands
            if len(cands) == 1:
                pick = cands[0]
            elif len(cands) > 1:
                note("warning", f'{p["title"]}: several repos match ({", ".join(r["name"] for r in cands)}); '
                                f'set "repo" in config/profile.json')
            else:
                names = ", ".join(r["name"] for r in repos[:12]) or "none"
                note("warning", f'{p["title"]}: no public repo found. Public repos: {names}. '
                                f'Set "repo" in config/profile.json if it is named differently or private.')
        if pick:
            taken.add(pick["name"])
            res[p["slug"]] = {"name": pick["name"], "url": pick["html_url"], "homepage": pick.get("homepage"),
                              "langs_url": pick["languages_url"], "why": why}
    return res


def repo_languages(url):
    got = rest(url)
    s = sum(got.values())
    return [(k, 100 * b / s) for k, b in sorted(got.items(), key=lambda kv: -kv[1])] if s else []


# --------------------------------------------------------------------------- #
def collect(cfg):
    user = cfg["handle"]
    d = {"user": None, "cal": None, "weeks": None, "commits": None, "repos": None, "langs": None,
         "resolved": {}, "repo_langs": {}, "streak": None, "ok_any": False}
    # profile facts
    try:
        u = rest(f"https://api.github.com/users/{user}")
        d["user"] = {"public_repos": u.get("public_repos"), "followers": u.get("followers"),
                     "since": (u.get("created_at") or "")[:4] or None}
        d["ok_any"] = True
    except FetchError as e:
        note("warning", f"profile facts unavailable: {e}")
    # contribution calendar: token-based first, then the public page
    for fn in (calendar_graphql, calendar_scrape):
        try:
            d["cal"] = fn(user)
            d["ok_any"] = True
            note("info", f'contribution calendar from {d["cal"]["source"]}: {d["cal"]["total"]} contributions')
            break
        except FetchError as e:
            note("warning", f"contribution calendar via {fn.__name__} failed: {e}")
    if d["cal"]:
        d["weeks"] = to_weeks(d["cal"]["days"])
        d["streak"] = streaks(d["cal"]["days"])
        d["commits"] = d["cal"]["commits"]
    if d["commits"] is None and d["cal"]:
        since = (date.fromisoformat(max(d["cal"]["days"])) - timedelta(days=364)).isoformat()
        try:
            r = rest(f"https://api.github.com/search/commits?q=author:{user}+author-date:%3E%3D{since}&per_page=1")
            d["commits"] = r["total_count"]
            note("info", "commit count from commit search (default-branch commits in public repos)")
        except (FetchError, KeyError) as e:
            note("warning", f"commit count unavailable: {e}")
    # repositories, languages, project resolution
    try:
        repos = list_repos(user)
        d["repos"] = repos
        d["ok_any"] = True
        own = [r for r in repos if not r.get("fork")]
        totals = {}
        for r in own[:60]:
            try:
                got = rest(r["languages_url"])
            except FetchError as e:
                note("warning", f'languages for {r["name"]} unavailable: {e}')
                continue
            for k, b in got.items():
                totals[k] = totals.get(k, 0) + b
        s = sum(totals.values())
        d["langs"] = [(k, 100 * b / s) for k, b in sorted(totals.items(), key=lambda kv: -kv[1])] if s else []
        d["resolved"] = resolve_projects(cfg, own)
        for slug, info in d["resolved"].items():
            try:
                d["repo_langs"][slug] = repo_languages(info["langs_url"])
            except FetchError as e:
                note("warning", f"{slug} languages unavailable: {e}")
        note("info", "resolved projects: " + (", ".join(f'{k}->{v["name"]}' for k, v in d["resolved"].items()) or "none"))
    except FetchError as e:
        note("warning", f"repository list unavailable: {e}")
    return d


def stars_total(repos):
    return sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork")) if repos is not None else None
