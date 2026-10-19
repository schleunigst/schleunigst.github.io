#!/usr/bin/env python3
"""Static research-blog builder (stdlib only).

Usage:
    python3 blog/build.py [--content DIR] [--static DIR] [--dist DIR]

Reads every published entry from content/*.md (files starting with "_" and
files carrying `draft: true` are skipped), converts the markdown body with a
hand-written converter, wraps it in a shared HTML shell and writes:

    dist/index.html                 index of published entries (newest first)
    dist/<slug>/index.html          one page per entry
    dist/<slug>/<slug>.md           verbatim "text version" copy of the source
    dist/static/...                 copy of static/
    dist/.nojekyll                  so GitHub Pages serves files verbatim

Every href/src emitted by the builder is relative, so the site works from a
project subpath such as https://user.github.io/repo/.

Exit code 0 on success, 1 on any content error (with a clear message).
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path

# --------------------------------------------------------------------------
# Site constants (edit these to taste; no branding of any other site included)
# --------------------------------------------------------------------------

SITE_TITLE = "Schleunigst"
SITE_TAGLINE = "Notes on making Android cameras instant"
SITE_DEK = (
    "Field notes on making Android cameras instant: teardowns of the "
    "scan stacks people actually run, every camera state priced in "
    "milliseconds and milliamps, and the design the measurements imply. "
    "Newest entries first."
)
WORDS_PER_MINUTE = 200

FONTS_HREF = (
    "https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700"
    "&display=swap"
)

BLOG_DIR = Path(__file__).resolve().parent
DEFAULT_CONTENT = BLOG_DIR / "content"
DEFAULT_STATIC = BLOG_DIR / "static"
DEFAULT_DIST = BLOG_DIR / "dist"
DEFAULT_DATA = BLOG_DIR / "data"

STRING_KEYS = {"title", "dek", "author", "org", "org_url", "status", "date", "slug"}


class BuildError(Exception):
    """Raised with a message shown to the author; build exits 1."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def esc(value: object) -> str:
    """Escape text for HTML text nodes and quoted attributes."""
    return html.escape(str(value), quote=True)


def slugify(text: str) -> str:
    """Lowercase ASCII slug: runs of non-alphanumerics collapse to '-'."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def strip_inline(text: str) -> str:
    """Plain text from inline markdown/html (for slugs and roadmap labels)."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\{\#[A-Za-z0-9_-]+\}", "", text)
    text = text.replace("**", "").replace("*", "").replace("`", "")
    return text.strip()


def read_time_minutes(body: str) -> int:
    """Reading time from prose words only (fences/code/links removed), 200 wpm."""
    text = re.sub(r"```.*?```", " ", body, flags=re.S)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[#>*_|~`-]+", " ", text)
    words = [w for w in text.split() if any(ch.isalnum() for ch in w)]
    return max(1, math.ceil(len(words) / WORDS_PER_MINUTE))


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _iso_date(value: str):
    try:
        return _date.fromisoformat(value.strip())
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------


def parse_frontmatter(text: str, filename: str):
    """Return (meta, body).

    Accepted syntax -- lines between the first `---` fence and the next `---`:

        key: value                      (title, dek, author, org, org_url,
                                         status, date, slug, draft)
        sections:                       (optional, own line)
          - Label | Short deck          (one per H2 heading, in order)
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise BuildError(
            f"{filename}: missing frontmatter -- the file must start with a line "
            f"containing only '---'"
        )
    meta: dict = {}
    sections: list = []
    section_mode = False
    closed = False
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            closed = True
            i += 1
            break
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith("#"):
            i += 1
            continue
        if section_mode and re.match(r"^\s*-\s+", line):
            item = line.strip()[1:].strip()
            label, _, deck = item.partition("|")
            if not label.strip():
                raise BuildError(f"{filename}: empty section label on frontmatter line {i + 1}")
            sections.append({"label": label.strip(), "deck": deck.strip()})
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not m:
            raise BuildError(
                f"{filename}: frontmatter line {i + 1} is not 'key: value': {line!r}"
            )
        key = m.group(1).lower()
        value = m.group(2).strip()
        section_mode = False
        if key == "sections":
            if value:
                raise BuildError(
                    f"{filename}: 'sections' must be followed by indented '- Label | Deck' "
                    f"lines, not an inline value"
                )
            section_mode = True
        elif key in STRING_KEYS:
            meta[key] = _strip_quotes(value)
        elif key == "draft":
            meta["draft"] = value.strip().lower() in {"true", "yes", "1"}
        else:
            raise BuildError(
                f"{filename}: unknown frontmatter key {key!r} (accepted: "
                f"{', '.join(sorted(STRING_KEYS))}, draft, sections)"
            )
        i += 1
    if not closed:
        raise BuildError(f"{filename}: frontmatter is missing its closing '---' line")
    meta["sections"] = sections
    return meta, "\n".join(lines[i:])


# --------------------------------------------------------------------------
# Markdown converter
# --------------------------------------------------------------------------

TAG_RE = re.compile(
    r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*?)(/?)>", re.S
)

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}

BLOCK_TAGS = {
    "address", "article", "aside", "audio", "blockquote", "canvas", "caption",
    "colgroup", "dd", "details", "dialog", "div", "dl", "dt", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hr", "iframe", "img", "li", "main", "math", "nav", "ol",
    "option", "p", "picture", "pre", "script", "section", "select", "source",
    "style", "summary", "svg", "table", "tbody", "td", "template", "textarea",
    "tfoot", "th", "thead", "tr", "ul", "video",
}

CODE_LANGS = {
    "bash", "c", "cpp", "css", "diff", "go", "html", "java", "js", "json",
    "jsx", "kotlin", "md", "python", "py", "ruby", "rust", "sh", "sql", "svg",
    "swift", "toml", "ts", "tsx", "txt", "xml", "yaml", "yml",
}

FENCE_RE = re.compile(r"^(\s*)(```|~~~)\s*([A-Za-z0-9_+-]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.*?)\s*$")
HR_RE = re.compile(r"^\s*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
UL_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
OL_RE = re.compile(r"^(\s*)(\d{1,9})[.)]\s+(.*)$")
FNDEF_RE = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s?(.*)$")
TABLE_SEP_CELL_RE = re.compile(r"^:?-{2,}:?$")
CALLOUT_RE = re.compile(r"^\[!(NOTE|TIP|INFO|WARNING|IMPORTANT|CAUTION)\]\s*(.*)$", re.I)
HEADING_ID_RE = re.compile(r"^(.*?)\s*\{#([A-Za-z0-9_-]+)\}\s*$")

CODE_SPAN_RE = re.compile(r"`([^`]+)`")
URL_PART = r"(?:[^\s()]|\([^\s()]*\))+"
IMG_RE = re.compile(r"!\[([^\]]*)\]\(\s*(" + URL_PART + r")(?:\s+[\"']([^\"']*)[\"'])?\s*\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(\s*(" + URL_PART + r")(?:\s+[\"']([^\"']*)[\"'])?\s*\)")
FNREF_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)\]")
BOLD_ITAL_RE = re.compile(r"\*\*\*(.+?)\*\*\*", re.S)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
ITAL_RE = re.compile(r"(?<![A-Za-z0-9*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![A-Za-z0-9*])")
ITAL_UND_RE = re.compile(r"(?<![\w*])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w*])")


def _tag_delta(line: str) -> int:
    """Net opening-closing tag depth change for one raw HTML line."""
    delta = 0
    for m in TAG_RE.finditer(line):
        closing, name, _attrs, selfclose = m.groups()
        if name.lower() in VOID_TAGS or selfclose:
            continue
        delta += -1 if closing else 1
    return delta


class MarkdownConverter:
    """Hand-written converter for the documented markdown subset."""

    def __init__(self) -> None:
        self.footnotes: dict = {}            # id -> raw inline text
        self.footnote_order: list = []       # ids in first-reference order
        self.footnote_defs_order: list = []  # ids in definition order
        self.referenced: set = set()
        self.headings: list = []             # {"level", "id", "text"}
        self.warnings: list = []
        self._used_ids: dict = {}

    # ---- inline ----------------------------------------------------------

    def render_inline(self, text: str, in_footnote: bool = False) -> str:
        codes: list = []
        tags: list = []

        def stash_code(m):
            codes.append(m.group(1))
            return f"\x00C{len(codes) - 1}\x00"

        def stash_tag(m):
            tags.append(m.group(0))
            return f"\x00T{len(tags) - 1}\x00"

        out = CODE_SPAN_RE.sub(stash_code, text)
        out = TAG_RE.sub(stash_tag, out)
        out = html.escape(out, quote=True)

        def img(m):
            alt, src, title = m.group(1), m.group(2), m.group(3)
            t = f' title="{title}"' if title else ""
            return f'<img src="{src}" alt="{alt}" loading="lazy"{t}>'

        def link(m):
            label, href, title = m.group(1), m.group(2), m.group(3)
            t = f' title="{title}"' if title else ""
            return f'<a href="{href}"{t}>{label}</a>'

        out = IMG_RE.sub(img, out)
        out = LINK_RE.sub(link, out)
        if not in_footnote:
            out = FNREF_RE.sub(lambda m: self._footnote_ref(m.group(1)), out)
        out = BOLD_ITAL_RE.sub(r"<strong><em>\1</em></strong>", out)
        out = BOLD_RE.sub(r"<strong>\1</strong>", out)
        out = ITAL_RE.sub(r"<em>\1</em>", out)
        out = ITAL_UND_RE.sub(r"<em>\1</em>", out)

        for i, tag in enumerate(tags):
            out = out.replace(f"\x00T{i}\x00", tag)
        for i, code in enumerate(codes):
            out = out.replace(f"\x00C{i}\x00", f"<code>{html.escape(code, quote=False)}</code>")
        return out

    # ---- footnotes -------------------------------------------------------

    def _footnote_ref(self, fid: str) -> str:
        if fid not in self.footnotes:
            self.warnings.append(f"footnote [^{fid}] is referenced but never defined")
            return html.escape(f"[^{fid}]")
        if fid not in self.referenced:
            self.referenced.add(fid)
            self.footnote_order.append(fid)
        n = self.footnote_order.index(fid) + 1
        pop = self.render_inline(self.footnotes[fid], in_footnote=True)
        return (
            f'<span class="fn">'
            f'<button type="button" class="fn-mark" id="fnref-{n}" '
            f'aria-describedby="fnpop-{n}" aria-expanded="false" '
            f'aria-label="Footnote {n}">[{n}]</button>'
            f'<span class="fn-pop" role="tooltip" id="fnpop-{n}">{pop} '
            f'<a class="fn-pop-more" href="#fn-{n}">note&nbsp;&darr;</a></span>'
            f"</span>"
        )

    def footnotes_html(self) -> str:
        if not self.footnotes:
            return ""
        ids = list(self.footnote_order)
        for fid in self.footnote_defs_order:
            if fid not in ids:
                ids.append(fid)
        items = []
        for idx, fid in enumerate(ids, 1):
            text = self.render_inline(self.footnotes[fid], in_footnote=True)
            back = ""
            if fid in self.referenced:
                back = (
                    f' <a class="fn-back" href="#fnref-{idx}" '
                    f'aria-label="Back to reference {idx}">&crarr;</a>'
                )
            items.append(
                f'<li id="fn-{idx}"><span class="fn-num">{idx}.</span> '
                f'<span class="fn-body">{text}</span>{back}</li>'
            )
        return (
            '<section class="footnotes" id="footnotes" aria-label="Footnotes">\n'
            '<h2 class="footnotes-title">Footnotes</h2>\n'
            '<ol class="footnotes-list">\n' + "\n".join(items) + "\n</ol>\n</section>"
        )

    def _extract_footnote_defs(self, lines: list) -> list:
        body = []
        i = 0
        while i < len(lines):
            m = FNDEF_RE.match(lines[i])
            if m:
                fid, text = m.group(1), m.group(2).strip()
                i += 1
                while i < len(lines) and lines[i].strip() and re.match(r"^(?: {4}|\t)", lines[i]):
                    text += " " + lines[i].strip()
                    i += 1
                if fid in self.footnotes:
                    self.warnings.append(f"footnote [^{fid}] defined twice; keeping the first")
                else:
                    self.footnotes[fid] = text
                    self.footnote_defs_order.append(fid)
                continue
            body.append(lines[i])
            i += 1
        return body

    # ---- blocks ----------------------------------------------------------

    def _unique_id(self, base: str) -> str:
        base = base or "section"
        n = self._used_ids.get(base, 0) + 1
        self._used_ids[base] = n
        return base if n == 1 else f"{base}-{n}"

    def _heading(self, level: int, text: str) -> str:
        explicit = None
        m = HEADING_ID_RE.match(text)
        if m:
            text, explicit = m.group(1), m.group(2)
        plain = strip_inline(text)
        hid = self._unique_id(explicit or slugify(plain))
        self.headings.append({"level": level, "id": hid, "text": plain or hid})
        return f'<h{level} id="{hid}">{self.render_inline(text.strip())}</h{level}>'

    def _is_table_sep(self, line: str) -> bool:
        if "|" not in line:
            return False
        cells = self._split_row(line)
        return bool(cells) and all(TABLE_SEP_CELL_RE.match(c) for c in cells)

    def _split_row(self, line: str) -> list:
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|") and not s.endswith("\\|"):
            s = s[:-1]
        cells, cur, escaped = [], [], False
        for ch in s:
            if escaped:
                cur.append(ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "|":
                cells.append("".join(cur))
                cur = []
            else:
                cur.append(ch)
        cells.append("".join(cur))
        return [c.strip() for c in cells]

    def _is_html_block_start(self, line: str):
        s = line.lstrip()
        if s.startswith("<!--"):
            return "comment"
        m = re.match(r"<([a-zA-Z][a-zA-Z0-9-]*)[\s/>]", s + " ")
        if m and m.group(1).lower() in BLOCK_TAGS:
            return "tag"
        return None

    def _starts_block(self, lines: list, i: int) -> bool:
        line = lines[i]
        if not line.strip():
            return True
        if FENCE_RE.match(line) or HEADING_RE.match(line) or HR_RE.match(line):
            return True
        if line.lstrip().startswith(">"):
            return True
        if UL_RE.match(line) or OL_RE.match(line):
            return True
        if self._is_html_block_start(line):
            return True
        if "|" in line and i + 1 < len(lines) and self._is_table_sep(lines[i + 1]):
            return True
        return False

    def _consume_html_block(self, lines: list, i: int) -> int:
        n = len(lines)
        first = lines[i].lstrip()
        if first.startswith("<!--"):
            while i < n:
                if "-->" in lines[i]:
                    return i + 1
                i += 1
            return n
        m = re.match(r"<(script|style|textarea|pre)\b", first, re.I)
        if m:
            close = f"</{m.group(1).lower()}"
            while i < n:
                if close in lines[i].lower():
                    return i + 1
                i += 1
            return n
        depth = 0
        while i < n:
            depth += _tag_delta(lines[i])
            i += 1
            if depth <= 0:
                break
        return i

    def _consume_table(self, lines: list, i: int):
        n = len(lines)
        header = self._split_row(lines[i])
        seps = self._split_row(lines[i + 1])
        aligns = []
        for s in seps[: len(header)]:
            left, right = s.startswith(":"), s.endswith(":")
            aligns.append("ctr" if left and right else ("num" if right else ""))
        while len(aligns) < len(header):
            aligns.append("")
        i += 2
        rows = []
        while i < n and lines[i].strip() and "|" in lines[i]:
            rows.append(self._split_row(lines[i]))
            i += 1

        def cell(tag, text, cls):
            c = f' class="{cls}"' if cls else ""
            return f"<{tag}{c}>{self.render_inline(text)}</{tag}>"

        head = "".join(cell("th", t, aligns[k]) for k, t in enumerate(header))
        body_rows = []
        for row in rows:
            cells = "".join(
                cell("td", row[k] if k < len(row) else "", aligns[k] if k < len(aligns) else "")
                for k in range(len(header))
            )
            body_rows.append(f"<tr>{cells}</tr>")
        html_out = (
            '<div class="table-wrap">\n<table>\n'
            f"<thead><tr>{head}</tr></thead>\n<tbody>\n"
            + "\n".join(body_rows)
            + "\n</tbody>\n</table>\n</div>"
        )
        return html_out, i

    def _consume_list(self, lines: list, i: int):
        n = len(lines)
        base_indent = None
        top_type = "ul"
        start_num = 1
        items = []  # {"text": str, "sub_type": str|None, "sub": [str]}

        def new_item(text):
            return {"text": text, "sub_type": None, "sub": []}

        current = None
        while i < n:
            line = lines[i]
            if not line.strip():
                break
            m_ul, m_ol = UL_RE.match(line), OL_RE.match(line)
            if m_ul or m_ol:
                m = m_ul or m_ol
                mtype = "ul" if m_ul else "ol"
                indent = len(m.group(1).expandtabs(4))
                text = m.group(2) if m_ul else m.group(3)
                if base_indent is None:
                    base_indent = indent
                    top_type = mtype
                    if m_ol:
                        start_num = int(m.group(2))
                    current = new_item(text)
                    items.append(current)
                elif indent >= base_indent + 2:
                    if current is None:
                        current = new_item("")
                        items.append(current)
                    if current["sub_type"] is None:
                        current["sub_type"] = mtype
                    current["sub"].append(text)
                else:
                    current = new_item(text)
                    items.append(current)
                i += 1
                continue
            indent = len(line) - len(line.lstrip())
            if current is not None and indent >= base_indent + 2:
                if current["sub"] and current["sub_type"]:
                    current["sub"][-1] += " " + line.strip()
                else:
                    current["text"] += " " + line.strip()
                i += 1
                continue
            break

        attrs = f' start="{start_num}"' if top_type == "ol" and start_num != 1 else ""
        out = [f"<{top_type}{attrs}>"]
        for item in items:
            inner = self.render_inline(item["text"])
            if item["sub"]:
                sub_items = "\n".join(f"<li>{self.render_inline(s)}</li>" for s in item["sub"])
                inner += f'\n<{item["sub_type"]}>\n{sub_items}\n</{item["sub_type"]}>'
            out.append(f"<li>{inner}</li>")
        out.append(f"</{top_type}>")
        return "\n".join(out), i

    def _consume_blockquote(self, lines: list, i: int) -> tuple:
        n = len(lines)
        buf = []
        while i < n and lines[i].lstrip().startswith(">"):
            content = lines[i].lstrip()[1:]
            if content.startswith(">"):
                content = content[1:]
            buf.append(content.rstrip())
            i += 1
        # split into paragraphs on blank ">" lines
        paras, current = [], []
        for line in buf:
            if line.strip():
                current.append(line.strip())
            elif current:
                paras.append(" ".join(current))
                current = []
        if current:
            paras.append(" ".join(current))
        if not paras:
            paras = [""]

        marker = CALLOUT_RE.match(paras[0])
        if marker:
            kind = marker.group(1).lower()
            paras[0] = marker.group(2).strip()
            if not paras[0]:
                paras = paras[1:]
            body = "\n".join(f"<p>{self.render_inline(p)}</p>" for p in paras)
            return (
                f'<blockquote class="callout callout-{kind}">\n'
                f'<p class="callout-label">{kind.capitalize()}</p>\n{body}\n</blockquote>',
                i,
            )
        body = "\n".join(f"<p>{self.render_inline(p)}</p>" for p in paras)
        return f"<blockquote>\n{body}\n</blockquote>", i

    def convert(self, body: str) -> str:
        lines = self._extract_footnote_defs(body.split("\n"))
        n = len(lines)
        out = []
        i = 0
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            fence = FENCE_RE.match(line)
            if fence:
                fence_mark = fence.group(2)
                lang = fence.group(3)
                i += 1
                code_lines = []
                while i < n:
                    closing = FENCE_RE.match(lines[i])
                    if closing and closing.group(2) == fence_mark and not closing.group(3):
                        i += 1
                        break
                    code_lines.append(lines[i])
                    i += 1
                code = html.escape("\n".join(code_lines), quote=False)
                label = (
                    f'<span class="code-lang">{esc(lang)}</span>\n' if lang else ""
                )
                out.append(
                    f'<div class="code-block">\n{label}<pre><code>{code}</code></pre>\n</div>'
                )
                continue

            if HR_RE.match(line):
                out.append("<hr>")
                i += 1
                continue

            heading = HEADING_RE.match(line)
            if heading:
                out.append(self._heading(len(heading.group(1)), heading.group(2).strip()))
                i += 1
                continue

            if line.lstrip().startswith(">"):
                block, i = self._consume_blockquote(lines, i)
                out.append(block)
                continue

            if UL_RE.match(line) or OL_RE.match(line):
                block, i = self._consume_list(lines, i)
                out.append(block)
                continue

            if "|" in line and i + 1 < n and self._is_table_sep(lines[i + 1]):
                block, i = self._consume_table(lines, i)
                out.append(block)
                continue

            kind = self._is_html_block_start(line)
            if kind:
                j = self._consume_html_block(lines, i)
                out.append("\n".join(lines[i:j]))
                i = j
                continue

            # paragraph
            para = [line.strip()]
            i += 1
            while i < n and not self._starts_block(lines, i):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{self.render_inline(chr(10).join(para))}</p>")

        return "\n".join(out)


# --------------------------------------------------------------------------
# Entry model + rendering
# --------------------------------------------------------------------------


@dataclass
class Entry:
    path: Path
    meta: dict
    body: str
    slug: str = ""
    read_minutes: int = 0
    body_html: str = ""
    footnotes_html: str = ""
    roadmap: list = field(default_factory=list)
    headings: list = field(default_factory=list)


def load_entries(content_dir: Path) -> list:
    if not content_dir.is_dir():
        raise BuildError(f"content directory not found: {content_dir}")
    entries, skipped = [], []
    for path in sorted(content_dir.glob("*.md")):
        if path.name.startswith("_"):
            skipped.append((path.name, "name starts with '_'"))
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text, path.name)
        if meta.get("draft"):
            skipped.append((path.name, "draft: true"))
            continue
        if not meta.get("title"):
            raise BuildError(f"{path.name}: frontmatter is missing a required 'title'")
        entries.append(Entry(path=path, meta=meta, body=body))
    entries.sort(key=lambda e: (e.meta.get("date", ""), e.path.name), reverse=True)
    return entries, skipped


def build_roadmap(entry: Entry) -> list:
    h2s = [h for h in entry.headings if h["level"] == 2]
    provided = entry.meta.get("sections") or []
    cards = []
    if provided and len(provided) != len(h2s):
        print(
            f"warning: {entry.path.name}: frontmatter has {len(provided)} section(s) "
            f"but the entry has {len(h2s)} H2 heading(s); matching them in order",
            file=sys.stderr,
        )
    if provided:
        for idx, h2 in enumerate(h2s):
            info = provided[idx] if idx < len(provided) else {"label": h2["text"], "deck": ""}
            cards.append({"href": h2["id"], "label": info["label"], "deck": info.get("deck", "")})
    else:
        for h2 in h2s:
            cards.append({"href": h2["id"], "label": h2["text"], "deck": ""})
    return cards


def render_roadmap(cards: list) -> str:
    if not cards:
        return ""
    links = []
    for idx, card in enumerate(cards, 1):
        deck = f'<span class="rm-deck">{esc(card["deck"])}</span>' if card["deck"] else ""
        links.append(
            f'<a class="rm-card" href="#{esc(card["href"])}">'
            f'<span class="rm-title"><span class="rm-number">{idx}</span>'
            f'<span class="rm-label">{esc(card["label"])}</span></span>'
            f"{deck}</a>"
        )
    return (
        '<nav class="roadmap" aria-label="Entry sections">\n'
        + "\n".join(links)
        + "\n</nav>"
    )


def render_title_block(entry: Entry) -> str:
    meta = entry.meta
    names = [esc(meta.get("author", ""))]
    org = meta.get("org", "")
    if org:
        if meta.get("org_url"):
            names.append(f'<a class="byline-org" href="{esc(meta["org_url"])}">{esc(org)}</a>')
        else:
            names.append(esc(org))
    names_html = ' <span class="sep" aria-hidden="true">&middot;</span> '.join(p for p in names if p)

    status_bits = []
    if meta.get("status"):
        status_bits.append(f'<span class="byline-status-text">{esc(meta["status"])}</span>')
    status_bits.append(f'<span>{entry.read_minutes}-minute read</span>')
    status_bits.append(f'<a href="{esc(entry.slug)}.md">Text version</a>')
    status_bits.append('<a href="../">&uarr; All entries</a>')
    status_html = ' <span class="sep" aria-hidden="true">&middot;</span> '.join(status_bits)

    dek = f'<p class="dek">{esc(meta["dek"])}</p>' if meta.get("dek") else ""
    return (
        '<div class="title-block">\n'
        f"<h1>{esc(meta['title'])}</h1>\n"
        f"{dek}\n"
        '<div class="byline">\n'
        f'<p class="byline-names">{names_html}</p>\n'
        f'<p class="byline-status">{status_html}</p>\n'
        "</div>\n</div>"
    )


def render_shell(*, title: str, description: str, asset_prefix: str, content_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS_HREF}">
<link rel="stylesheet" href="{asset_prefix}/style.css">
<link rel="stylesheet" href="{asset_prefix}/interactive.css">
</head>
<body id="top">
<a class="skip-link" href="#content">Skip to content</a>
<div id="reading-progress" aria-hidden="true"></div>
{content_html}
<script src="{asset_prefix}/footnotes.js" defer></script>
<script src="{asset_prefix}/entry.js" defer></script>
<script src="{asset_prefix}/interactive.js" defer></script>
<script src="{asset_prefix}/data.js" defer></script>
</body>
</html>
"""


def render_entry_page(entry: Entry) -> str:
    masthead = (
        '<header class="masthead">\n'
        f'<a class="identity" href="../">{esc(SITE_TAGLINE)}</a>\n'
        '<nav class="top-links"><a href="../">&uarr; All entries</a></nav>\n'
        "</header>"
    )
    footer = (
        '<footer class="page-footer">\n'
        f'<span>{esc(entry.meta["title"])}</span>\n'
        '<a href="#top">Back to beginning &uarr;</a>\n'
        "</footer>"
    )
    content = (
        f"<main id=\"content\">\n{masthead}\n{render_title_block(entry)}\n"
        f"{render_roadmap(entry.roadmap)}\n"
        f'<article class="entry">\n{entry.body_html}\n</article>\n'
        f"{entry.footnotes_html}\n</main>\n{footer}"
    )
    description = entry.meta.get("dek") or SITE_TAGLINE
    return render_shell(
        title=f"{entry.meta['title']} \u00b7 {SITE_TITLE}",
        description=description,
        asset_prefix="../static",
        content_html=content,
    )


def render_index_page(entries: list) -> str:
    masthead = (
        '<header class="masthead">\n'
        f'<a class="identity" href="./">{esc(SITE_TAGLINE)}</a>\n'
        '<nav class="top-links"><a href="#entries">Entries &darr;</a></nav>\n'
        "</header>"
    )
    if entries:
        cards = []
        for idx, entry in enumerate(entries, 1):
            dek = f'<span class="entry-dek">{esc(entry.meta["dek"])}</span>' if entry.meta.get("dek") else ""
            bits = []
            if entry.meta.get("date"):
                bits.append(esc(entry.meta["date"]))
            bits.append(f"{entry.read_minutes}-minute read")
            if entry.meta.get("author"):
                bits.append(esc(entry.meta["author"]))
            cards.append(
                f'<a class="entry-card" href="./{esc(entry.slug)}/">'
                f'<span class="entry-number">{idx:02d}</span>'
                f'<span class="entry-copy">'
                f'<span class="entry-title">{esc(entry.meta["title"])}</span>'
                f"{dek}"
                f'<span class="entry-meta">{" &middot; ".join(bits)}</span>'
                f"</span></a>"
            )
        listing = '<nav class="entry-list" id="entries" aria-label="Entries">\n' + "\n".join(cards) + "\n</nav>"
    else:
        listing = (
            '<div class="empty-state" id="entries">\n'
            "<p>No entries yet.</p>\n"
            "<p>Write one as <code>blog/content/&lt;slug&gt;.md</code> "
            "(see <code>content/_template.md</code>) and run "
            "<code>python3 blog/build.py</code>.</p>\n</div>"
        )
    title_block = (
        '<div class="title-block index-title">\n'
        f"<h1>{esc(SITE_TITLE)}</h1>\n"
        f'<p class="dek">{esc(SITE_DEK)}</p>\n'
        "</div>"
    )
    footer = (
        '<footer class="page-footer">\n'
        f"<span>{esc(SITE_TAGLINE)}</span>\n"
        '<a href="#top">Back to top &uarr;</a>\n'
        "</footer>"
    )
    content = f'<main id="content">\n{masthead}\n{title_block}\n{listing}\n</main>\n{footer}'
    return render_shell(
        title=SITE_TITLE,
        description=SITE_DEK,
        asset_prefix="./static",
        content_html=content,
    )


# --------------------------------------------------------------------------
# Data page (the benchmark datasets shipped with the site)
# --------------------------------------------------------------------------

# The entry this bundled dataset belongs to (used for the back-link only).
DATA_ENTRY_SLUG = "the-camera-was-never-slow"
DATA_ENTRY_TITLE = "The Camera Was Never Slow"

DATA_ENV_LABELS = {
    "phone": "Galaxy S24 FE \u00b7 Android 16 \u00b7 arm64 release builds",
    "emulator": "pixel_bench AVD \u00b7 API 35 \u00b7 x86_64 \u00b7 SwiftShader",
}
DATA_APP_LABELS = {
    "a1_vanilla": "A1 \u00b7 mobile_scanner, vanilla",
    "a2_warm": "A2 \u00b7 mobile_scanner, controller held",
    "p1_prewarm": "P1 \u00b7 CameraX preview, prewarmed",
    "p2_camera2": "P2 \u00b7 camera2-direct",
    "p3_mlkit": "P3 \u00b7 CameraX + ML Kit",
    "p4_c2_mlkit": "P4 \u00b7 camera2-direct + ML Kit",
}
DATA_FILE_KINDS = ("stages", "events", "summary", "rows")
_DATA_RFID_MARKERS = (
    "rfid_start_result",
    "stop_for_nfc_requested",
    "stop_requested",
    "arbiter_wait_camera",
)
_DATA_SPAN_PRIORITY = {
    "launch": ("fast_ready", "started", "preview_painted", "camera_open"),
    "entry": ("first_frame", "first_analysis_frame", "camera_open", "started"),
    "rfid": ("rfid_start_result",),
}


def cycle_kind(cycle: dict) -> str:
    """Classify one harness cycle: launch prewarm, scan entry, or RFID handoff."""
    keys = set(cycle) - {"tab_tap"}
    if keys & set(_DATA_RFID_MARKERS):
        return "rfid"
    if "controller_created" in keys or (
        "first_frame" not in keys
        and "camera_open" not in keys
        and any(k.startswith("warmup") for k in keys)
    ):
        return "launch"
    return "entry"


def _cycle_span(cycle: dict, kind: str):
    for stage in _DATA_SPAN_PRIORITY[kind]:
        if stage in cycle:
            return cycle[stage]
    return None


def _median_of(values) -> int | None:
    """Median of non-None values; dataset timestamps are microseconds."""
    values = [v for v in values if v is not None]
    return round(statistics.median(values)) if values else None


def _fmt_us(value) -> str:
    """Format a dataset timestamp (microseconds) as ms or s."""
    if value is None:
        return "&mdash;"
    ms = value / 1000.0
    if ms >= 1000:
        return f"{ms / 1000.0:.2f}&nbsp;s"
    return f"{round(ms)}&nbsp;ms"


def load_dataset(data_dir: Path):
    """Load blog/data/: envs with apps, file paths, and raw cycles."""
    env_order = {name: idx for idx, name in enumerate(DATA_ENV_LABELS)}
    envs = []
    total_cycles = 0
    dirs = (p for p in data_dir.iterdir() if p.is_dir())
    for env_dir in sorted(dirs, key=lambda p: (env_order.get(p.name, 99), p.name)):
        apps = []
        for stages_path in sorted(env_dir.glob("*.stages.json")):
            app_id = stages_path.name[: -len(".stages.json")]
            stages = json.loads(stages_path.read_text(encoding="utf-8"))
            trials = stages.get("trials", [])
            files = {}
            for kind in DATA_FILE_KINDS:
                candidate = env_dir / f"{app_id}.{kind}.json"
                files[kind] = (
                    f"{env_dir.name}/{candidate.name}" if candidate.is_file() else None
                )
            apps.append(
                {
                    "id": app_id,
                    "label": DATA_APP_LABELS.get(app_id, app_id),
                    "files": files,
                    "trials": trials,
                }
            )
            total_cycles += len(trials)
        if apps:
            envs.append(
                {
                    "id": env_dir.name,
                    "label": DATA_ENV_LABELS.get(env_dir.name, env_dir.name),
                    "apps": apps,
                }
            )
    return envs, total_cycles


def _render_data_tables(envs: list) -> str:
    blocks = []
    for env in envs:
        rows = []
        for app in env["apps"]:
            by_kind = {"launch": [], "entry": [], "rfid": []}
            for cycle in app["trials"]:
                by_kind[cycle_kind(cycle)].append(cycle)
            launch = _median_of(_cycle_span(c, "launch") for c in by_kind["launch"])
            entry = _median_of(_cycle_span(c, "entry") for c in by_kind["entry"])
            release = _median_of(c.get("camera_released") for c in by_kind["rfid"])
            rfid = _median_of(_cycle_span(c, "rfid") for c in by_kind["rfid"])
            rows.append(
                "<tr>"
                f"<td>{esc(app['label'])}</td>"
                f'<td class="num">{len(app["trials"])}</td>'
                f'<td class="num">{_fmt_us(launch)}</td>'
                f'<td class="num">{_fmt_us(entry)}</td>'
                f'<td class="num">{_fmt_us(release)}</td>'
                f'<td class="num">{_fmt_us(rfid)}</td>'
                "</tr>"
            )
        blocks.append(
            f"<h3>{esc(env['label'])}</h3>\n"
            '<div class="table-wrap"><table>\n<thead><tr>'
            '<th>app</th><th class="num">cycles</th>'
            '<th class="num">launch &rarr; ready</th>'
            '<th class="num" title="first_frame where instrumented; the '
            'mobile_scanner builds only report camera_open completing">'
            "scan entry &rarr; ready</th>"
            '<th class="num">NFC &rarr; camera released</th>'
            '<th class="num">NFC &rarr; RFID started</th>'
            "</tr></thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody></table></div>"
        )
    return "\n".join(blocks)


def _render_data_files(envs: list) -> str:
    blocks = []
    for env in envs:
        items = []
        for app in env["apps"]:
            links = [
                f'<a href="./{esc(rel)}">{kind}</a>'
                for kind in DATA_FILE_KINDS
                if (rel := app["files"][kind])
            ]
            items.append(
                f'<li><span class="dx-file-app">{esc(app["label"])}</span>'
                f'<span class="dx-file-links">{" &middot; ".join(links)}</span></li>'
            )
        blocks.append(
            f"<h3>{esc(env['label'])}</h3>\n"
            '<ul class="dx-files">\n' + "\n".join(items) + "\n</ul>"
        )
    return "\n".join(blocks)


def render_data_page(data_dir: Path) -> str:
    envs, total_cycles = load_dataset(data_dir)
    manifest = {
        "envs": [
            {
                "id": env["id"],
                "label": env["label"],
                "apps": [
                    {
                        "id": app["id"],
                        "label": app["label"],
                        "files": app["files"],
                        "cycles": len(app["trials"]),
                    }
                    for app in env["apps"]
                ],
            }
            for env in envs
        ]
    }
    manifest_json = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")

    masthead = (
        '<header class="masthead">\n'
        f'<a class="identity" href="../">{esc(SITE_TAGLINE)}</a>\n'
        '<nav class="top-links">'
        f'<a href="../{esc(DATA_ENTRY_SLUG)}/">{esc(DATA_ENTRY_TITLE)}</a> '
        '<a href="../">&uarr; All entries</a></nav>\n'
        "</header>"
    )
    title_block = (
        '<div class="title-block">\n'
        "<h1>The data</h1>\n"
        f'<p class="dek">Every cycle behind <em>{esc(DATA_ENTRY_TITLE)}</em> \u2014 '
        "six implementations, two environments, "
        f"{total_cycles} recorded cycles \u2014 reconstructed from the raw "
        "<code>BENCH</code> logs. Pick an environment, an app, and a cycle; "
        "or take the JSON files directly.</p>\n"
        "</div>"
    )

    explorer = (
        '<div id="data-explorer" class="dx">\n'
        '<p class="dx-note">The per-cycle browser needs JavaScript. '
        "Without it, the summary tables and the raw files are still here.</p>\n"
        f"{_render_data_tables(envs)}\n"
        "</div>\n"
        f'<script id="data-manifest" type="application/json">{manifest_json}</script>'
    )

    article = (
        '<article class="entry">\n'
        f"{explorer}\n"
        '<p class="dx-hint">Cell values are medians in ms / s. "scan entry" '
        "uses <code>first_frame</code> where the build instruments one (P apps); "
        "the mobile_scanner builds (A1/A2) only report <code>camera_open</code> "
        "completing \u2014 an ack that says nothing about a visible frame. "
        "Each <code>stages</code> file stores one object per "
        "cycle: stage name \u2192 microseconds since that cycle\u2019s tab tap "
        "(the browser above shows ms / s). "
        "<code>events</code> is the raw timestamped log the harness parsed; "
        "<code>summary</code> is its aggregate and <code>rows</code> (where "
        "present) the host-side screen-visibility sample.</p>\n"
        "<h2>Raw files</h2>\n"
        f"{_render_data_files(envs)}\n"
        "</article>"
    )

    footer = (
        '<footer class="page-footer">\n'
        "<span>The data</span>\n"
        '<a href="#top">Back to top &uarr;</a>\n'
        "</footer>"
    )
    content = f'<main id="content">\n{masthead}\n{title_block}\n{article}\n</main>\n{footer}'
    return render_shell(
        title=f"The data \u00b7 {SITE_TITLE}",
        description=(
            f"Every recorded BENCH cycle behind {DATA_ENTRY_TITLE}: "
            "per-app stage timings and raw event logs."
        ),
        asset_prefix="../static",
        content_html=content,
    )


# --------------------------------------------------------------------------
# Build driver
# --------------------------------------------------------------------------


def build_site(
    content_dir: Path,
    static_dir: Path,
    dist_dir: Path,
    data_dir: Path | None = None,
) -> dict:
    if not static_dir.is_dir():
        raise BuildError(f"static directory not found: {static_dir}")
    entries, skipped = load_entries(content_dir)

    # Convert everything in memory first so errors never leave a half-built dist.
    for entry in entries:
        entry.slug = slugify(entry.meta.get("slug") or entry.meta["title"])
        if not entry.slug:
            raise BuildError(
                f"{entry.path.name}: could not derive a slug from title "
                f"{entry.meta['title']!r}; add a 'slug:' frontmatter key"
            )
        entry.read_minutes = read_time_minutes(entry.body)
        converter = MarkdownConverter()
        entry.body_html = converter.convert(entry.body)
        entry.footnotes_html = converter.footnotes_html()
        entry.headings = converter.headings
        entry.roadmap = build_roadmap(entry)
        for warning in converter.warnings:
            print(f"warning: {entry.path.name}: {warning}", file=sys.stderr)

    slugs = {}
    for entry in entries:
        if entry.slug in slugs:
            raise BuildError(
                f"duplicate slug {entry.slug!r}: {slugs[entry.slug]} and {entry.path.name} "
                f"both build to dist/{entry.slug}/; add distinct 'slug:' keys"
            )
        slugs[entry.slug] = entry.path.name

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    (dist_dir / "index.html").write_text(render_index_page(entries), encoding="utf-8")

    built = []
    for entry in entries:
        out_dir = dist_dir / entry.slug
        out_dir.mkdir(parents=True)
        (out_dir / "index.html").write_text(render_entry_page(entry), encoding="utf-8")
        (out_dir / f"{entry.slug}.md").write_text(
            entry.path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        built.append(out_dir / "index.html")

    shutil.copytree(static_dir, dist_dir / "static")

    # Optional bundled dataset: copied verbatim plus a rendered explorer page.
    data_page = None
    if data_dir is not None and Path(data_dir).is_dir():
        data_dir = Path(data_dir)
        data_out = dist_dir / "data"
        shutil.copytree(data_dir, data_out)
        data_page = data_out / "index.html"
        data_page.write_text(render_data_page(data_dir), encoding="utf-8")

    (dist_dir / ".nojekyll").write_text("", encoding="utf-8")

    return {
        "entries": built,
        "skipped": skipped,
        "index": dist_dir / "index.html",
        "data": data_page,
        "dist": dist_dir,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the static research blog into dist/ (stdlib only)."
    )
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="benchmark dataset directory to publish at dist/data/ (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    try:
        summary = build_site(args.content, args.static, args.dist, data_dir=args.data)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    print(f"blog build ok -> {summary['dist']}")
    if summary["entries"]:
        print(f"entries built ({len(summary['entries'])}):")
        for path in summary["entries"]:
            print(f"  {path}")
    else:
        print("entries built (0): the index shows the empty state")
    print(f"index: {summary['index']}")
    print(f"assets: {summary['dist']}/static/, .nojekyll written")
    if summary["data"]:
        print(f"data: {summary['data']}")
    else:
        print("data: no dataset directory found; explorer page skipped")
    for name, reason in summary["skipped"]:
        print(f"skipped: {name} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
