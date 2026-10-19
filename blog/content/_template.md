---
# ============================================================================
#  ENTRY TEMPLATE -- this file is never built.
#  Files whose names start with "_" are skipped by build.py, as are files with
#  `draft: true`. Copy this file to `content/<your-entry>.md` and edit it.
#
#  Frontmatter rules (the block between the two `---` fences):
#    - one `key: value` per line; values are plain text (quotes optional)
#    - keys: title (required), dek, author, org, org_url, status, date,
#      slug, draft, sections
#    - `date` is a free string, ideally YYYY-MM-DD (entries list newest-first)
#    - `slug` defaults to a slugified title; it becomes dist/<slug>/
#    - `sections:` (optional) is followed by one `- Label | Deck` line per H2
#      heading, in the same order as the H2s, to drive the roadmap cards.
#      Without it, roadmap cards are generated from the H2 headings.
# ============================================================================
title: A clear, specific entry title
dek: One-sentence summary shown under the title and on the index card.
author: Schleunigst
org: Schleunigst
org_url: https://example.com
status: Working notes
date: 2026-01-31
slug: a-clear-specific-entry-title
draft: false
sections:
  - First theme | What this section covers, in a few words
  - Second theme | Another short deck for the roadmap card
---

Opening paragraph. This is the only paragraph that the stylesheet slightly
enlarges, in the style of the reference essay's opening statement. Write
ordinary markdown here -- the converter handles the subset documented below,
and raw HTML blocks pass through untouched.

## First theme

Body paragraphs use **bold**, *italic*, `inline code`, and [links](https://example.com).
Inline HTML is allowed: a <span class="metric">2.1x</span> metric highlight,
or any <span class="some-class">span</span> you need.

### A subsection

Bullet list, one nesting level:

- First bullet
- Second bullet
  - Nested bullet
  - Another nested bullet
- Third bullet

Numbered list:

1. First step
2. Second step
3. Third step

Blockquote (muted left rule):

> An ordinary blockquote, set off from the text.

Callout note (same syntax, with a marker on the first line):

> [!NOTE]
> A callout box for asides, caveats and "how to read this" notes.
> Kinds: NOTE, TIP, INFO, WARNING, IMPORTANT, CAUTION.

Horizontal rule:

---

## Second theme

Fenced code block with an optional language label:

```python
def convert(text):
    return text.replace("--", "-")
```

Footnote reference[^first] and a second one.[^second]

[^first]: Footnotes are single paragraphs; continuation lines are indented
    by four spaces and joined into the same note.
[^second]: Popovers open on hover or keyboard focus, pin open on tap/click,
    and close on Escape or an outside click. The full list also appears at
    the end of the entry, in reference order.

### Markdown table

GFM pipe tables work; `:` alignment also drives CSS classes
(right column -> `class="num"`, center -> `class="ctr"`):

| Model | Params | Score | Note |
| --- | ---: | :---: | --- |
| Small | 92k | 0.58 | underfits |
| Medium | 7.06M | 0.81 | baseline |
| Large | 28.6M | 0.87 | best |

---

# Figure catalog (raw HTML)

Raw HTML blocks are passed through byte-for-byte and are NOT parsed as
markdown, so build figures directly in HTML. All classes below are defined in
`static/style.css`.

## Image grid with labels

```html
<figure>
  <div class="fig-grid">
    <div class="fig-cell">
      <img src="assets/example-a.png" alt="Placeholder A">
      <span class="fig-label">Label A</span>
    </div>
    <div class="fig-cell">
      <img src="assets/example-b.png" alt="Placeholder B">
      <span class="fig-label">Label B</span>
    </div>
  </div>
  <figcaption><span class="fig-num">Fig 1.</span> A labeled grid.</figcaption>
</figure>
```

## Horizontal strip of small labeled images

```html
<figure>
  <div class="fig-strip">
    <div class="fig-cell"><img src="assets/step-1.png" alt=""><span class="fig-label">step 1</span></div>
    <div class="fig-cell"><img src="assets/step-2.png" alt=""><span class="fig-label">step 2</span></div>
    <div class="fig-cell"><img src="assets/step-3.png" alt=""><span class="fig-label">step 3</span></div>
  </div>
  <figcaption>Training snapshots, left to right.</figcaption>
</figure>
```

## Two-column comparison

```html
<div class="fig-compare">
  <div class="fig-panel">
    <h4>What we thought</h4>
    <p>A short paragraph on the left side.</p>
  </div>
  <div class="fig-panel">
    <h4>What's going on</h4>
    <p>And the corrected reading on the right.</p>
  </div>
</div>
```

`class="side-by-side"` is an alias of `.fig-compare` when you just want two
columns without the compare framing.

## Verdict chips

```html
<div class="verdict-chips">
  <span>hold: 97%</span>
  <span class="is-negative">off by 3%</span>
</div>
```

## Inline metric highlight

```html
<p>Accuracy moved from 58% to <span class="metric">81.1%</span>.</p>
```

## Monospace event strip (log-style pills)

```html
<div class="event-strip">
  <span>load model</span><span>ablate head 4.2</span><span>score ↑</span>
</div>
```

## Compact key/value metric table

```html
<div class="table-wrap">
  <table class="kv-table">
    <thead><tr><th>Metric</th><th class="num">Value</th></tr></thead>
    <tbody>
      <tr><td>Top-1 accuracy</td><td class="num">58.35%</td></tr>
      <tr><td>Top-5 accuracy</td><td class="num">81.14%</td></tr>
    </tbody>
  </table>
</div>
```

## Full-bleed-ish hero figure

```html
<figure class="hero-figure">
  <img src="assets/hero.png" alt="Wide hero image">
  <figcaption>A wide figure that leans past the text column.</figcaption>
</figure>
```

## Click-to-keep figure

Add `class="fig-keep"` to any figure; readers can click it (or focus and press
Enter) to outline it while comparing figures.

```html
<figure class="fig-keep">
  <img src="assets/keep-me.png" alt="">
  <figcaption>Click to keep this figure highlighted.</figcaption>
</figure>
```

## Callout as HTML

```html
<blockquote class="callout callout-note">
  <p class="callout-label">Note</p>
  <p>Callouts can also be written directly in HTML.</p>
</blockquote>
```

## Wide table wrapper

Wrap any wide table in `<div class="table-wrap">...</div>` so it scrolls
horizontally instead of overflowing the column. (`build.py` already wraps all
markdown-generated tables this way.)
