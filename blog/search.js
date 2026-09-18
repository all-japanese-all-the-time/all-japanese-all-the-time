/* Title search for the AJATT archive.
 *
 * The original site's search was server-side WordPress, which a static mirror
 * cannot answer. The markup is still here and untouched: every page carries
 *   <form role="search" method="get" action="/blog/"><input name="s"></form>
 * so pressing enter already navigates to /blog/?s=query, exactly as it did on
 * the live site. All that was missing was something to read that parameter.
 *
 * This script adds two things and changes no existing markup:
 *   1. a dropdown of the top matches under the search box, on every page
 *   2. a paginated result list on /blog/?s=query
 *
 * The index (1,165 titles, ~115 kB, ~38 kB gzipped) is fetched lazily on first
 * use, so a visitor who never searches never downloads it. Styles are injected
 * from here rather than added to the theme stylesheet, which is a mirrored
 * asset and best left byte-for-byte as it was captured.
 */
(function () {
  'use strict';

  var INDEX_URL = '/blog/search-index.json';
  var PER_PAGE = 10;
  var MAX_DROPDOWN = 5;

  var index = null, loading = null;

  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) {
      loading = fetch(INDEX_URL)
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (rows) { index = rows; return rows; })
        .catch(function () { loading = null; return []; });
    }
    return loading;
  }

  // Titles use typographic punctuation; queries usually don't.
  function norm(s) {
    return s.toLowerCase()
            .replace(/[‘’ʼ]/g, "'")
            .replace(/[“”]/g, '"')
            .replace(/[–—]/g, '-');
  }

  function hasCJK(s) {
    return /[぀-ヿ㐀-䶿一-鿿豈-﫿]/.test(s);
  }

  // Three Latin characters is enough to avoid matching most of the archive at
  // once, but Japanese queries are routinely one or two characters (漢字, 本),
  // so a flat minimum would make part of this site unsearchable.
  function longEnough(q) {
    return hasCJK(q) ? q.length >= 1 : q.trim().length >= 3;
  }

  function search(q) {
    var n = norm(q).trim();
    if (!n || !index) return [];
    var out = [];
    for (var i = 0; i < index.length; i++) {
      var slug = index[i][0], title = index[i][1];
      var t = norm(title), pos = t.indexOf(n);
      if (pos === -1) {
        if (norm(slug).indexOf(n.replace(/\s+/g, '-')) === -1) continue;
        out.push({ slug: slug, title: title, rank: 4, pos: 0 });
        continue;
      }
      var rank = t === n ? 0                                   // exact title
               : pos === 0 ? 1                                 // title starts with it
               : /[\s(\[‘"'\-:]/.test(t.charAt(pos - 1)) ? 2   // starts a word
               : 3;                                            // somewhere inside
      out.push({ slug: slug, title: title, rank: rank, pos: pos });
    }
    out.sort(function (a, b) {
      return a.rank - b.rank || a.pos - b.pos ||
             a.title.length - b.title.length ||
             a.title.localeCompare(b.title);
    });
    return out;
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;   // textContent, never innerHTML
    return e;
  }

  function highlight(title, q) {
    var frag = document.createDocumentFragment();
    var pos = norm(title).indexOf(norm(q).trim());
    if (pos === -1) { frag.appendChild(document.createTextNode(title)); return frag; }
    var len = norm(q).trim().length;
    frag.appendChild(document.createTextNode(title.slice(0, pos)));
    frag.appendChild(el('mark', 'ajatt-hit', title.slice(pos, pos + len)));
    frag.appendChild(document.createTextNode(title.slice(pos + len)));
    return frag;
  }

  function styles() {
    if (document.getElementById('ajatt-search-styles')) return;
    var s = el('style');
    s.id = 'ajatt-search-styles';
    s.textContent = [
      /* the search bar is #333 with #eee text, so the dropdown continues it */
      '.ajatt-dd{position:absolute;z-index:9999;left:0;right:18px;margin:0;padding:0;',
      'list-style:none;background:#333;border:1px solid #4a4a4a;border-top:none;',
      'max-height:60vh;overflow-y:auto;box-shadow:0 6px 18px rgba(0,0,0,.35)}',
      '.ajatt-dd li{margin:0;padding:0;border-top:1px solid #444}',
      '.ajatt-dd li:first-child{border-top:none}',
      '.ajatt-dd a{display:block;padding:9px 12px;color:#eee;text-decoration:none;',
      'font-size:13px;line-height:1.35}',
      '.ajatt-dd a:hover,.ajatt-dd li.sel a{background:#222;color:#fff}',
      '.ajatt-dd .ajatt-more{padding:8px 12px;color:#aaa;font-size:12px;font-style:italic}',
      '.ajatt-hit{background:transparent;color:#ffd479;font-weight:bold}',
      '.ajatt-results{margin:0 0 24px}',
      '.ajatt-results h1{margin:0 0 4px}',
      '.ajatt-results .ajatt-count{color:#777;font-size:13px;margin:0 0 18px}',
      '.ajatt-results ol{list-style:none;margin:0;padding:0}',
      '.ajatt-results ol li{padding:10px 0;border-bottom:1px solid #ddd}',
      '.ajatt-results ol li a{font-size:16px;line-height:1.4}',
      '.ajatt-results .ajatt-hit{color:#b34700}',
      '.ajatt-pager{margin:20px 0;text-align:center}',
      '.ajatt-pager button{margin:0 2px;padding:5px 10px;border:1px solid #ccc;',
      'background:#fff;cursor:pointer;font-size:13px;line-height:1}',
      '.ajatt-pager button[disabled]{opacity:.4;cursor:default}',
      '.ajatt-pager button.cur{background:#333;color:#fff;border-color:#333}',
      '.ajatt-pager .ajatt-gap{padding:0 4px;color:#999}'
    ].join('');
    document.head.appendChild(s);
  }

  /* ---------- dropdown, on every page that has the box ---------- */

  function attachDropdown(input) {
    var form = input.form;
    if (!form) return;
    var wrap = form.parentNode;
    if (getComputedStyle(wrap).position === 'static') wrap.style.position = 'relative';

    var dd = el('ul', 'ajatt-dd');
    dd.style.display = 'none';
    dd.setAttribute('role', 'listbox');
    wrap.appendChild(dd);
    var results = [], sel = -1;

    function close() { dd.style.display = 'none'; sel = -1; }

    function render(q) {
      dd.textContent = '';
      results = search(q);
      if (!results.length) { close(); return; }
      results.slice(0, MAX_DROPDOWN).forEach(function (r, i) {
        var li = el('li'), a = el('a');
        a.href = '/blog/' + r.slug + '/';
        a.appendChild(highlight(r.title, q));
        a.setAttribute('role', 'option');
        li.appendChild(a);
        li.addEventListener('mouseenter', function () { mark(i); });
        dd.appendChild(li);
      });
      if (results.length > MAX_DROPDOWN) {
        var more = el('li');
        more.appendChild(el('div', 'ajatt-more',
          results.length + ' matches — press Enter to see them all'));
        dd.appendChild(more);
      }
      dd.style.display = 'block';
      sel = -1;
    }

    function mark(i) {
      var items = dd.querySelectorAll('li');
      for (var k = 0; k < items.length; k++) items[k].classList.remove('sel');
      if (i >= 0 && items[i] && items[i].querySelector('a')) items[i].classList.add('sel');
      sel = i;
    }

    function update() {
      var q = input.value;
      if (!longEnough(q)) { close(); return; }
      load().then(function () { if (input.value === q) render(q); });
    }

    input.addEventListener('input', update);
    input.addEventListener('focus', function () { load(); });
    input.addEventListener('keydown', function (e) {
      var n = Math.min(results.length, MAX_DROPDOWN);
      if (e.key === 'ArrowDown' && n) { e.preventDefault(); mark((sel + 1) % n); }
      else if (e.key === 'ArrowUp' && n) { e.preventDefault(); mark((sel - 1 + n) % n); }
      else if (e.key === 'Enter') {
        if (sel >= 0 && results[sel]) {
          e.preventDefault();
          window.location.href = '/blog/' + results[sel].slug + '/';
        }
        /* otherwise the form submits to /blog/?s=... on its own */
      } else if (e.key === 'Escape') close();
    });
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) close();
    });
  }

  /* ---------- results view, on /blog/?s=query ---------- */

  function renderResults(q) {
    var host = document.getElementById('primary');
    if (!host) return;
    var all = search(q), page = 1;
    var box = el('div', 'ajatt-results');

    var h = el('h1', 'entry-title');
    h.appendChild(document.createTextNode('Search results for “' + q + '”'));
    box.appendChild(h);
    var count = el('p', 'ajatt-count',
      all.length ? all.length + (all.length === 1 ? ' post' : ' posts') + ' found'
                 : 'No posts matched that title.');
    box.appendChild(count);

    var list = el('ol'), pager = el('div', 'ajatt-pager');
    box.appendChild(list); box.appendChild(pager);

    function draw() {
      list.textContent = ''; pager.textContent = '';
      var pages = Math.max(1, Math.ceil(all.length / PER_PAGE));
      page = Math.min(Math.max(1, page), pages);
      all.slice((page - 1) * PER_PAGE, page * PER_PAGE).forEach(function (r) {
        var li = el('li'), a = el('a');
        a.href = '/blog/' + r.slug + '/';
        a.appendChild(highlight(r.title, q));
        li.appendChild(a); list.appendChild(li);
      });
      if (pages < 2) return;
      var btn = function (label, to, dis, cur) {
        var b = el('button', cur ? 'cur' : '', label);
        b.type = 'button';
        if (dis) b.disabled = true;
        else b.addEventListener('click', function () {
          page = to; draw();
          box.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        pager.appendChild(b);
      };
      btn('‹ Prev', page - 1, page === 1);
      var shown = [];
      for (var i = 1; i <= pages; i++) {
        if (i === 1 || i === pages || Math.abs(i - page) <= 2) shown.push(i);
      }
      shown.forEach(function (i, k) {
        if (k && i - shown[k - 1] > 1) pager.appendChild(el('span', 'ajatt-gap', '…'));
        btn(String(i), i, false, i === page);
      });
      btn('Next ›', page + 1, page === pages);
    }

    draw();
    host.textContent = '';
    host.appendChild(box);
    document.title = 'Search results for “' + q + '” | AJATT | All Japanese All The Time';
  }

  /* ---------- boot ---------- */

  function init() {
    styles();
    var inputs = document.querySelectorAll('input[name="s"]');
    for (var i = 0; i < inputs.length; i++) attachDropdown(inputs[i]);

    var q = new URLSearchParams(window.location.search).get('s');
    if (q && q.trim() && document.getElementById('primary')) {
      load().then(function () { renderResults(q.trim()); });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
