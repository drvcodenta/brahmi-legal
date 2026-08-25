#!/usr/bin/env python3
"""
Bake the live legal documents from Supabase into privacy.html / terms.html.

    python3 bake.py            # sync both pages
    python3 bake.py privacy    # just one

── Why this exists ───────────────────────────────────────────

`legal.js` re-fetches these documents from Supabase on load, which makes it
tempting to think editing the database is enough. It is not. Each page carries
TWO baked copies of the same document:

  1. <script id="legal-data">  — the JSON legal.js compares against
  2. <article id="legal-article"> — the rendered HTML

Both are what a reader sees before (or without) JavaScript: with JS disabled,
offline, on a slow connection, or — the one that actually matters — when a
crawler that does not execute JS reads the page. Google Play's policy URL is
exactly such a reader, so a privacy policy that only becomes accurate after a
fetch is, for compliance purposes, not accurate.

Editing the database and stopping there silently leaves the static copy stale.
That happened once already: `app_opens` was disclosed in the database while
these pages still showed the previous version.

So: edit the database (the shared source of truth with the mobile app), then
run this, then commit and push.

Stdlib only — no install step, so there is no reason to skip it.
"""

import html
import json
import re
import sys
import urllib.request

SUPABASE_URL = "https://vhaxfnquauzoqnuemyfo.supabase.co"
# The publishable (anon) key, same one legal.js ships. legal_documents is
# public-read by design; this grants nothing that the page does not already.
SUPABASE_KEY = "sb_publishable_viW7Dx53I0Mc4H1drYb9VA_sOCwytCn"

PAGES = {"privacy": "privacy.html", "terms": "terms.html"}

FIELDS = "key,title,eyebrow,last_updated,intro,blocks,disclaimer"


def fetch(key):
    url = f"{SUPABASE_URL}/rest/v1/legal_documents?key=eq.{key}&select={FIELDS}"
    req = urllib.request.Request(url, headers={"apikey": SUPABASE_KEY})
    with urllib.request.urlopen(req, timeout=20) as r:
        rows = json.load(r)
    if not rows:
        raise SystemExit(f"bake: no legal_documents row for key={key!r}")
    return rows[0]


def e(text):
    """Escape for HTML text content. Everything from the DB goes through this."""
    return html.escape(text or "", quote=False)


def render_article(doc):
    """Mirror of render() in legal.js — the two must produce the same DOM.

    If you change the markup here, change it there as well, or the page will
    visibly reflow the moment the fetch lands.
    """
    out = [
        f'<p class="eyebrow">{e(doc.get("eyebrow"))}</p>',
        f'<h1>{e(doc.get("title"))}</h1>',
        f'<p class="legal-updated">{e(doc.get("last_updated"))}</p>',
        f'<p class="legal-intro">{e(doc.get("intro"))}</p>',
    ]
    for block in doc.get("blocks") or []:
        if block.get("heading"):
            out.append(f'<h2>{e(block["heading"])}</h2>')
        for p in block.get("paragraphs") or []:
            out.append(f"<p>{e(p)}</p>")
        bullets = block.get("bullets") or []
        if bullets:
            items = "".join(f"<li>{e(b)}</li>" for b in bullets)
            out.append(f"<ul>{items}</ul>")
        if block.get("quote"):
            out.append(f'<blockquote>{e(block["quote"])}</blockquote>')
    out.append(f'<p class="legal-disclaimer">{e(doc.get("disclaimer"))}</p>')
    return "\n      ".join(out)


def replace_block(source, pattern, replacement, what, path):
    new, n = re.subn(pattern, lambda _: replacement, source, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"bake: could not find {what} in {path}")
    return new


def bake(key):
    path = PAGES[key]
    doc = fetch(key)
    src = open(path, encoding="utf-8").read()

    # 1. The JSON legal.js diffs against. Escaped so a "</script>" inside any
    #    string cannot close the tag early.
    payload = json.dumps(doc, ensure_ascii=False, indent=2).replace("</", "<\\/")
    src = replace_block(
        src,
        r'(<script[^>]*id="legal-data"[^>]*>)(.*?)(</script>)',
        f'<script id="legal-data" type="application/json">\n{payload}\n    </script>',
        "the legal-data script block",
        path,
    )

    # 2. The rendered HTML a non-JS reader gets.
    src = replace_block(
        src,
        r'(<article[^>]*id="legal-article"[^>]*>)(.*?)(</article>)',
        f'<article id="legal-article">\n      {render_article(doc)}\n    </article>',
        "the legal-article block",
        path,
    )

    open(path, "w", encoding="utf-8").write(src)
    print(f"  {path:14s} ← {doc.get('last_updated')}")


def main():
    keys = sys.argv[1:] or list(PAGES)
    unknown = [k for k in keys if k not in PAGES]
    if unknown:
        raise SystemExit(f"bake: unknown page(s) {unknown}; expected {list(PAGES)}")
    print("Baking legal documents from Supabase…")
    for k in keys:
        bake(k)
    print("Done. Commit and push to deploy.")


if __name__ == "__main__":
    main()
