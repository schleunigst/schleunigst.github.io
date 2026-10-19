# blog

A small static research blog with a serif, essay-like design (see
`DESIGN-NOTES.md` for the design system and the reference analysis). It is
built by `build.py` using **only the Python standard library** -- no pip, no
third-party packages -- and deploys to GitHub Pages under a project subpath.

## Quick start

```bash
python3 blog/build.py                 # build into blog/dist/
python3 -m http.server -d blog/dist   # preview at http://localhost:8000
python3 blog/tests/test_build.py      # run the test suite
```

`blog/dist/` is a build artifact. It is git-ignored, cleared on every build,
and must never be hand-edited.

## Layout

```
blog/
  build.py                 the builder (stdlib only)
  content/                 one .md file per entry
    _template.md           never built; copy-paste scaffold for new entries
    _sample.md             never built; draft sample exercising every feature
  static/                  copied verbatim to dist/static/
    style.css              the design system
    footnotes.js           popover footnotes
    entry.js               progress bar, roadmap active state, keeps, anchors
    interactive.css        styles for interactive figures (data-ix)
    interactive.js         interactive figure engine (startup / ranking / arbiter)
    data.js                per-cycle explorer for the bundled dataset page
    figures/               entry figures (SVG; also the no-JS fallbacks)
  data/                    published benchmark datasets (see below)
    phone/                 Galaxy S24 FE runs, com.cardscanner. prefix stripped
    emulator/              pixel_bench AVD runs, same shape
  tools/
    collect_data.py        copies ../results_phone/ and ../results/ into data/
    make_figures.py        regenerates static/figures/*.svg from the inline
                           benchmark numbers (stdlib only)
  tests/                   unittest suite + fixtures
  dist/                    generated (git-ignored)
```

## Writing an entry

1. Copy `content/_template.md` to `content/<slug>.md`.
2. Fill in the frontmatter and write the body.
3. Run `python3 blog/build.py`. The entry lands at `dist/<slug>/index.html`
   and appears on the index, newest first by `date`.

Files whose names start with `_` are never built. Files with `draft: true` in
the frontmatter are skipped (and listed in the build summary).

### Frontmatter syntax (exact)

The file must start with a line containing only `---`, then `key: value`
lines, then a closing `---` line. Plain text values; surrounding quotes are
optional. Full-line `# comments` are ignored. Accepted keys:

| Key | Required | Meaning |
| --- | --- | --- |
| `title` | yes | entry title (also the default slug source) |
| `dek` | no | one-sentence summary; shown under the title and on the index card |
| `author` | no | byline name |
| `org` | no | organisation shown after the author |
| `org_url` | no | makes the org a link |
| `status` | no | e.g. `Working notes`, `Draft`, `A working hypothesis` |
| `date` | no | free string, preferably `YYYY-MM-DD`; drives index order |
| `slug` | no | URL segment; defaults to a slugified title |
| `draft` | no | `true` skips the file |
| `sections` | no | roadmap cards, see below |

`sections` is a key on its own line, followed by one `- Label | Deck` line per
H2 heading, **in the same order as the H2s**:

```yaml
sections:
  - The evidence | Why the old reading fails
  - The new reading | What we think is happening instead
```

Without `sections`, the roadmap is generated from the H2 headings themselves.
Read time is computed automatically from prose words (200 wpm).

## Supported markdown

`build.py` contains a hand-written converter (no markdown package). It
supports exactly this subset:

- ATX headings `#` ... `####`; auto slug anchors (`## Hello, World` ->
  `id="hello-world"`), or explicit `## Text {#custom-id}`.
- Paragraphs; **bold**; *italic* (also `_italic_`); `` `inline code` ``.
- Links `[text](url)` and images `![alt](src)` (titles `"..."` allowed).
- Bullet (`-`, `*`, `+`) and numbered (`1.`, `1)`) lists, with **one** level
  of nesting (indent nested items by 2+ spaces).
- Blockquotes `> ...`; a callout with `> [!NOTE]` (also TIP, INFO, WARNING,
  IMPORTANT, CAUTION) on the first line.
- Fenced code blocks with an optional language: ` ```python `.
- GFM pipe tables; `---:` right-aligns a column (emits `class="num"`),
  `:---:` centers (`class="ctr"`); tables are auto-wrapped in
  `<div class="table-wrap">` so they scroll.
- Horizontal rules (`---`).
- Footnotes: reference `[^id]`, definition `[^id]: text`. The definition may
  continue on following lines indented by four spaces. Marks render as small
  bracketed superscript numbers that open hover/focus popovers; the full list
  also appears at the end of the entry.
- **Raw HTML passthrough, both block and inline.** A line that starts with a
  block-level tag (`<figure>`, `<div>`, `<section>`, `<table>`, `<svg>`,
  `<details>`, `<blockquote>`, ...) begins a raw block that is copied through
  byte-for-byte, including blank lines and nested tags, until its tags balance
  closed. Markdown is **not** processed inside raw blocks. Inline tags
  (`<span class="metric">...`) pass through inside paragraphs.
- Everything else is HTML-escaped.

Literal `<` or `&` in prose is escaped for you; a stray line starting with an
unknown lowercase tag like `<notatag>` is treated as text.

## Figure utility classes

All of these are styled in `static/style.css`; use them inside raw HTML
blocks (see `content/_template.md` for full copy-paste examples).

| Class | Use |
| --- | --- |
| `.fig-grid` | responsive image grid: `<div class="fig-grid"><div class="fig-cell"><img ...><span class="fig-label">A</span></div>...</div>` |
| `.fig-strip` | horizontal row of small labeled images: `<div class="fig-strip"><div class="fig-cell"><img ...><span class="fig-label">step 1</span></div>...</div>` |
| `.fig-compare` / `.side-by-side` | two columns: `<div class="fig-compare"><div class="fig-panel"><h4>What we thought</h4><p>...</p></div><div class="fig-panel">...</div></div>` |
| `.verdict-chips` | inline chips: `<div class="verdict-chips"><span>hold: 97%</span><span class="is-negative">off by 3%</span></div>` |
| `.metric` | inline metric highlight: `<span class="metric">81.1%</span>` |
| `.event-strip` | mono pill row: `<div class="event-strip"><span>load model</span><span>score &uarr;</span></div>` |
| `.callout` | note box: `<blockquote class="callout callout-note"><p class="callout-label">Note</p><p>...</p></blockquote>` |
| `.table-wrap` | makes any wide table scroll (markdown tables get it automatically) |
| `.kv-table` | compact key/value metrics: `<table class="kv-table">...<td class="num">58.35%</td>...` |
| `.hero-figure` | full-bleed-ish figure: `<figure class="hero-figure"><img ...><figcaption>...</figcaption></figure>` |
| `.decomp` | CSS-only decomposition bars (see interactive.css): `.decomp-row` > `.decomp-head` + `.decomp-bar` (`.decomp-seg`, `.decomp-ghost`) + `.decomp-under`, then a `.decomp-legend` |
| `.fig-keep` | click-to-keep highlight: add to any `<figure>`; readers click (or focus + Enter) to outline it |
| `td.num` / `th.num` | right-aligned tabular number cells in hand-written tables |

Figure caption conventions: `<figcaption>` with an optional
`<span class="fig-num">Fig 1.</span>` lead-in; `<strong>` for the bold lead
sentence. Captions are sans-serif, muted, and left-aligned.

## Interactive figures

`static/interactive.js` upgrades a figure when it carries
`data-ix="startup|ranking|arbiter"`. The figure always ships a static SVG
fallback first; the script removes it only after it successfully builds the
live version, so the page stays readable without JavaScript (and with
`prefers-reduced-motion`, playback is skipped and the end state shown).

```html
<figure class="ix" id="ix-ranking" data-ix="ranking">
  <img class="ix-fallback" src="../static/figures/ranking-inversion.svg" alt="...">
  <figcaption>...</figcaption>
</figure>
```

- `startup` — replay of the tap-to-first-frame event chain, one button per
  implementation. Markers are hoverable/focusable for exact numbers.
- `ranking` — environment toggle with animated bars swapping rank order.
- `arbiter` — two-lane race from tab tap to RFID start, with the camera
  dead-time band revealed as the playhead passes.

Datasets for each kind live at the top of `interactive.js` (keyed by kind,
not by figure), which is fine for one entry but should be split per-entry
when a second entry needs different numbers. Styles are in
`static/interactive.css`; all playback respects reduced motion.

A fourth style, `.decomp`, is pure CSS (no JS): rows of segmented bars for
"where the time went" breakdowns, where text lays itself out and cannot clip
the way hand-positioned SVG text can. Segment variants: `.is-camera` (accent,
start of bar), `.is-stack` (solid warm block, optional inner `<span>` label),
`.is-wait` (hatched warm — "held, but not working"), plus `.decomp-ghost` for
the not-yet-reached remainder; under-bar flags accept the same `is-*` classes
and legend swatches are `.sw.is-*`. The generator in `tools/make_figures.py`
still emits `cold-decomposition.svg` for the record, but the entry uses the
CSS version.

## Bundled dataset (`dist/data/`)

The benchmark datasets ship with the site so every number in an entry can be
checked against the raw logs it came from.

```bash
python3 blog/tools/collect_data.py    # ../results_phone/ -> data/phone/
                                      # ../results/       -> data/emulator/
python3 blog/build.py                 # copies blog/data/ -> dist/data/ + page
python3 blog/build.py --data other/   # publish a different directory
```

`collect_data.py` strips the `com.cardscanner.` prefix from the harness files
(`<app>.stages.json`, `.events.json`, `.summary.json`, `.rows.json`) and
copies only files whose bytes changed (`--check` reports without writing).
`build.py` then copies `blog/data/` verbatim into `dist/data/` and renders
`dist/data/index.html`: a dataset listing, a server-rendered summary table of
medians per cycle kind (works without JavaScript), and a JSON manifest for the
explorer. Stage timestamps in the files are microseconds since the cycle's tab
tap; the page renders them as ms / s.

`static/data.js` upgrades the page with the per-cycle browser: environment and
app pickers, a cycle strip, and a full stage timeline plus delta table for the
selected cycle. Selections are permalinked (`data/?env=phone&app=p3_mlkit&cycle=3`);
without the script the static table and the raw-file links remain. Styles are
`.dx-*` in `interactive.css`.

The build skips data entirely when `--data` points at a missing directory (the
test suite builds both ways), so the site works with or without `blog/data/`.

## Site text

The masthead tagline, index title/dek and font link live at the top of
`build.py` as `SITE_TAGLINE`, `SITE_TITLE`, `SITE_DEK` and `FONTS_HREF`.
Edit them there.

## Testing

```bash
python3 blog/tests/test_build.py
```

Covers frontmatter parsing (including draft/underscore skipping), slug
generation, read time, every converter feature, raw-HTML passthrough with
blank lines and nesting, footnotes, tables, and full builds against
`tests/fixtures/site/` -- asserting relative links, `.nojekyll`, the copied
text version, and that every generated page parses with stdlib
`html.parser`.

## Deploying to GitHub Pages

There is no git remote or commit yet; set that up yourself first.

1. Push the repository to GitHub (the default branch must be `main` or
   `master`).
2. In the repository: **Settings -> Pages -> Source: "GitHub Actions"**.
3. Every push that touches `blog/**` (or the workflow itself) rebuilds the
   site with `python3 blog/build.py` and deploys `blog/dist` via
   `.github/workflows/deploy-blog.yml`. You can also run it manually with
   **Actions -> Deploy blog to GitHub Pages -> Run workflow**
   (`workflow_dispatch`).
4. The site is served at `https://<user>.github.io/<repo>/`. All emitted
   links are relative, so project subpaths work unchanged; a `.nojekyll`
   file is written so Pages serves the files verbatim.

No commit is performed by the build or the tests.
