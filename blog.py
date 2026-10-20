#!/usr/bin/env python3
"""
Scaffold and build the blog under /blog/.

    python3 blog.py new "Why streaks reset"     # new draft at blog/why-streaks-reset/
    python3 blog.py new "Title" --slug short     # choose the URL yourself
    python3 blog.py publish why-streaks-reset    # un-draft, date it today, build
    python3 blog.py build                        # re-sync everything after edits

── How a post is laid out ────────────────────────────────────

Each post is one hand-editable file, blog/<slug>/index.html, served at
https://brahmi.site/blog/<slug>/. At the top of its <head> sits

    <script type="application/json" id="post-meta"> {...} </script>

which is the source of truth for the post's title, description, dates,
category, author and image. `build` regenerates everything derived from it:

  - the <!-- blog:head --> block   (title, meta, canonical, OG, JSON-LD)
  - the <!-- blog:header --> block (eyebrow, h1, date line)
  - the card list + schema in blog/index.html
  - the <!-- blog:urls --> region of sitemap.xml

So: change the title in post-meta, not in the <h1>. The body between the
<!-- blog:body --> markers is yours and is never touched.

Drafts ("draft": true) are built with noindex and left out of the list and
the sitemap, so a half-written post can be pushed without being indexed.

Same rules as bake.py: stdlib only, and all text from post-meta is inserted
escaped.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

SITE = "https://brahmi.site"
BLOG_DIR = "blog"
INDEX = os.path.join(BLOG_DIR, "index.html")
SITEMAP = "sitemap.xml"
DEFAULT_IMAGE = "/assets/logo.webp"
PLAY_URL = "https://play.google.com/store/apps/details?id=com.brahmi.app"
WORDS_PER_MINUTE = 200

e = html.escape


# ── Helpers ────────────────────────────────────────────────

def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)[:70].rstrip("-")


def today():
    return datetime.date.today().isoformat()


def human_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def json_ld(obj):
    # Escaped so a "</script>" inside any string cannot close the tag early.
    return json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")


def replace_marked(src, name, content, path):
    """Swap the text between <!-- name --> and <!-- /name -->."""
    pattern = re.compile(rf"(<!-- {name}\b[^>]*-->)(.*?)(\n[ \t]*<!-- /{name} -->)", re.S)
    if not pattern.search(src):
        raise SystemExit(f"blog: {path} is missing its <!-- {name} --> markers")
    body = f"\n{content}" if content else ""
    return pattern.sub(lambda m: f"{m.group(1)}{body}{m.group(3)}", src, count=1)


def read_meta(src, path):
    m = re.search(r'<script[^>]*id="post-meta"[^>]*>(.*?)</script>', src, re.S)
    if not m:
        raise SystemExit(f"blog: {path} has no post-meta block")
    meta = json.loads(m.group(1))
    for field in ("title", "description"):
        if not meta.get(field):
            raise SystemExit(f"blog: {path} post-meta needs a {field!r}")
    return meta


def write_meta(src, meta):
    payload = json_ld(meta)
    return re.sub(
        r'(<script[^>]*id="post-meta"[^>]*>)(.*?)(</script>)',
        lambda m: f"{m.group(1)}\n{payload}\n  {m.group(3)}",
        src, count=1, flags=re.S,
    )


def reading_minutes(src):
    m = re.search(r"<!-- blog:body -->(.*?)<!-- /blog:body -->", src, re.S)
    text = re.sub(r"<!--.*?-->|<[^>]+>", " ", m.group(1) if m else "", flags=re.S)
    return max(1, round(len(text.split()) / WORDS_PER_MINUTE))


def absolute(url):
    return url if url.startswith("http") else SITE + url


def author_node(meta):
    if meta.get("author"):
        node = {"@type": "Person", "name": meta["author"]}
        if meta.get("author_url"):
            node["url"] = meta["author_url"]
        return node
    return {"@type": "Organization", "name": "Brahmi", "url": SITE + "/"}


# ── Rendering ──────────────────────────────────────────────

def render_head(slug, meta):
    url = f"{SITE}/blog/{slug}/"
    image = absolute(meta.get("image") or DEFAULT_IMAGE)
    published = meta.get("published") or today()
    updated = meta.get("updated") or published
    title, desc = meta["title"], meta["description"]

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": url + "#post",
                "headline": title,
                "description": desc,
                "image": image,
                "datePublished": published,
                "dateModified": updated,
                "author": author_node(meta),
                "publisher": {
                    "@type": "Organization",
                    "name": "Brahmi",
                    "url": SITE + "/",
                    "logo": {"@type": "ImageObject", "url": SITE + DEFAULT_IMAGE},
                },
                "mainEntityOfPage": url,
                "inLanguage": "en",
                **({"articleSection": meta["category"]} if meta.get("category") else {}),
                **({"keywords": ", ".join(meta["keywords"])} if meta.get("keywords") else {}),
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": url},
                ],
            },
        ],
    }

    lines = [
        f"  <title>{e(title)} — Brahmi</title>",
        f'  <meta name="description" content="{e(desc)}" />',
        f'  <link rel="canonical" href="{url}" />',
    ]
    if meta.get("draft"):
        lines.append('  <meta name="robots" content="noindex" />')
    lines += [
        '  <meta property="og:type" content="article" />',
        f'  <meta property="og:title" content="{e(title)}" />',
        f'  <meta property="og:description" content="{e(desc)}" />',
        f'  <meta property="og:url" content="{url}" />',
        f'  <meta property="og:image" content="{e(image)}" />',
        '  <meta property="og:site_name" content="Brahmi" />',
        f'  <meta property="article:published_time" content="{published}" />',
        f'  <meta property="article:modified_time" content="{updated}" />',
        f'  <meta name="twitter:card" content="{"summary_large_image" if meta.get("image") else "summary"}" />',
        f'  <script type="application/ld+json">\n{json_ld(schema)}\n  </script>',
    ]
    return "\n".join(lines)


def render_header(meta, minutes):
    published = meta.get("published") or today()
    updated = meta.get("updated")
    byline = meta.get("author") or "Brahmi"
    date_line = f'<time datetime="{published}">{human_date(published)}</time>'
    if updated and updated != published:
        date_line += f' &middot; Updated <time datetime="{updated}">{human_date(updated)}</time>'
    out = []
    if meta.get("category"):
        out.append(f'        <p class="eyebrow">{e(meta["category"])}</p>')
    out.append(f'        <h1>{e(meta["title"])}</h1>')
    out.append(f'        <p class="post-dateline">{date_line} &middot; {minutes} min read &middot; By {e(byline)}</p>')
    return "\n".join(out)


def render_card(slug, meta, minutes):
    published = meta["published"]
    eyebrow = f'<p class="eyebrow">{e(meta["category"])}</p>\n' if meta.get("category") else ""
    return (
        f'      <li class="post-card">\n'
        f'        <a href="/blog/{slug}/">\n'
        f'          {eyebrow}'
        f'          <h2>{e(meta["title"])}</h2>\n'
        f'          <p>{e(meta["description"])}</p>\n'
        f'          <p class="post-dateline"><time datetime="{published}">{human_date(published)}</time>'
        f' &middot; {minutes} min read</p>\n'
        f'        </a>\n'
        f'      </li>'
    )


def render_index_schema(posts):
    schema = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "@id": SITE + "/blog/#blog",
        "name": "Brahmi Blog",
        "url": SITE + "/blog/",
        "publisher": {"@type": "Organization", "name": "Brahmi", "url": SITE + "/"},
        "blogPost": [
            {
                "@type": "BlogPosting",
                "headline": meta["title"],
                "url": f"{SITE}/blog/{slug}/",
                "datePublished": meta["published"],
            }
            for slug, meta, _ in posts
        ],
    }
    return f'  <script type="application/ld+json">\n{json_ld(schema)}\n  </script>'


def render_sitemap(posts):
    if not posts:
        return ""
    newest = max(m.get("updated") or m["published"] for _, m, _ in posts)
    entries = [("/blog/", newest, "weekly", "0.7")]
    entries += [
        (f"/blog/{slug}/", meta.get("updated") or meta["published"], "monthly", "0.6")
        for slug, meta, _ in posts
    ]
    return "\n".join(
        f"  <url>\n    <loc>{SITE}{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for loc, lastmod, freq, prio in entries
    )


# ── Commands ───────────────────────────────────────────────

def post_path(slug):
    return os.path.join(BLOG_DIR, slug, "index.html")


def all_slugs():
    return sorted(
        d for d in os.listdir(BLOG_DIR)
        if os.path.isfile(post_path(d))
    )


def build():
    published = []
    for slug in all_slugs():
        path = post_path(slug)
        src = open(path, encoding="utf-8").read()
        meta = read_meta(src, path)
        minutes = reading_minutes(src)
        src = replace_marked(src, "blog:head", render_head(slug, meta), path)
        src = replace_marked(src, "blog:header", render_header(meta, minutes), path)
        open(path, "w", encoding="utf-8").write(src)
        state = "draft" if meta.get("draft") else meta.get("published")
        print(f"  blog/{slug}/  ({state})")
        if not meta.get("draft"):
            if not meta.get("published"):
                raise SystemExit(f"blog: {path} is not a draft but has no 'published' date")
            published.append((slug, meta, minutes))

    published.sort(key=lambda p: p[1]["published"], reverse=True)

    src = open(INDEX, encoding="utf-8").read()
    cards = "\n".join(render_card(*p) for p in published) or (
        '      <li class="post-empty">The first posts are on their way.</li>'
    )
    src = replace_marked(src, "blog:list", cards, INDEX)
    src = replace_marked(src, "blog:schema", render_index_schema(published), INDEX)
    open(INDEX, "w", encoding="utf-8").write(src)

    src = open(SITEMAP, encoding="utf-8").read()
    src = replace_marked(src, "blog:urls", render_sitemap(published), SITEMAP)
    open(SITEMAP, "w", encoding="utf-8").write(src)

    print(f"Built {len(published)} published post(s). Commit and push to deploy.")


def new(title, slug, category):
    slug = slug or slugify(title)
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit(f"blog: bad slug {slug!r}; use lowercase words joined by hyphens")
    path = post_path(slug)
    if os.path.exists(path):
        raise SystemExit(f"blog: {path} already exists")

    meta = {
        "title": title,
        "description": "One or two sentences, 140–160 characters, shown in search results and on the blog card.",
        "category": category,
        "keywords": [],
        "author": "",
        "image": "",
        "published": "",
        "updated": "",
        "draft": True,
    }
    os.makedirs(os.path.dirname(path))
    open(path, "w", encoding="utf-8").write(POST_SKELETON.replace("{{META}}", json_ld(meta)))
    print(f"Created {path}")
    build()


def publish(slug):
    path = post_path(slug)
    if not os.path.exists(path):
        raise SystemExit(f"blog: no post at {path}")
    src = open(path, encoding="utf-8").read()
    meta = read_meta(src, path)
    if "One or two sentences" in meta["description"]:
        raise SystemExit("blog: write a real description in post-meta before publishing")
    meta["draft"] = False
    meta["published"] = meta.get("published") or today()
    open(path, "w", encoding="utf-8").write(write_meta(src, meta))
    build()


def main():
    p = argparse.ArgumentParser(description="Brahmi blog scaffolder")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create a draft post")
    n.add_argument("title")
    n.add_argument("--slug")
    n.add_argument("--category", default="Brahmacharya")
    pub = sub.add_parser("publish", help="un-draft a post and date it today")
    pub.add_argument("slug")
    sub.add_parser("build", help="regenerate head/header/list/sitemap from post-meta")
    args = p.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if args.cmd == "new":
        new(args.title, args.slug, args.category)
    elif args.cmd == "publish":
        publish(args.slug)
    else:
        build()


# ── New-post skeleton ──────────────────────────────────────
#
# Copied once per post by `new`; after that each post's file is its own.
# Paths are root-relative because posts live two directories deep.

POST_SKELETON = """<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Source of truth for this post. Edit here, then: python3 blog.py build -->
  <script type="application/json" id="post-meta">
{{META}}
  </script>
  <!-- blog:head (generated by blog.py from post-meta; edits here are overwritten) -->
  <!-- /blog:head -->
  <link rel="icon" type="image/png" href="/assets/logo.webp" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700&family=Space+Grotesk:wght@700&display=swap"
    rel="stylesheet" />
  <meta name="theme-color" content="#FFF8F7" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#141010" media="(prefers-color-scheme: dark)" />
  <link rel="stylesheet" href="/style.css" />
  <!-- Apply the saved theme before first paint. Toggle lives in script.js. -->
  <script>try { var t = localStorage.getItem('brahmi-theme'); if (t) document.documentElement.setAttribute('data-theme', t); } catch (e) { }</script>
</head>

<body>

  <!-- ── Navbar ─────────────────────────────────────────── -->
  <header class="navbar">
    <nav class="nav-inner">
      <a class="brand" href="/">
        <img src="/assets/logo-192.webp" alt="Brahmi app icon" class="brand-icon" />
        <span class="brand-name">Brahmi</span>
      </a>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="nav-menu">
        <span></span><span></span><span></span>
      </button>
      <div class="nav-menu" id="nav-menu">
        <a href="/#features">Features</a>
        <a href="/#journey">The journey</a>
        <a href="/#practices">Practices</a>
        <a href="/#how-it-works">How it works</a>
        <a href="/#faq">FAQ</a>
        <a href="/blog/">Blog</a>
        <a href="/privacy.html">Privacy</a>
        <a href="mailto:codentas@gmail.com">Contact</a>
        <a href="/#get" class="btn btn-primary nav-cta">Get the app</a>
      </div>
    </nav>
  </header>

  <main class="post-main">
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <a href="/">Home</a> <span aria-hidden="true">/</span> <a href="/blog/">Blog</a>
    </nav>

    <article class="post">
      <header class="post-header">
        <!-- blog:header (generated by blog.py from post-meta) -->
        <!-- /blog:header -->
      </header>

      <div class="post-body">
        <!-- blog:body -->
        <!--
          Write the post here, in plain HTML. Structure that ranks and reads well:
            - Open with 2–3 sentences that answer the title's question directly.
            - <h2> for each main section, <h3> under it. Never a second <h1>.
            - Short paragraphs; <ul>/<ol> for steps; <blockquote> for scripture.
            - Images: <figure><img src="/assets/blog/<slug>.webp" alt="…" width="…" height="…" loading="lazy" /><figcaption>…</figcaption></figure>
            - Link 1–2 related posts with /blog/<slug>/ and, where it fits, the homepage.
            - Health claims: cite a source or soften them. The footer disclaimer covers the rest.
        -->
        <p class="post-lede">Lead paragraph: answer the reader's question in two or three sentences.</p>

        <h2>First section</h2>
        <p>Body text.</p>

        <h2>Second section</h2>
        <p>Body text.</p>

        <h2>Key takeaways</h2>
        <ul>
          <li>Point one.</li>
          <li>Point two.</li>
        </ul>
        <!-- /blog:body -->
      </div>

      <aside class="post-cta">
        <h2>Build the practice, one day at a time</h2>
        <p>Brahmi gives you an honest streak tracker, daily check-ins and guided pranayama, rooted in the gurukul tradition.</p>
        <a href="%(play)s" class="btn btn-primary">Get Brahmi on Google Play</a>
      </aside>
    </article>

    <p class="post-back"><a href="/blog/">&larr; All posts</a></p>
  </main>

  <!-- ── Footer ─────────────────────────────────────────── -->
  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <img src="/assets/logo-192.webp" alt="Brahmi" class="footer-icon" />
        <span>Brahmi</span>
      </div>
      <nav class="footer-links">
        <a href="/#features">Features</a>
        <a href="/#faq">FAQ</a>
        <a href="/blog/">Blog</a>
        <a href="/privacy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
        <a href="/delete-account.html">Delete account</a>
        <a href="mailto:codentas@gmail.com">Contact us</a>
      </nav>
      <p class="footer-disclaimer">
        Brahmi is an educational and self-improvement app, not a medical service.
        Its content is for general wellness and informational purposes only and is
        not medical, psychological, or professional advice, diagnosis, or treatment.
        Individual experiences vary. If you are struggling with compulsive behaviour,
        distress, or any health concern, please consult a qualified professional.
      </p>
      <p class="footer-copy">&copy; 2026 Brahmi. All rights reserved. &middot; For all ages</p>
    </div>
  </footer>

  <script src="/script.js"></script>
</body>

</html>
""".replace("%(play)s", PLAY_URL)


if __name__ == "__main__":
    main()
