# Setup, secrets and troubleshooting

`README.md` is **generated** from `config/profile.json` + `config/readme.template.md` by `.github/scripts/make_readme.py`. Edit those, not the README.

## 1. Publish

1. Create a **public** repo named exactly `adnan-15`. Push everything in this folder to `main`.
2. **Settings > Actions > General > Workflow permissions**: *Read and write permissions*.
3. The first push starts **Refresh profile assets** by itself (it watches `config/`, `.github/scripts/`, the workflow and `assets/icons/`). You can also run it from the **Actions** tab.
4. Open the finished run: the **summary** lists every data source used and every warning, and the log shows the same as annotations.

Until that first run succeeds the page shows a compact "pending" stats panel (only facts from the config: 4 projects, 12 technologies, your degree), a compact contribution placeholder, and unlinked project rings. After it, everything is real GitHub data and repo links are filled in.

## 2. What gets verified automatically

| Item | Source | If it fails |
| --- | --- | --- |
| Contribution grid, total, active days, streaks | GraphQL (token) then the public contributions page | grid replaced by a compact placeholder, warning annotation |
| Commits, last 12 months | GraphQL, else commit search API | tile omitted |
| Public repos, followers, stars, "since" | REST | tile/row omitted (zero stars/followers are never headlined) |
| Language bar | languages of your public non-fork repos | panel omitted |
| **Project repo links + language rings** | each project is matched to a public repo by (1) `repo` in the config, (2) a repo whose *homepage* equals the live URL, (3) a repo name that contains the project keywords | card stays unlinked and a warning lists your repo names; the profile URL is never used as a stand-in |

If **no** data at all can be fetched the job **fails (red)** and leaves existing files untouched. Partial data produces a smaller but complete-looking dashboard plus warnings.

To pin a project to a repo explicitly, set `"repo": "exact-repo-name"` in `config/profile.json`. Private repositories cannot be linked or analysed.

## 3. Secrets and permissions

* **Nothing is required** for public data: the built-in `GITHUB_TOKEN` is used.
* **Private contributions (optional):** create a classic token with scope `read:user`, add it as repository secret **`STATS_TOKEN`**, and turn on *Profile > Settings > Contributions > Private contributions*. Never put the token in any file.
* If the run log says `HTTP 401 ... token rejected`, the `STATS_TOKEN` secret is invalid or expired: delete or renew it. `HTTP 403 ... rate limit` means retry later.

## 4. Your photo

The hero uses `https://github.com/adnan-15.png?size=460` as an ordinary `<img>`. It is always your current GitHub avatar, needs no download step, and cannot be broken by SVG security rules. Change your avatar on GitHub and the README follows. GitHub strips CSS from READMEs, so a border or glow around a bare `<img>` is not possible; the terminal card beside it carries the visual frame.

## 5. Customising

| Want to... | Edit |
| --- | --- |
| add LinkedIn / email / portfolio | `links` in `config/profile.json`, then run the workflow (a button and a hero row appear) |
| mark technologies you are still learning | add their keys (e.g. `"java"`) to `learning`; they get a hollow marker instead of the "used in a project" dot |
| change projects, tags, blurbs | `projects` in `config/profile.json` |
| reorder or add sections | `config/readme.template.md` |

Local runs (Python 3.8+, standard library only):

```bash
python .github/scripts/make_static.py
python .github/scripts/make_stats.py            # needs network; export GITHUB_TOKEN for a higher rate limit
python .github/scripts/make_readme.py
python .github/scripts/make_stats.py --demo     # SYNTHETIC data into ./preview/ for layout checks only
```

## 6. Notes

* The bot commit touches only `assets/` and `README.md`, uses `GITHUB_TOKEN` and `[skip ci]`, and those paths are not workflow triggers, so it cannot loop.
* GitHub caches README images. Generated panels refresh within minutes to hours; if you restyle a *static* file, rename it and the reference together.
* Scheduled workflows pause after 60 days without repository activity; re-enable from the Actions tab.
* Phones get portrait/compact variants through `<picture media="(max-width: 700px)">`. If GitHub ignores the media query, phones simply receive the desktop variants.
* Icons: Simple Icons (CC0) and one Font Awesome Free brand icon (CC BY 4.0); see `assets/icons/NOTICE.md`.
