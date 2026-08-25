# CLAUDE.md

Guidance for Claude Code working in this repo (`drvcodenta/brahmi-legal`).

This is the **public** site for the Brahmi app: marketing page, privacy
policy, terms, and the account-deletion page Google Play requires. Served by
GitHub Pages from `main` (hence `.nojekyll`). The app itself lives in a
separate, private repo.

## The one thing to get right

**The legal pages are NOT simply rendered from Supabase at runtime.**

`public.legal_documents` in Supabase is the source of truth for the *content*
of `privacy.html` and `terms.html` — it is shared with the mobile app, which
fetches it live. But each page here carries **two baked copies**:

| Copy | Element |
|---|---|
| JSON | `<script id="legal-data">` — what `legal.js` diffs against |
| HTML | `<article id="legal-article">` — the rendered page |

`legal.js` re-fetches on load and re-renders if the document changed. That is
progressive enhancement. Before it runs — or if it never does — the baked HTML
*is* the page, and the readers who never run it are the ones that matter:
Google Play's privacy-policy crawler reads this URL, and a policy that only
becomes correct after a `fetch()` is not correct.

So: **editing the database is not enough.** Run the bake.

```bash
git pull                 # the owner pushes here directly from GitHub
python3 bake.py          # both pages; or: python3 bake.py privacy
git add -A && git commit && git push
```

This has already gone wrong once — an `app_opens` disclosure was live in the
database while this site served the previous version for days.

## bake.py

Stdlib only, no install step. Pulls both documents from Supabase with the
publishable key (`legal_documents` is public-read by design) and rewrites both
copies on both pages.

`render_article()` in `bake.py` must stay a **mirror** of `render()` in
`legal.js`. If the two produce different markup, the page visibly reflows the
moment the fetch lands. Change one, change the other.

All text from the database is inserted escaped — `bake.py` uses
`html.escape`, `legal.js` uses `textContent`, never `innerHTML`. Keep it that
way; this content is editable from a SQL editor.

## Layout

| File | What |
|---|---|
| `index.html` | Marketing site (`script.js`, `style.css`, `assets/`) |
| `privacy.html`, `terms.html` | Legal pages — baked, see above |
| `delete-account.html` | Account-deletion request page. Play requires a reachable one. |
| `legal.js` | Live-refresh enhancement for the two legal pages |
| `google*.html` | Search Console verification. **Do not delete.** |
| `.nojekyll` | Stops Pages running Jekyll over the site |

## Working here

- **Always `git pull` first.** The owner edits and pushes through the GitHub
  web UI, so a local checkout goes stale without notice.
- **Never force-push a rejected push.** Pull, re-run `bake.py` on top of their
  files, commit again. Hand-written pages and footer links live alongside the
  generated blocks and `bake.py` does not reproduce them.
- Changing legal *copy* means editing Supabase, not these files. Editing the
  baked HTML by hand works until the next bake silently reverts it.

## Related

The app repo has `LEGAL_AND_WEBSITE.md` at its root, which maps the same
pipeline from the other side and lists two dead copies of these pages that
still sit in it (`docs/`, `scripts/generate-legal.ts`) — both stale leftovers
of a retired GitHub Action, and both easy to mistake for the real thing.
