# Design notes: what the reference does, and what this blog mirrors

Reference analyzed: `https://already-clean.goodfire.com/` (HTML + `style.css`,
`title-typography.css`, `footnotes.css`, `footnotes.js`, `roadmap.css`, plus the
`essay.md` plain-text twin). This blog is a **from-scratch recreation of the look and
behavior**; no stylesheet, script, text, image or branding is copied. The Goodfire name
appears nowhere in the build output.

## What the reference is

A single long-form research essay rendered as one HTML page:

- A 65px-tall sans-serif masthead (identity line left, one external link right,
  hairline bottom border).
- A wide serif title block: `h1` (Source Serif 4, up to 65–68px, weight 600,
  tight tracking, balanced wrapping) + italic dek paragraph + a two-line byline
  (`author · org` then `status · read time · text version · jump link`).
- A "roadmap" of four numbered cards, each linking to a major `H2` section
  (number, bold sans label, serif deck). Hovering one card dims the others.
- A narrow reading column (~660px of text, inside a wider ~1160px canvas) with
  Georgia body text at 19px/1.75, Source Serif 4 section headings, sans figure
  captions (13px, `#717a80`), sans `h3`s, and a left-margin "sidenote" pattern.
- Interactive figures built from raw HTML/SVG plus small vanilla-JS scripts.
- Footnotes ("Distill-style"): a tiny superscript bracketed mark that opens a
  **hover/focus popover card**, with the full footnote list still present in the
  document; tapping pins it open on touch, `Escape` closes.
- A 3px reading-progress bar, smooth anchor scrolling (`scroll-padding-top:85px`),
  `prefers-reduced-motion` support and a full print stylesheet.

The reference site remains the copyright of its authors; we reproduce measurements and
interaction ideas, not code or content.

## Extracted tokens (verified from the served CSS)

### Color

| Token | Value | Use in reference |
| --- | --- | --- |
| `--ink` | `#222629` | body text |
| `--muted` | `#677179` | secondary text, roadmap links |
| caption muted | `#717a80` | `figcaption` text |
| `--line` | `#dce1e4` | hairline rules, borders |
| `--accent` | `#28627b` | links, footnote marks, progress bar |
| link hover | `#163d51` | `a:hover` |
| link underline | `#bccdd5` | `a { border-bottom }` |
| `--tint` | `#f4f7f8` | soft panels, segment backgrounds |
| `--orange` | `#ac6538` | "warm"/negative accents (figures) |
| dek color | `#566168` | italic title-block dek |
| byline names | `#2f393f` / status `#7a848b` | title-block byline |
| selection | `#d7e9ef` | `::selection` |
| focus ring | `#3585ab` | `:focus-visible` outline (3px, offset 5px) |

The mission brief guessed `#34444b` / `#c9772c` / `#4f82ad` for ink/warm/cool; the
actually-served stylesheet uses `#222629` ink, `#ac6538` warm and `#28627b` accent.
Where the brief and the CSS disagreed I kept the verified CSS values (and used
`#28627b` for links/accents). `#717a80` **is** the real caption muted value.

### Type

| Token | Value |
| --- | --- |
| `--display` | `"Source Serif 4", Georgia, "Times New Roman", serif` (Google Fonts, variable optical size 8–60) |
| `--serif` (body) | `Georgia, "Times New Roman", serif` |
| `--sans` | `-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif` |
| `--mono` | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` |
| `h1` | `clamp(44px, 4.6vw, 66px)` / 600 / `line-height 1.06` / tracking `-0.004em` |
| dek | 23px / italic / 1.45 / `#566168` |
| body `p` | 19px / 1.75 serif (opening paragraph 20px) |
| `h2` | 32px display serif 600 |
| `h3` (section) | 26px display serif 600; UI `h3` 23–24px sans 600 |
| byline names | 15px / 500 / `#2f393f`; status 13.5px `#7a848b` |
| `figcaption` | 13px / 1.6 sans / `#717a80`, max-width 810px |
| roadmap label | 15px / 600 sans; deck 14px / 1.45 serif `#677179`; number 12px faint |
| masthead | 65px tall, 14px, `#677179` links |
| page footer | 12px / `#7e8a91` |

### Layout

| Token | Value |
| --- | --- |
| canvas | max-width 1160px (masthead, footer, figure strips) |
| title block | max-width 980px (1000px ≥1450px), margin 72–88px auto 42px |
| reading column | `article section { max-width: 660px }` |
| wide figures | 1040px, pulled left by `-190px` from the 660px column |
| paragraph rhythm | `margin: 0 0 23px` |
| section spacing | `h2 { margin: 65px 0 25px }` |
| roadmap | 4 equal columns, 44px gap, max-width 1128px |
| radius | 2–4px on cards/inputs, 6px popover |

### Motion / behavior

- `html { scroll-behavior: smooth; scroll-padding-top: 85px }`
- reading-progress bar: 3px, `--accent`, fixed top, width = scroll fraction
- roadmap hover: `:has(.card:hover) .card:not(:hover) { opacity: .35 }`-style dimming
- footnotes: `.fn-mark` is a `<button>`; `.fn-pop[role=tooltip]` inside
  `<span class="fn">`; open on `:hover`, `:focus-visible +`, or `.fn-open`;
  click toggles, outside click and `Escape` close; `aria-describedby` wires the
  mark to the popover; popover max-width `min(420px, 86vw)`, max-height
  `min(62vh, 560px)`, scrolls internally
- `@media (prefers-reduced-motion: reduce)`: no smooth scroll, no transitions
- print stylesheet hides chrome (progress bar, roadmap, menus)

## What this blog mirrors

- Same token palette, fonts (Source Serif 4 for display **and** body), body size
  (~19px / 1.72), caption styling, byline layout, masthead height, footer style,
  selection color, focus ring, progress bar, smooth anchors.
- Title block: `h1` → italic dek → two-line byline (`author · org` /
  `status · N-minute read · Text version · ↑ All entries`).
- Numbered roadmap cards above the entry body, generated from frontmatter
  `sections` (or from the entry's `H2`s), linking to heading anchors; hovering a
  card dims the rest; the active section is highlighted while scrolling.
- Footnote marks as small bracketed numbers (`[1]`) in `--accent` superscript that
  open hover/focus popovers; the full list stays at the end of the entry.
- Figure conventions: `figure` + left-aligned sans `figcaption`; a catalog of
  utility classes (`.fig-grid`, `.fig-strip`, `.fig-compare`, `.hero-figure`, …)
  so entries can build reference-style figures in raw HTML.
- Tables with thin rules and sans headers, numeric cells right-aligned via
  `td.num` / `th.num` (GFM `---:` produces that class automatically).
- Muted left-rule blockquotes, plus a `.callout` note box.

## What is simplified, and why

| Reference | Here | Why |
| --- | --- | --- |
| Source Serif 4 for display + Georgia for body | Source Serif 4 for display **and** body | Mission asked for a Source Serif 4 body; one family keeps the build self-consistent (Georgia stays as fallback) |
| Bespoke per-figure JS (canvases, sliders, atlases) | Utility CSS classes + tiny `entry.js` helpers | No third-party code, no data files; entries can embed their own inline SVG/HTML |
| Footnote popovers partially generated by hand | Footnotes converted from `[^id]` markdown by `build.py` | Entry authors write plain markdown footnotes; builder emits the popover markup |
| "References" list of 22 citations with popovers | No special reference system; authors use footnotes or links | Keeps the converter small; documented |
| Dynamic hero animation, contents dropdown, paper.js | Omitted; roadmap + progress bar kept | Out of scope, heavyweight |
| Static single essay | Multi-entry build with index cards, drafts, per-entry roadmap | Mission requirement |
| Sidebar sidenotes | Not mirrored | Column-layout complexity; callouts cover the use case |
| `66px` h1 at 1450px+ | `clamp(40px, 4.6vw, 62px)` | Slightly calmer for entry pages; same proportions |
| Print stylesheet in full detail | A compact print block | Same intent, fewer rules |

## Deviations of note

- **Relative URLs are mandatory.** The reference is served at a domain root; this
  site must work under `https://user.github.io/repo/`, so every `href`/`src` the
  builder emits is relative (`../static/…`, `./slug/`, `slug.md`) and tests
  enforce it. The only absolute URLs are the Google Fonts `<link>` and author links.
- **No YAML library.** Frontmatter is a tiny line format (`key: value` plus
  `- Label | Deck` section lines); exact syntax documented in `README.md` and
  `content/_template.md`.
- **No markdown/YAML/Jinja packages.** The converter in `build.py` is hand-written
  and covers exactly the documented subset, including raw-HTML passthrough with
  tag-depth tracking.
- **Footnote popovers** are our own ~30-line `footnotes.js` (click/tap toggle,
  Escape, outside-click close, ARIA wiring) rather than a copy of the reference
  script; look and behavior are matched.
- **Build artifacts.** `blog/dist/` is generated only; `.nojekyll` is written so
  GitHub Pages serves files verbatim.
