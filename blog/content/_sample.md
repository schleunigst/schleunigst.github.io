---
# ============================================================================
#  DRAFT SAMPLE -- never built. This file starts with "_" (always skipped)
#  and also carries `draft: true` (skipped when published).
#  It exercises every feature the builder supports, so tests and curious
#  authors have a working example:
#    python3 -c "import blog.build ..."  or run the test suite
#  To publish something like it, copy it to content/<slug>.md and set
#  draft to false (and give it a real title).
# ============================================================================
title: Sample draft exercising the markup subset
dek: A test entry that touches every supported block and inline feature, plus the figure utility classes.
author: Test Author
org: Test Org
org_url: https://example.com
status: Draft sample
date: 2026-10-16
slug: sample-draft
draft: true
sections:
  - Inline and blocks | A tour of the converter's supported subset
  - Figures and tables | Raw HTML passthrough examples
---

This opening paragraph is the one the stylesheet enlarges slightly. It is a
test fixture, not a real entry -- the draft flag keeps it out of `dist/`.

## Inline and blocks

Plain text with **bold**, *italic*, `inline code`, and a
[relative link](../) plus an [external link](https://example.com). A footnote
pointer[^note] renders as a small bracketed mark wired to a popover, and an
inline HTML span like <span class="metric">2.1x</span> passes through.

A paragraph with raw inline HTML: <span class="verdict-chips"><span>ok</span><span class="is-negative">no</span></span>
at the end of a line.

### Lists

- First bullet
- Second bullet
  - Nested bullet one
  - Nested bullet two
- Third bullet

1. First numbered step
2. Second numbered step
3. Third numbered step

### Quote and callout

> A plain blockquote with a muted left rule.

> [!NOTE]
> A callout note for caveats and reading instructions.

### Code

```python
def example(value: int) -> int:
    return value * 2
```

---

## Figures and tables

| Model | Params | Score |
| --- | ---: | :---: |
| Small | 92k | 0.58 |
| Medium | 7.06M | 0.81 |

<figure class="fig-keep" data-sample="passed-through">
  <div class="fig-grid">

    <div class="fig-cell">
      <span class="fig-label">placeholder A</span>
    </div>
    <div class="fig-cell">
      <span class="fig-label">placeholder B</span>
    </div>
  </div>
  <figcaption><span class="fig-num">Fig 1.</span> This raw block contains a
  blank line and nested divs; the converter must pass it through untouched.
  It also carries <code>class="fig-keep"</code> for the click-to-keep helper.</figcaption>
</figure>

<div class="event-strip">
  <span>load</span><span>ablate</span><span>score&nbsp;&uarr;</span>
</div>

<figure class="hero-figure">
  <div class="fig-compare">
    <div class="fig-panel">
      <h4>What we thought</h4>
      <p>Placeholder text for the left panel.</p>
    </div>
    <div class="fig-panel">
      <h4>What's going on</h4>
      <p>Placeholder text for the right panel.</p>
    </div>
  </div>
  <figcaption>A compare figure inside a hero figure.</figcaption>
</figure>

<blockquote class="callout callout-warning">
  <p class="callout-label">Warning</p>
  <p>A raw-HTML callout.</p>
</blockquote>

[^note]: Footnote definitions can span multiple lines when continuation
    lines are indented by four spaces, like this one.
