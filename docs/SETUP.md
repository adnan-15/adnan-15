# Setup

## 1. Publish

1. On GitHub create a **public** repository named exactly `adnan-15` (same as your username). GitHub only shows a profile README from a repo with that name.
2. Push everything in this folder to its `main` branch (keep `.github/`, `assets/`, `config/`, `docs/`, `README.md`).
3. Open the **Actions** tab and, if asked, enable workflows.
4. Repository **Settings > Actions > General > Workflow permissions**: choose **Read and write permissions**. (The workflow also declares `contents: write`, but an organisation or account default can override it.)
5. Run **Actions > Refresh profile assets > Run workflow** once. It rewrites `assets/generated/*` with your real numbers and commits them. After that it runs daily at 00:30 UTC and whenever you change `config/` or `.github/scripts/`.

Until step 5 finishes, the stats panel, runner and card rings show `n/a`. That is deliberate: nothing is estimated.

## 2. Fill in what is missing (`config/profile.json`)

| Field | Effect |
| --- | --- |
| `links.linkedin`, `links.email`, `links.portfolio` | Adds a `Grid.*` row to the hero. Also uncomment the matching button in `README.md`. |
| `projects[].repo` (repo name only, e.g. `"skymart"`) | The card ring switches from "tech count" to the real language split of that repo. |
| `projects[].url` / `label` | Live URL shown on the card. Also update the card's `href` in `README.md`. |

Then regenerate locally or just push (the workflow reruns on config changes):

```bash
python .github/scripts/make_static.py   # hero, tagline, tech stack, buttons
python .github/scripts/make_stats.py    # needs network; GITHUB_TOKEN optional
python .github/scripts/make_stats.py --demo   # SYNTHETIC data into ./preview/ for layout checks only
```

Python 3.8+, standard library only. No `pip install`.

## 3. Optional

* **Private contributions**: create a classic token with `read:user`, store it as repository secret `STATS_TOKEN`. Also enable *Settings (profile) > Contributions > Private contributions*. Without it only public activity is counted.
* **Cache**: GitHub caches README images. If you change a *static* asset (`hero.svg`, `tech-stack.svg`, ...), rename it (for example `hero-v2.svg`) and update `README.md`; otherwise visitors may keep the old version. Generated panels refresh on their own within minutes to hours.
* **Scheduled runs pause** on repos with no activity for 60 days. Re-enable the workflow in the Actions tab if that happens.

## How the workflow avoids loops

* It commits only `assets/`, which is not in the `push.paths` filter.
* It commits with the built-in `GITHUB_TOKEN`, and pushes made with that token never start another workflow run.
* The commit message carries `[skip ci]`.
* A `concurrency` group prevents two runs from overlapping.
* If the GitHub API fails, existing generated files are left untouched.
