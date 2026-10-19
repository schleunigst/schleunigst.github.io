# schleunigst.github.io

Source for the Schleunigst blog: field notes on making Android cameras
instant, priced in milliseconds and milliamps.

- `content/` — the entries (markdown with frontmatter)
- `build.py` — the static generator (stdlib Python)
- `data/` — the raw measurement traces the entries cite
- `tests/`, `tools/` — the generator's own checks

Built by CI on every push (`.github/workflows/deploy-blog.yml`) and served
by GitHub Pages at https://schleunigst.github.io.
