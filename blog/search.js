/* Title search for the AJATT archive.
 *
 * The original site's search was server-side WordPress, which a static mirror
 * cannot answer. The markup is still here and untouched: every page carries
 *   <form role="search" method="get" action="/blog/"><input name="s"></form>
 * so pressing enter already navigates to /blog/?s=query, exactly as it did on
 * the live site. All that was missing was something to read that parameter.
 *
 * This script adds three things and changes no existing markup:
 *   1. a dropdown of the top matches under the search box, on every page
 *   2. a paginated result list on /blog/?s=query
 *   3. the "@Random Post" menu item, which the same index can answer
 *
 * The index (1,300 titles, ~131 kB, ~41 kB gzipped) is fetched lazily on first
 * use, so a visitor who never searches or rolls the dice never downloads it.
 * Styles are injected from here rather than added to the theme stylesheet,
 * which is a mirrored asset and best left byte-for-byte as it was captured.
 */
(function () {
  'use strict';

  /* Everything this file points at is worked out from its own <script src>,
   * so the archive runs wherever it is put: at /blog/ on the live site, under
   * a subdirectory of some other host, or in a folder opened straight off a
   * disk. document.currentScript is read here, while the script is executing;
   * by the time anything below runs it would be null. */
  var BASE = (function () {
    var self = document.currentScript;
    return self ? new URL('.', self.src).href : new URL('/blog/', location.href).href;
  })();

  /* A browser asked for file:///.../a-post/ lists the directory rather than
   * serving its index.html, so off a disk the file has to be named. On a
   * server the bare directory URL is the real one and is left alone. */
  var FILE = location.protocol === 'file:';

  function postUrl(slug) {
    return BASE + slug + '/' + (FILE ? 'index.html' : '');
  }

  function homeUrl(query) {
    return BASE + (FILE ? 'index.html' : '')
         + (query ? '?s=' + encodeURIComponent(query) : '');
  }

  var INDEX_URL = BASE + 'search-index.json';
  /* Full-text search runs on a small API on the maintainer's own machine. It is
   * consulted ONLY from the results page - never from the dropdown, which keeps
   * the dropdown instant and independent of any server. If the API is slow or
   * unreachable the page falls back to the title index below and says so, so a
   * degraded search is visible rather than silently worse. */
  var API_URL = 'https://search.alljapanesealltheti.me/search';
  var API_TIMEOUT = 2500;
  var PER_PAGE = 10;
  var MAX_DROPDOWN = 5;

  var index = null, loading = null, loadFailed = false;

  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) {
      loading = fetch(INDEX_URL)
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (rows) { index = rows; return rows; })
        .catch(function () { loading = null; loadFailed = true; return []; });
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

  /* Resolves to {mode:'full-text', results:[...]} or null when unavailable.
   * Never rejects: the caller treats null as "use the local index". */
  function apiSearch(q, url) {
    if (typeof fetch !== 'function' || typeof AbortController !== 'function') {
      return Promise.resolve(null);
    }
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, API_TIMEOUT);
    return fetch(url + '?q=' + encodeURIComponent(q) + '&limit=200',
                 { signal: ctrl.signal, mode: 'cors', credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        clearTimeout(timer);
        return (d && d.results) ? d : null;
      })
      .catch(function () {
        clearTimeout(timer);
        return null;                 /* give up quietly; the caller uses titles */
      });
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
      /* the page body is light, unlike the #333 bar the dropdown lives in */
      '.ajatt-searchbar{margin:0 0 16px;display:flex;gap:6px}',
      '.ajatt-searchbar input{flex:1 1 auto;padding:8px 10px;font-size:14px;',
      'border:1px solid #ccc;background:#fff;color:#222;min-width:0}',
      '.ajatt-searchbar input:focus{outline:none;border-color:#888}',
      '.ajatt-searchbar button{padding:8px 14px;border:1px solid #333;background:#333;',
      'color:#fff;cursor:pointer;font-size:13px}',
      '.ajatt-searchbar button:hover{background:#222}',
      '.ajatt-hint{color:#777;font-size:13px;font-style:italic;margin:0 0 18px}',
      '.ajatt-results h1{margin:0 0 4px}',
      '.ajatt-results .ajatt-count{color:#777;font-size:13px;margin:0 0 18px}',
      '.ajatt-results ol{list-style:none;margin:0;padding:0}',
      '.ajatt-results ol li{padding:10px 0;border-bottom:1px solid #ddd}',
      '.ajatt-results ol li a{font-size:16px;line-height:1.4}',
      '.ajatt-snippet{color:#555;font-size:13px;line-height:1.5;margin:4px 0 0}',
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
        a.href = postUrl(r.slug);
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
          window.location.href = postUrl(results[sel].slug);
        }
        /* otherwise the form submits to /blog/?s=... on its own */
      } else if (e.key === 'Escape') close();
    });
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) close();
    });

    /* The theme's form is <form action="/blog/" method="get">, which is the
     * right URL on the live site and nothing at all off a disk. Taking the
     * submit makes the same box work from a folder; on a server it goes
     * exactly where the form would have gone on its own. */
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      window.location.href = homeUrl(input.value.trim());
    });
  }

  /* ---------- results view, on /blog/?s=query ---------- */

  function renderResults(initialQuery) {
    var host = document.getElementById('primary');
    if (!host) return;

    var q = initialQuery, all = search(q), page = 1, mode = 'titles', corrected = null;
    var box = el('div', 'ajatt-results');

    /* The theme's own search box sits in #drop-down-search, which is
     * display:none behind a slideToggle icon. It survives this render (it is
     * outside #primary) but it is hidden, so refining a search would mean
     * hunting for the toggle. This bar is a real form with the same name="s"
     * and action, so enter works even if the handler below never binds. */
    var bar = el('form', 'ajatt-searchbar');
    bar.setAttribute('method', 'get');
    bar.setAttribute('action', homeUrl(''));
    bar.setAttribute('role', 'search');
    var input = el('input');
    input.type = 'search';
    input.name = 's';
    input.value = q;
    input.setAttribute('aria-label', 'Search post titles');
    input.placeholder = 'Search post titles\u2026';
    var go = el('button', null, 'Search');
    go.type = 'submit';
    bar.appendChild(input);
    bar.appendChild(go);
    box.appendChild(bar);

    var h = el('h1', 'entry-title');
    box.appendChild(h);
    var count = el('p', 'ajatt-count');
    box.appendChild(count);
    var list = el('ol'), pager = el('div', 'ajatt-pager');
    box.appendChild(list);
    box.appendChild(pager);

    function heading() {
      h.textContent = '';
      h.appendChild(document.createTextNode('Search results for \u201c' + q + '\u201d'));
      document.title = 'Search results for \u201c' + q + '\u201d | AJATT | All Japanese All The Time';
      count.className = 'ajatt-count';
      if (!longEnough(q)) {
        count.className = 'ajatt-hint';
        count.textContent = hasCJK(q)
          ? 'Type at least one character.'
          : 'Type at least three characters.';
      } else if (loadFailed) {
        /* Saying "no posts matched" when the index never arrived is a lie that
         * looks exactly like a working search finding nothing. */
        count.className = 'ajatt-hint';
        count.textContent = 'The search index could not be loaded. Reload the page to try again.';
      } else if (mode === 'full-text' && corrected) {
        count.textContent = all.length + (all.length === 1 ? ' post' : ' posts')
          + ' found for \u201c' + corrected + '\u201d \u2014 nothing matched \u201c'
          + q + '\u201d, so the spelling was corrected';
      } else if (mode === 'full-text') {
        count.textContent = all.length
          ? all.length + (all.length === 1 ? ' post' : ' posts') + ' found'
            + ' \u2014 searching titles and post text'
          : 'Nothing matched, in titles or post text.';
      } else {
        count.textContent = all.length
          ? all.length + (all.length === 1 ? ' post' : ' posts') + ' found'
            + ' \u2014 titles only; full-text search is unavailable right now'
          : 'No posts matched that title. Full-text search is unavailable right '
            + 'now, so this covers post titles only.';
      }
    }

    function draw() {
      list.textContent = ''; pager.textContent = '';
      if (!longEnough(q)) return;
      var pages = Math.max(1, Math.ceil(all.length / PER_PAGE));
      page = Math.min(Math.max(1, page), pages);
      all.slice((page - 1) * PER_PAGE, page * PER_PAGE).forEach(function (r) {
        var li = el('li'), a = el('a');
        a.href = postUrl(r.slug);
        a.appendChild(highlight(r.title, q));
        li.appendChild(a);
        if (r.snippet) {
          var sn = el('div', 'ajatt-snippet');
          sn.appendChild(highlight(r.snippet, q));
          li.appendChild(sn);
        }
        list.appendChild(li);
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
      btn('\u2039 Prev', page - 1, page === 1);
      var shown = [];
      for (var i = 1; i <= pages; i++) {
        if (i === 1 || i === pages || Math.abs(i - page) <= 2) shown.push(i);
      }
      shown.forEach(function (i, k) {
        if (k && i - shown[k - 1] > 1) pager.appendChild(el('span', 'ajatt-gap', '\u2026'));
        btn(String(i), i, false, i === page);
      });
      btn('Next \u203a', page + 1, page === pages);
    }

    function setQuery(next, pushUrl) {
      q = next;
      all = longEnough(q) ? search(q) : [];
      mode = 'titles';
      page = 1;
      heading(); draw();
      if (longEnough(q)) {
        apiSearch(q, API_URL).then(function (d) {
          if (!d || q !== next) return;          /* stale response, ignore */
          all = d.results; mode = 'full-text'; corrected = d.corrected || null; page = 1;
          heading(); draw();
        });
      }
      /* keep the address bar shareable without reloading the page */
      if (pushUrl && window.history && window.history.replaceState) {
        try {
          window.history.replaceState(null, '', homeUrl(q));
        } catch (e) { /* file:// refuses this in some browsers; harmless */ }
      }
    }

    input.addEventListener('input', function () { setQuery(input.value, false); });
    bar.addEventListener('submit', function (e) {
      e.preventDefault();
      setQuery(input.value, true);
      input.blur();
    });

    heading(); draw();
    host.textContent = '';
    host.appendChild(box);

    /* Titles render immediately from the local index, then full-text results
     * replace them if the API answers in time. */
    if (longEnough(q)) {
      apiSearch(q, API_URL).then(function (d) {
        if (!d || d.q !== q) return;
        all = d.results; mode = 'full-text'; corrected = d.corrected || null; page = 1;
        heading(); draw();
      });
    }
  }

  /* ---------- random post ---------- */

  /* The theme's "@Random Post" menu item asks for the blog home with a ?random
   * query, which WordPress used to answer server-side by picking a post. A
   * static mirror cannot, so the button has only ever reloaded the home page.
   * The title index is already a list of every post in the archive, so the
   * pick is one line of arithmetic once it has loaded.
   *
   * Two paths, because the link is not written the same way everywhere: most
   * pages point at ../index.html?random, a few at /blog/?random, and on a feed
   * page the relative link resolves to the post itself. Intercepting the click
   * skips loading an intermediate page; handling ?random on arrival catches
   * every href, a bookmarked URL, and a click that came from somewhere this
   * script had not loaded. Nothing here edits the mirrored markup, and with
   * JavaScript off the link still does what it did before.
   */

  function currentSlug() {
    var here = window.location.href.split('?')[0].split('#')[0];
    if (here.indexOf(BASE) !== 0) return null;
    return here.slice(BASE.length).split('/')[0] || null;
  }

  /* Resolves true once the browser is on its way to a post, false if the index
   * never arrived - in which case the caller falls back to the plain link.
   *
   * `replace` matters for Back. A click should leave the page it came from in
   * history, the way following the link always did; an arrival at ?random
   * should not, or Back lands on the redirect and rolls again, and the reader
   * cannot get out of the archive by going backwards. */
  function goRandom(except, replace) {
    return load().then(function (rows) {
      if (rows.length < 2) return false;
      var slug;
      do {
        slug = rows[Math.floor(Math.random() * rows.length)][0];
      } while (slug === except);           /* never re-roll the post you are on */
      var url = postUrl(slug);
      if (replace) window.location.replace(url);
      else window.location.href = url;
      return true;
    });
  }

  function randomLink(e) {
    if (!e.target || !e.target.closest) return null;
    var a = e.target.closest('a');
    return a && /\?random\b/.test(a.getAttribute('href') || '') ? a : null;
  }

  function attachRandomLinks() {
    /* delegated on document, because below 768px the theme moves the whole
     * #site-navigation into its off-canvas panel (themed934.js prependTo) -
     * the same link, somewhere else in the page */
    document.addEventListener('mouseover', function (e) {
      if (randomLink(e)) load();           /* warm the index before the click */
    });
    document.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button !== 0 ||
          e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = randomLink(e);
      if (!a) return;
      e.preventDefault();
      goRandom(currentSlug(), false).then(function (went) {
        if (!went) window.location.href = a.href;
      });
    });
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

  function boot() {
    attachRandomLinks();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  /* ?random is answered before the DOM is ready: the redirect needs no markup,
   * and the index fetch is the only thing standing between the click and the
   * post. If the index cannot be loaded the page carries on as itself. */
  if (new URLSearchParams(window.location.search).has('random')) {
    goRandom(currentSlug(), true).then(function (went) { if (!went) boot(); });
  } else {
    boot();
  }
})();
