#!/usr/bin/env python3
"""Fetch pages missing from the mirror from the Wayback Machine and clean them.

Wayback's `if_` modifier does not suppress the toolbar, so the injected markup is
stripped here and every rewritten archive link is pointed back at this site's own
structure. Output is a normal page of the archive, indistinguishable in shape
from the 1,172 that were captured directly.
"""
import os, re, sys, json, time
from urllib.parse import quote
import urllib.request

ORIGIN = 'http://www.alljapaneseallthetime.com/blog/'
UA = {'User-Agent': 'Mozilla/5.0 (archival restoration; alljapanesealltheti.me)'}

# --- injected by the Wayback Machine, never part of the original page ---
RE_TAIL      = re.compile(r'<!--\s*FILE ARCHIVED ON.*?-->\s*$', re.S | re.I)
RE_WMSCRIPT  = re.compile(r'<script[^>]*(?:web-static|archive\.org/_static)[^>]*>.*?</script>', re.S | re.I)
RE_WMLINK    = re.compile(r'<link[^>]*(?:web-static|archive\.org/_static)[^>]*>', re.I)
RE_WMINLINE  = re.compile(r'<script[^>]*>[^<]*__wm\.[^<]*</script>', re.S | re.I)
RE_WMSTYLE   = re.compile(r'<style[^>]*>[^<]*#wm-ipp.*?</style>', re.S | re.I)
RE_WMDIV     = re.compile(r'<div[^>]+id="wm-ipp[^"]*".*?</div>\s*(?=<)', re.S | re.I)

# https://web.archive.org/web/<ts><mod>/<original url>
RE_ARCH_SELF = re.compile(r'https?://web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/https?://(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)/blog/', re.I)
RE_ARCH_ROOT = re.compile(r'https?://web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/https?://(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)/', re.I)
RE_ARCH_ANY  = re.compile(r'https?://web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/(https?://)', re.I)
# protocol-relative form, used by the dns-prefetch hints: //web.archive.org/web/<ts>/http://host/
RE_ARCH_PREL = re.compile(r'//web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/(https?://)', re.I)
RE_ABS_SELF  = re.compile(r'https?://(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)/blog/', re.I)
RE_ABS_ROOT  = re.compile(r'https?://(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)/', re.I)

# Two shapes the plain URL regexes cannot see, both real in these snapshots:
#   JSON-escaped inside inline script  ->  https:\/\/web.archive.org\/web\/<ts>\/
#   percent-encoded inside a query     ->  url=http%3A%2F%2Fwww.alljapaneseallthetime.com%2Fblog%2F
RE_ARCH_JSON = re.compile(r'https?:\\/\\/web\.archive\.org\\/web\\/\d{4,14}[a-z_]{0,3}\\/', re.I)
RE_ABS_JSON  = re.compile(r'https?:\\/\\/(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)\\/blog\\/', re.I)
RE_ARCH_PCT  = re.compile(r'https?%3A%2F%2Fweb\.archive\.org%2Fweb%2F\d{4,14}[a-z_]{0,3}%2F', re.I)
RE_ABS_PCT   = re.compile(r'https?%3A%2F%2F(?:www\.)?(?:alljapaneseallthetime\.com|ajatt\.com)%2Fblog%2F', re.I)

SEARCH_TAG = '<script defer src="/blog/search.js"></script>'

def fetch(slug, ts):
    url = f'https://web.archive.org/web/{ts}if_/{ORIGIN}{quote(slug)}/'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def clean(raw):
    s = raw.decode('utf-8', 'surrogateescape')
    for rx in (RE_TAIL, RE_WMSCRIPT, RE_WMLINK, RE_WMINLINE, RE_WMSTYLE, RE_WMDIV):
        s = rx.sub('', s)
    # archive links -> this site's own paths
    s = RE_ARCH_SELF.sub('/blog/', s)
    s = RE_ARCH_ROOT.sub('/blog/', s)      # pre-/blog/ era urls also live under blog/ now
    s = RE_ARCH_ANY.sub(r'\1', s)          # external resources: drop the archive wrapper
    s = RE_ARCH_PREL.sub(r'\1', s)
    # Catch-all for wrappers around non-http schemes: the toolbar rewrites even
    # mailto: links, e.g. .../web/<ts>/mailto:/?subject=... . Strip the wrapper,
    # then repair the stray slash it leaves behind in the mailto.
    s = re.sub(r'https?://web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/', '', s, flags=re.I)
    s = re.sub(r'//web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/', '', s, flags=re.I)
    s = s.replace('mailto:/?', 'mailto:?')
    s = RE_ABS_SELF.sub('/blog/', s)
    s = RE_ABS_ROOT.sub('/blog/', s)
    # the escaped / encoded variants
    s = RE_ARCH_JSON.sub('', s)
    s = RE_ABS_JSON.sub(r'\\/blog\\/', s)
    s = RE_ARCH_PCT.sub('', s)
    s = RE_ABS_PCT.sub('%2Fblog%2F', s)
    # match the rest of the archive: local hashed theme assets
    s = s.replace('/blog/wp-content/themes/magazine-premium/style.css',
                  '/blog/wp-content/themes/magazine-premium/styled934.css')
    s = s.replace('/blog/wp-includes/js/jquery/jquery.js',
                  '/blog/wp-includes/js/jquery/jqueryb8ff.js')
    # The theme decides whether a link is external by comparing against the
    # hostname it was published under. Left alone it would treat every internal
    # link on the live site as outbound, so it is pointed at the current domain.
    s = s.replace("'www.alljapaneseallthetime.com'", "'alljapanesealltheti.me'")
    s = s.replace('"www.alljapaneseallthetime.com"', '"alljapanesealltheti.me"')

    if SEARCH_TAG not in s and '</body>' in s:
        i = s.rfind('</body>')
        s = s[:i] + '\t\t' + SEARCH_TAG + '\n\t' + s[i:]
    return s.encode('utf-8', 'surrogateescape')

def looks_real(b):
    # Deliberately looser than "is a blog post": WordPress *pages* (product,
    # billing, testimonials) use different heading markup from posts, and those
    # are exactly the ones worth recovering here.
    s = b.decode('utf-8', 'replace')
    if len(b) < 3000: return False, f'too small ({len(b)}B)'
    if '<html' not in s.lower(): return False, 'not html'
    if not re.search(r'<title>', s, re.I): return False, 'no title'
    if 'web.archive.org' in s: return False, 'archive links remain'
    if re.search(r'Page Not Found|404 Not Found|Wayback Machine has not archived', s, re.I):
        return False, 'error page'
    if not re.search(r'id="(primary|main|content)"|entry-title|<article', s, re.I):
        return False, 'no content region'
    return True, 'ok'

# ---------------------------------------------------------------------------
# Snapshots older than the magazine-premium theme use entirely different markup
# (#mainwrapper, .entry, a bare <h1>). Dropping them in as-is would leave pages
# that look nothing like the rest of the archive, so the post is lifted out and
# re-wrapped in the current theme's shell. Same approach as the generated
# product pages: only the content region is ours.
# ---------------------------------------------------------------------------

SHELL_SRC = None

def _shell(root):
    global SHELL_SRC
    if SHELL_SRC is None:
        t = open(os.path.join(root, 'blog', 'not-nothing', 'index.html'), 'rb').read()
        s = t.decode('utf-8', 'surrogateescape')
        a = s.index('<div id="primary"'); a = s.index('>', a) + 1
        b = s.index('</div><!-- #primary')
        head, tail = s[:a], s[b:]
        head = re.sub(r'<link rel="alternate"[^>]*?\bComments Feed"[^>]*href="feed/[^>]*>', '', head, flags=re.I)
        head = re.sub(r'<link rel="alternate"[^>]*oembed[^>]*>', '', head, flags=re.I)
        head = re.sub(r"<link rel='shortlink'[^>]*>", '', head, flags=re.I)
        SHELL_SRC = (head, tail)
    return SHELL_SRC

def _extract_div(s, start):
    """Return the inner html of the div opening at `start`, matching nesting."""
    i = s.index('>', start) + 1
    depth, j = 1, i
    for m in re.finditer(r'<(/?)div\b', s[i:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            j = i + m.start(); break
    return s[i:j]

def modernise(raw, root):
    """Old-theme snapshot -> the current theme's shell. None if not old-theme."""
    s = raw.decode('utf-8', 'surrogateescape')
    if re.search(r'id="primary"|entry-title', s):
        return None                                  # already the current theme
    m = re.search(r'<div class="entry">', s, re.I)
    if not m:
        return None
    body = _extract_div(s, m.start())
    h = re.search(r'<h1[^>]*>(.*?)</h1>', s[:m.start()][-3000:], re.S | re.I)
    title = re.sub(r'<[^>]+>', '', h.group(1)).strip() if h else ''
    if not title:
        t = re.search(r'<title>([^<|]+)', s)
        title = t.group(1).strip() if t else 'Recovered page'
    head, tail = _shell(root)
    head = re.sub(r'<title>.*?</title>',
                  f'<title>{html_escape(title)} | AJATT | All Japanese All The Time</title>',
                  head, count=1, flags=re.S)
    art = (f'\n\t\t\t<article class="post">\n\t\t\t\t<header class="entry-header">'
           f'\n\t\t\t\t\t<h1 class="entry-title">{html_escape(title)}</h1>'
           f'\n\t\t\t\t</header>\n\t\t\t\t<div class="entry-content">\n{body}\n'
           f'\t\t\t\t</div><!-- .entry-content -->\n\t\t\t</article>\n')
    return (head + art + tail).encode('utf-8', 'surrogateescape')

def html_escape(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def main():
    todo = json.load(open(sys.argv[1]))          # {slug: [ts_newest, ...]}
    root = sys.argv[2]
    ok = fail = 0
    log = []
    for slug, stamps in sorted(todo.items()):
        dest = os.path.join(root, 'blog', slug)
        if os.path.isfile(os.path.join(dest, 'index.html')):
            print(f'  SKIP exists   {slug[:52]}', flush=True); continue
        if isinstance(stamps, str): stamps = [stamps]
        saved = False
        why = 'no snapshots'
        # newest first; fall back through older ones when a capture is broken
        for ts in stamps:
            try:
                raw = fetch(slug, ts)
            except Exception as e:
                why = f'fetch {e}'; time.sleep(6); continue
            body = clean(raw)
            modern = modernise(body, root)
            if modern is not None:
                body = modern
            good, why = looks_real(body)
            if not good:
                time.sleep(4.0); continue
            os.makedirs(dest, exist_ok=True)
            open(os.path.join(dest, 'index.html'), 'wb').write(body)
            print(f'  OK {len(body):>7}B {ts}  {slug[:50]}', flush=True)
            log.append([slug, ts, len(body)])
            ok += 1; saved = True
            time.sleep(4.0)
            break
        if not saved:
            print(f'  FAIL          {slug[:50]}  ({why})', flush=True)
            fail += 1
    json.dump(log, open(os.path.join(root, '..', 'ajatt', 'audit', 'recovered.json'), 'w'),
              ensure_ascii=False, indent=0)
    print(f'\nrecovered {ok}, failed {fail}', flush=True)

if __name__ == '__main__':
    main()
