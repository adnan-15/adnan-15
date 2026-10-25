# Third-party assets embedded in the SVGs

| Asset | Source | License |
|---|---|---|
| Unbounded (ExtraBold, 800) - display font | https://github.com/googlefonts/unbounded - variable font instanced at wght 800, subset to Latin, converted to WOFF2 | SIL OFL 1.1 (`OFL-Unbounded.txt`) |
| JetBrains Mono (Medium 500, Bold 700) - mono font | https://github.com/JetBrains/JetBrainsMono - official `webfonts/*.woff2`, subset to Latin + a few symbols | SIL OFL 1.1 (`OFL-JetBrainsMono.txt`) |
| Tech and social icons (HTML5, CSS, JavaScript, React, Tailwind CSS, Redux, TanStack Query, Axios, Chart.js, Git, GitHub, Python, Django, Flask, PostgreSQL) | Simple Icons v16.36.0 - https://github.com/simple-icons/simple-icons | CC0 1.0 (`LICENSE-SimpleIcons-CC0.md`); brand marks remain trademarks of their owners |
| Java glyph | Simple Icons `openjdk` (Simple Icons has no `java` icon) - shown with the label "Java" | CC0 1.0; mark belongs to its owner |
| LinkedIn mark | Simple Icons v13.15.0 `linkedin.svg` (last release that contained it; later releases removed it) | CC0 1.0 for the file; LinkedIn is a trademark of LinkedIn Corp. |
| Portraits | Your own `id.png` and `right_pointing.png`, downscaled with alpha unchanged (620 / 380 / 860 px wide) | yours |

The fonts are embedded as base64 WOFF2 `@font-face` data URIs, so no SVG makes a network request.
