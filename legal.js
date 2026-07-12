// Legal pages — live refresh (progressive enhancement).
//
// The article content is baked into the HTML, so the page is complete without
// JS or network. On load we fetch the same document from Supabase (the shared
// source of truth with the mobile app) and, if it changed since the site was
// deployed, re-render the article. All fetched strings are inserted via
// textContent — never innerHTML.

(function () {
  const SUPABASE_URL = 'https://vhaxfnquauzoqnuemyfo.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_viW7Dx53I0Mc4H1drYb9VA_sOCwytCn';

  const article = document.getElementById('legal-article');
  const embeddedEl = document.getElementById('legal-data');
  if (!article || !embeddedEl) return;

  let baked;
  try {
    baked = JSON.parse(embeddedEl.textContent);
  } catch {
    return;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function render(doc) {
    const nodes = [
      el('p', 'eyebrow', doc.eyebrow),
      el('h1', null, doc.title),
      el('p', 'legal-updated', doc.last_updated),
      el('p', 'legal-intro', doc.intro),
    ];
    for (const block of doc.blocks || []) {
      if (block.heading) nodes.push(el('h2', null, block.heading));
      for (const p of block.paragraphs || []) nodes.push(el('p', null, p));
      if (block.bullets && block.bullets.length) {
        const ul = document.createElement('ul');
        for (const item of block.bullets) ul.appendChild(el('li', null, item));
        nodes.push(ul);
      }
      if (block.quote) nodes.push(el('blockquote', null, block.quote));
    }
    nodes.push(el('p', 'legal-disclaimer', doc.disclaimer));
    article.replaceChildren(...nodes);
    document.title = doc.title + ' — Brahmi';
  }

  const params = new URLSearchParams({
    key: 'eq.' + baked.key,
    select: 'key,title,eyebrow,last_updated,intro,blocks,disclaimer',
  });

  fetch(SUPABASE_URL + '/rest/v1/legal_documents?' + params, {
    headers: { apikey: SUPABASE_KEY },
  })
    .then((res) => (res.ok ? res.json() : Promise.reject(new Error(res.status))))
    .then((rows) => {
      const doc = rows && rows[0];
      if (!doc) return;
      if (JSON.stringify(doc) !== JSON.stringify(baked)) render(doc);
    })
    .catch(() => {
      /* Offline or Supabase unreachable — the baked content stands. */
    });
})();
