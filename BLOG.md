# Writing and publishing a blog post

Posts live at `https://brahmi.site/blog/<slug>/`. You need Python 3, nothing else.

## 1. Start a draft

```bash
git pull
python3 blog.py new "What is brahmacharya, really?"
# optional: --slug short-url  --category "Pranayama"
```

This creates `blog/what-is-brahmacharya-really/index.html`. Drafts are safe to
push: they are `noindex`, not listed on `/blog/`, and not in the sitemap.

## 2. Fill in the metadata

At the top of the new file is a `post-meta` JSON block. It is the source of
truth for everything about the post, so edit it here and nowhere else:

| Field | What to put |
|---|---|
| `title` | The headline. Also becomes the `<h1>` and the page title. |
| `description` | 140–160 characters. Shown in Google results and on the blog card. |
| `category` | Short label, e.g. `Brahmacharya`, `Pranayama`, `Streaks`. |
| `keywords` | e.g. `["brahmacharya", "nofap benefits"]`. Optional. |
| `author` | A real person's name. Leave empty to credit "Brahmi". |
| `author_url` | Optional link to that person's profile. |
| `image` | e.g. `/assets/blog/<slug>.webp` (1200×630 works best). Optional. |
| `published` | Leave empty; `publish` fills it in. |
| `updated` | Set to today's date (`YYYY-MM-DD`) when you meaningfully revise a post. |
| `draft` | Leave `true`; `publish` flips it. |

## 3. Write the body

Write plain HTML between `<!-- blog:body -->` and `<!-- /blog:body -->`.
Nothing outside those markers needs touching.

- Open with a `<p class="post-lede">` that answers the title in 2–3 sentences.
- Use `<h2>` for sections and `<h3>` under them. Never a second `<h1>`.
- Keep paragraphs short. Use `<ul>`/`<ol>` for steps and `<blockquote>` for quotes or scripture.
- Images: `<figure><img src="/assets/blog/<slug>.webp" alt="…" width="…" height="…" loading="lazy" /><figcaption>…</figcaption></figure>`
- Link to one or two other posts (`/blog/<slug>/`).
- Back up health claims with a source, or soften them.

Preview locally:

```bash
python3 blog.py build
python3 -m http.server 8000     # open http://localhost:8000/blog/<slug>/
```

## 4. Publish

```bash
python3 blog.py publish what-is-brahmacharya-really
git add -A && git commit -m "Blog: What is brahmacharya, really?" && git push
```

`publish` dates the post today and runs `build`, which adds it to `/blog/` and
`sitemap.xml`. The site is live a minute or two after the push. To get it
indexed faster, paste the URL into Search Console → URL Inspection → Request
indexing.

## Editing later

Change the body or `post-meta`, set `updated` if it's a real revision, then
`python3 blog.py build`, commit and push. To unpublish, set `"draft": true`
and build.
