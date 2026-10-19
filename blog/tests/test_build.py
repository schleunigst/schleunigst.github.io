#!/usr/bin/env python3
"""Tests for blog/build.py -- stdlib-only, run with:

    python3 blog/tests/test_build.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent
FIXTURES = HERE / "fixtures"

_spec = importlib.util.spec_from_file_location("blog_build", BLOG / "build.py")
build = importlib.util.module_from_spec(_spec)
sys.modules["blog_build"] = build
_spec.loader.exec_module(build)


def convert(markdown: str):
    conv = build.MarkdownConverter()
    html = conv.convert(markdown)
    return conv, html


class FrontmatterTests(unittest.TestCase):
    def test_basic_fixture(self):
        text = (FIXTURES / "frontmatter-basic.md").read_text(encoding="utf-8")
        meta, body = build.parse_frontmatter(text, "frontmatter-basic.md")
        self.assertEqual(meta["title"], "A basic entry")
        self.assertEqual(meta["dek"], "Short summary for the card.")
        self.assertEqual(meta["author"], "Ada Example")
        self.assertEqual(meta["org"], "Example Lab")
        self.assertEqual(meta["org_url"], "https://example.com/lab")
        self.assertEqual(meta["status"], "Working notes")
        self.assertEqual(meta["date"], "2026-03-01")
        self.assertNotIn("draft", meta)
        self.assertIn("Body paragraph.", body)

    def test_sections_fixture(self):
        text = (FIXTURES / "frontmatter-sections.md").read_text(encoding="utf-8")
        meta, _ = build.parse_frontmatter(text, "frontmatter-sections.md")
        self.assertEqual(
            meta["sections"],
            [
                {"label": "First part", "deck": "What the first part is about"},
                {"label": "Second part", "deck": "What the second part is about"},
            ],
        )

    def test_draft_flag(self):
        text = (FIXTURES / "frontmatter-draft.md").read_text(encoding="utf-8")
        meta, _ = build.parse_frontmatter(text, "frontmatter-draft.md")
        self.assertTrue(meta["draft"])

    def test_quoted_values_stripped(self):
        meta, body = build.parse_frontmatter(
            '---\ntitle: "Quoted: title"\n---\nhello', "x.md"
        )
        self.assertEqual(meta["title"], "Quoted: title")
        self.assertEqual(body, "hello")

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(build.BuildError):
            build.parse_frontmatter("# Just markdown\n", "x.md")

    def test_missing_closing_fence_raises(self):
        with self.assertRaises(build.BuildError):
            build.parse_frontmatter("---\ntitle: X\nbody without close", "x.md")

    def test_unknown_key_raises(self):
        with self.assertRaises(build.BuildError):
            build.parse_frontmatter("---\ntitle: X\nwibble: 1\n---\n", "x.md")

    def test_inline_sections_value_raises(self):
        with self.assertRaises(build.BuildError):
            build.parse_frontmatter("---\ntitle: X\nsections: A | B\n---\n", "x.md")

    def test_load_entries_skips_drafts_and_underscores(self):
        entries, skipped = build.load_entries(FIXTURES / "site" / "content")
        self.assertEqual([e.path.name for e in entries], ["hello-world.md"])
        reasons = {name: reason for name, reason in skipped}
        self.assertEqual(reasons.get("draft-post.md"), "draft: true")
        self.assertEqual(reasons.get("_hidden.md"), "name starts with '_'")

    def test_missing_title_raises_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "no-title.md").write_text("---\ndek: x\n---\nbody", encoding="utf-8")
            with self.assertRaises(build.BuildError):
                build.load_entries(Path(tmp))


class HelperTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(build.slugify("Hello, World! v2"), "hello-world-v2")
        self.assertEqual(build.slugify("  Spaces  &  Symbols  "), "spaces-symbols")
        self.assertEqual(build.slugify("Ünïcode Title"), "n-code-title")

    def test_read_time(self):
        self.assertEqual(build.read_time_minutes("word " * 200), 1)
        self.assertEqual(build.read_time_minutes("word " * 201), 2)
        self.assertEqual(build.read_time_minutes("word " * 450), 3)
        self.assertEqual(build.read_time_minutes(""), 1)

    def test_read_time_ignores_code_and_links(self):
        body = "```\n" + "word " * 500 + "\n```\n\n[text](https://example.com)\n"
        self.assertEqual(build.read_time_minutes(body), 1)

    def test_strip_inline(self):
        self.assertEqual(build.strip_inline("**Bold** and `code`"), "Bold and code")
        self.assertEqual(build.strip_inline("[label](https://x)"), "label")


class InlineTests(unittest.TestCase):
    def test_emphasis_code_links(self):
        _, html = convert("A **bold** *italic* `code` [link](https://example.com).")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('<a href="https://example.com">link</a>', html)

    def test_image(self):
        _, html = convert("![alt text](assets/pic.png)")
        self.assertIn('<img src="assets/pic.png" alt="alt text" loading="lazy">', html)

    def test_text_is_escaped(self):
        _, html = convert("1 < 2 & 3")
        self.assertIn("1 &lt; 2 &amp; 3", html)

    def test_inline_html_span_passes_through(self):
        _, html = convert('A <span class="metric">2.1x</span> inside **bold**.')
        self.assertIn('<span class="metric">2.1x</span>', html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertTrue(html.startswith("<p>"))

    def test_inline_code_is_escaped(self):
        _, html = convert("Use `<div>` here")
        self.assertIn("<code>&lt;div&gt;</code>", html)


class BlockTests(unittest.TestCase):
    def test_heading_auto_slug(self):
        _, html = convert("## Hello, World!")
        self.assertIn('<h2 id="hello-world">Hello, World!</h2>', html)

    def test_heading_explicit_id(self):
        _, html = convert("### Custom title {#my-anchor}")
        self.assertIn('<h3 id="my-anchor">Custom title</h3>', html)

    def test_heading_duplicate_ids(self):
        _, html = convert("## Same\n\n## Same")
        self.assertIn('id="same"', html)
        self.assertIn('id="same-2"', html)

    def test_horizontal_rule(self):
        _, html = convert("---")
        self.assertIn("<hr>", html)

    def test_nested_bullet_list(self):
        _, html = convert("- top one\n  - nested a\n  - nested b\n- top two")
        self.assertEqual(html.count("<li>"), 4)
        self.assertIn("<li>nested a</li>", html)
        self.assertIn("<ul>\n<li>nested a</li>\n<li>nested b</li>\n</ul>", html)

    def test_ordered_list(self):
        _, html = convert("1. first\n2. second")
        self.assertTrue(html.startswith("<ol>"))
        self.assertIn("<li>second</li>", html)

    def test_ordered_list_start(self):
        _, html = convert("3. third\n4. fourth")
        self.assertIn('<ol start="3">', html)

    def test_blockquote(self):
        _, html = convert("> quoted line one\n> line two")
        self.assertIn("<blockquote>", html)
        self.assertIn("<p>quoted line one line two</p>", html)

    def test_callout(self):
        _, html = convert("> [!WARNING]\n> Watch out.")
        self.assertIn('<blockquote class="callout callout-warning">', html)
        self.assertIn("Watch out.", html)

    def test_fenced_code(self):
        _, html = convert('```python\nprint("hi")\n```')
        self.assertIn('<div class="code-block">', html)
        self.assertIn('<span class="code-lang">python</span>', html)
        self.assertIn('<pre><code>print("hi")</code></pre>', html)

    def test_fenced_code_escapes_html(self):
        _, html = convert('```html\n<div class="x">&</div>\n```')
        self.assertIn('&lt;div class="x"&gt;&amp;&lt;/div&gt;', html)

    def test_table_alignment_classes(self):
        _, html = convert("| Name | Count |\n| --- | ---: |\n| alpha | 12 |")
        self.assertIn('<div class="table-wrap">', html)
        self.assertIn('<th class="num">Count</th>', html)
        self.assertIn('<td class="num">12</td>', html)
        self.assertIn("<td>alpha</td>", html)

    def test_table_center_alignment(self):
        _, html = convert("| A |\n| :---: |\n| x |")
        self.assertIn('<th class="ctr">A</th>', html)

    def test_footnotes(self):
        conv, html = convert("Text[^a] more.\n\n[^a]: Note **body** here.")
        self.assertIn('<span class="fn">', html)
        self.assertIn('class="fn-mark"', html)
        self.assertIn('id="fnref-1"', html)
        self.assertIn('aria-describedby="fnpop-1"', html)
        self.assertIn('role="tooltip" id="fnpop-1"', html)
        self.assertIn("<strong>body</strong>", html)
        self.assertNotIn("[^a]:", html)
        foot = conv.footnotes_html()
        self.assertIn('<li id="fn-1">', foot)
        self.assertIn('class="fn-back"', foot)

    def test_footnote_numbering_by_reference_order(self):
        conv, html = convert("One[^b] two[^a].\n\n[^a]: A\n[^b]: B")
        self.assertIn('aria-label="Footnote 1">[1]</button>', html)
        self.assertLess(html.index('id="fnref-1"'), html.index('id="fnref-2"'))
        self.assertIn('role="tooltip" id="fnpop-1">B', html)
        foot = conv.footnotes_html()
        self.assertLess(foot.index("B"), foot.index("A"))

    def test_missing_footnote_definition_warns(self):
        conv, html = convert("Text[^nope].")
        self.assertIn("[^nope]", html)
        self.assertTrue(any("nope" in w for w in conv.warnings))

    def test_raw_html_block_with_blank_line_and_nesting(self):
        text = (FIXTURES / "raw-html.md").read_text(encoding="utf-8")
        _, body = build.parse_frontmatter(text, "raw-html.md")
        _, html = convert(body)
        start = body.index("<figure")
        end = body.index("</figure>") + len("</figure>")
        block = body[start:end]
        self.assertIn(block, html)
        self.assertIn("<strong>bold</strong>", html)

    def test_no_markdown_processing_inside_raw_html(self):
        _, html = convert("<div>\n**not bold**\n</div>")
        self.assertIn("**not bold**", html)
        self.assertNotIn("<strong>", html)

    def test_opening_paragraph_and_second(self):
        _, html = convert("First para.\n\nSecond para.")
        self.assertEqual(html.count("<p>"), 2)


class IntegrationTests(unittest.TestCase):
    """Full builds against the fixture site and the real static assets."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _build(self, content_dir=None, dist=None, data_dir=None):
        return build.build_site(
            content_dir or (FIXTURES / "site" / "content"),
            BLOG / "static",
            dist or (self.tmp / "dist"),
            data_dir=data_dir,
        )

    def _data_fixture(self):
        """Small dataset shaped like the real blog/data/ tree (timestamps in
        microseconds, all three cycle kinds, one optional rows file)."""
        data = self.tmp / "data"
        phone = data / "phone"
        emulator = data / "emulator"
        phone.mkdir(parents=True)
        emulator.mkdir(parents=True)
        stages = {
            "stages": [
                "warmup_requested",
                "fast_ready",
                "first_frame",
                "camera_released",
                "rfid_start_result",
            ],
            "trials": [
                {"tab_tap": 0, "warmup_requested": 200, "fast_ready": 490000,
                 "scan_page_mounted": 13000},
                {"tab_tap": 0, "stop_for_nfc_requested": 500,
                 "camera_released": 220000, "rfid_start_result": 400000},
                {"tab_tap": 0, "warmup_requested": 180, "camera_open": 35000,
                 "first_frame": 830000},
            ],
        }
        (phone / "p3_mlkit.stages.json").write_text(
            json.dumps(stages), encoding="utf-8"
        )
        (phone / "p3_mlkit.summary.json").write_text(
            json.dumps({"app": "p3_mlkit", "trial_stages": stages["trials"]}),
            encoding="utf-8",
        )
        (emulator / "p3_mlkit.stages.json").write_text(
            json.dumps({"stages": ["first_frame"], "trials": [
                {"tab_tap": 0, "first_frame": 3000000},
            ]}),
            encoding="utf-8",
        )
        (emulator / "p3_mlkit.rows.json").write_text(
            json.dumps({"rows": []}), encoding="utf-8"
        )
        return data

    def test_full_build(self):
        summary = self._build()
        dist = self.tmp / "dist"
        self.assertTrue((dist / "index.html").is_file())
        self.assertTrue((dist / "hello-world" / "index.html").is_file())
        self.assertTrue((dist / ".nojekyll").is_file())
        self.assertTrue((dist / "static" / "style.css").is_file())
        self.assertTrue((dist / "static" / "footnotes.js").is_file())
        self.assertTrue((dist / "static" / "entry.js").is_file())
        self.assertTrue((dist / "static" / "interactive.css").is_file())
        self.assertTrue((dist / "static" / "interactive.js").is_file())
        self.assertTrue((dist / "static" / "data.js").is_file())
        self.assertFalse((dist / "data").exists())
        self.assertIsNone(summary["data"])
        self.assertFalse((dist / "draft-post").exists())
        self.assertFalse((dist / "_hidden").exists())
        self.assertEqual(len(summary["entries"]), 1)

        source = (FIXTURES / "site" / "content" / "hello-world.md").read_text(encoding="utf-8")
        copied = (dist / "hello-world" / "hello-world.md").read_text(encoding="utf-8")
        self.assertEqual(source, copied)

    def test_data_page_builds(self):
        data = self._data_fixture()
        summary = self._build(data_dir=data)
        dist = self.tmp / "dist"
        self.assertEqual(summary["data"], dist / "data" / "index.html")
        self.assertTrue(summary["data"].is_file())
        copied = (dist / "data" / "phone" / "p3_mlkit.stages.json").read_bytes()
        self.assertEqual(
            copied, (data / "phone" / "p3_mlkit.stages.json").read_bytes()
        )
        page = summary["data"].read_text(encoding="utf-8")
        self.assertIn('src="../static/data.js"', page)
        self.assertIn('id="data-manifest"', page)
        self.assertIn("<h2>Raw files</h2>", page)
        self.assertIn('href="./phone/p3_mlkit.stages.json"', page)
        self.assertIn('href="./emulator/p3_mlkit.rows.json"', page)
        # Server-rendered fallback medians (microseconds formatted as ms / s).
        self.assertIn("490&nbsp;ms", page)
        self.assertIn("830&nbsp;ms", page)
        self.assertIn("220&nbsp;ms", page)
        self.assertIn("400&nbsp;ms", page)
        manifest = json.loads(
            re.search(
                r'<script id="data-manifest" type="application/json">(.*?)</script>',
                page,
                re.S,
            ).group(1)
        )
        envs = manifest["envs"]
        self.assertEqual([env["id"] for env in envs], ["phone", "emulator"])
        self.assertIn("Galaxy S24 FE", envs[0]["label"])
        app = envs[0]["apps"][0]
        self.assertEqual(app["label"], "P3 \u00b7 CameraX + ML Kit")
        self.assertEqual(app["cycles"], 3)
        self.assertIsNone(app["files"]["events"])
        self.assertIsNone(app["files"]["rows"])
        self.assertEqual(
            envs[1]["apps"][0]["files"]["rows"], "emulator/p3_mlkit.rows.json"
        )

    def test_data_page_absent_without_data_dir(self):
        summary = self._build()
        self.assertIsNone(summary["data"])
        self.assertFalse((self.tmp / "dist" / "data").exists())
        summary = self._build(data_dir=self.tmp / "missing", dist=self.tmp / "dist2")
        self.assertIsNone(summary["data"])
        self.assertFalse((self.tmp / "dist2" / "data").exists())

    def test_entry_page_contents(self):
        self._build()
        page = (self.tmp / "dist" / "hello-world" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<h1>Hello, World</h1>", page)
        self.assertIn("The first integration fixture entry.", page)
        self.assertIn("Ada Example", page)
        self.assertIn('<a class="byline-org" href="https://example.com/lab">Example Lab</a>', page)
        self.assertIn("Working notes", page)
        self.assertIn("minute read", page)
        self.assertIn('<a href="hello-world.md">Text version</a>', page)
        self.assertIn("&uarr; All entries", page)
        # roadmap from frontmatter sections
        self.assertIn('href="#opening-moves"', page)
        self.assertIn('href="#closing-moves"', page)
        self.assertIn("Opening moves", page)
        self.assertIn("The first theme of this test entry", page)
        # footnotes
        self.assertIn('class="fn-mark"', page)
        self.assertIn('<li id="fn-1">', page)
        # table and code
        self.assertIn('<div class="table-wrap">', page)
        self.assertIn("<code>raw code block</code>", page)
        # relative assets only
        self.assertIn('href="../static/style.css"', page)
        self.assertIn('src="../static/footnotes.js"', page)
        self.assertIn('href="../static/interactive.css"', page)
        self.assertIn('src="../static/interactive.js"', page)

    def test_raw_html_block_passthrough_in_page(self):
        self._build()
        source = (FIXTURES / "site" / "content" / "hello-world.md").read_text(encoding="utf-8")
        page = (self.tmp / "dist" / "hello-world" / "index.html").read_text(encoding="utf-8")
        start = source.index("<figure")
        end = source.index("</figure>") + len("</figure>")
        self.assertIn(source[start:end], page)

    def test_index_page_contents(self):
        self._build()
        index = (self.tmp / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Hello, World", index)
        self.assertIn("The first integration fixture entry.", index)
        self.assertIn('href="./hello-world/"', index)
        self.assertIn("minute read", index)
        self.assertNotIn("Draft post that must not build", index)
        self.assertIn('href="./static/style.css"', index)
        self.assertIn("Notes on making Android cameras instant", index)

    def test_index_newest_first(self):
        content = self.tmp / "content"
        shutil.copytree(FIXTURES / "site" / "content", content)
        (content / "newer.md").write_text(
            "---\ntitle: Newer entry\ndate: 2026-06-01\n---\n\nBody.\n", encoding="utf-8"
        )
        self._build(content_dir=content, dist=self.tmp / "dist")
        index = (self.tmp / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertLess(index.index("Newer entry"), index.index("Hello, World"))

    def test_empty_content_state(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        summary = self._build(content_dir=empty, dist=self.tmp / "dist")
        self.assertEqual(summary["entries"], [])
        index = (self.tmp / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertIn("No entries yet.", index)

    def test_duplicate_slugs_fail(self):
        content = self.tmp / "dup"
        content.mkdir()
        (content / "a.md").write_text("---\ntitle: Same\n---\nA\n", encoding="utf-8")
        (content / "b.md").write_text("---\ntitle: Same\n---\nB\n", encoding="utf-8")
        with self.assertRaises(build.BuildError):
            self._build(content_dir=content, dist=self.tmp / "dist")

    def test_generated_html_parses_and_links_are_relative(self):
        self._build(data_dir=self._data_fixture())
        pages = sorted((self.tmp / "dist").rglob("*.html"))
        self.assertGreaterEqual(len(pages), 3)
        link_re = re.compile(r'(?:href|src)="([^"]+)"')
        for page in pages:
            text = page.read_text(encoding="utf-8")
            parser = HTMLParser(convert_charrefs=True)
            parser.feed(text)
            parser.close()
            self.assertIn("</html>", text)
            for url in link_re.findall(text):
                if url.startswith(("http://", "https://", "#", "mailto:", "data:")):
                    continue
                self.assertFalse(url.startswith("/"), f"absolute path in {page}: {url}")
                self.assertNotIn("file://", url, f"file URL in {page}: {url}")

    def test_sample_draft_converts(self):
        sample = BLOG / "content" / "_sample.md"
        meta, body = build.parse_frontmatter(sample.read_text(encoding="utf-8"), "_sample.md")
        self.assertTrue(meta["draft"])
        conv = build.MarkdownConverter()
        html = conv.convert(body)
        self.assertIn('class="fn-mark"', html)
        self.assertIn('class="event-strip"', html)
        self.assertIn('class="fig-keep"', html)
        self.assertIn('<div class="table-wrap">', html)
        self.assertIn('<blockquote class="callout callout-note">', html)

    def test_real_content_dir_builds(self):
        """The shipped content/ builds: every published entry appears, every
        `_`-prefixed file and `draft: true` entry is skipped, pages parse."""
        content = BLOG / "content"
        expected = []
        for path in sorted(content.glob("*.md")):
            if path.name.startswith("_"):
                continue
            meta, _ = build.parse_frontmatter(path.read_text(encoding="utf-8"), path.name)
            if not meta.get("draft"):
                expected.append(path.stem)
        summary = self._build(
            content_dir=content, dist=self.tmp / "dist", data_dir=BLOG / "data"
        )
        built = sorted(p.parent.name for p in summary["entries"])
        self.assertEqual(built, sorted(expected))
        self.assertTrue((self.tmp / "dist" / "data" / "index.html").is_file())
        self.assertTrue(
            (self.tmp / "dist" / "data" / "phone" / "p3_mlkit.stages.json").is_file()
        )
        index = (self.tmp / "dist" / "index.html").read_text(encoding="utf-8")
        if expected:
            self.assertNotIn("No entries yet.", index)
            for slug in expected:
                self.assertTrue((self.tmp / "dist" / slug / "index.html").is_file())
                page = (self.tmp / "dist" / slug / "index.html").read_text(encoding="utf-8")
                parser = HTMLParser(convert_charrefs=True)
                parser.feed(page)
                parser.close()
        else:
            self.assertIn("No entries yet.", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
