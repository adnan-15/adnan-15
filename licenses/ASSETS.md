# Third-party assets used in the SVGs

## Fonts (SIL Open Font License 1.1, texts alongside this file)
| Font | Used for | Copyright | Licence text |
| --- | --- | --- | --- |
| Big Shoulders (Bold) | Display type | 2019 The Big Shoulders Project Authors (https://github.com/xotypeco/big_shoulders) | OFL-BigShoulders.txt |
| JetBrains Mono (Regular, Bold) | Mono type | 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono) | OFL-JetBrainsMono.txt |

Each SVG embeds a **subset** of these fonts (only the glyphs that SVG uses) as base64 WOFF2. Neither licence declares a
Reserved Font Name, so subsetting and embedding is permitted. The fonts are not sold on their own.

## Icons
Glyph paths were read from the `react-icons` 5.6.0 package (MIT) and inlined as plain SVG paths.

| Icon(s) | Source | Licence |
| --- | --- | --- |
| HTML5, CSS, JavaScript, React, Tailwind CSS, Redux, TanStack Query, Axios, Python, Django, Flask, PostgreSQL, Chart.js, Git, GitHub | Simple Icons (https://simpleicons.org) | CC0 1.0 |
| Java | Devicon Java mark (https://devicon.dev) | MIT |
| LinkedIn | Font Awesome Free "linkedin" brand glyph (https://fontawesome.com) | CC BY 4.0 |
| Location pin, graduation cap, four-point sparkle | Hand-drawn for this project | n/a |

Notes
* Simple Icons has no Java or LinkedIn mark, so those two come from Devicon and Font Awesome Free. They were taken from the
  installed npm package, not downloaded from Oracle or LinkedIn. Swap in the first-party files if you need pixel-exact marks.
* The Simple Icons entry for TanStack Query is titled "React Query" in that set; the label shown on the page is "TanStack Query".
* Brand names and logos belong to their owners and are used only to identify the technologies.
