#!/usr/bin/env python3
"""Generate blog/search-index.json — the title index behind the search box.

Run from the repository root after adding or renaming a post:

    python3 tools/build-search-index.py

Output is [[slug, title], ...], which is the most compact shape that still
round-trips: the URL is /blog/<slug>/ and nothing else is needed for a title
search. Roughly 110 kB, ~38 kB over the wire once gzipped, and it is fetched
lazily on first use of the search box rather than on page load.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')

# Not posts: taxonomy listings, feeds, and the mirrored WordPress plumbing.
SKIP = {
    'tag', 'category', 'series', 'author', 'archives', 'comments', 'feed',
    'page', 'search', 'wp-content', 'wp-includes', 'wp-admin', 'wp-json',
    'data', 'images', 'audio', 'store', 'deletions', 'emailsub',
}

H1 = re.compile(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', re.S | re.I)
TITLE = re.compile(r'<title>(.*?)</title>', re.S | re.I)
TAGS = re.compile(r'<[^>]+>')
SUFFIX = re.compile(r'\s*\|\s*AJATT\s*\|.*$', re.I | re.S)

def is_redirect_stub(path):
    """True for the small pages that only forward to somewhere else.

    They are real URLs and must keep working, but they are not content: listing
    one in the sitemap invites a search engine to index a redirect, and putting
    one in the search index offers the reader a result that immediately bounces
    them elsewhere.
    """
    try:
        head = open(path, 'rb').read(2048)
    except OSError:
        return False
    return b'location.replace' in head and b'canonical' in head

def clean(raw):
    return re.sub(r'\s+', ' ', html.unescape(TAGS.sub('', raw))).strip()

def title_for(page):
    src = open(page, 'rb').read().decode('utf-8', 'surrogateescape')
    m = H1.search(src)                       # the post's own heading, preferred
    if m:
        t = clean(m.group(1))
        if t:
            return t
    m = TITLE.search(src)                    # fall back to <title> minus the site suffix
    if m:
        return clean(SUFFIX.sub('', m.group(1)))
    return ''

def main():
    rows = []
    for slug in sorted(os.listdir(BLOG)):
        if slug in SKIP or slug.startswith('.'):
            continue
        page = os.path.join(BLOG, slug, 'index.html')
        if not os.path.isfile(page) or is_redirect_stub(page):
            continue
        t = title_for(page)
        if t:
            rows.append([slug, t])

    out = os.path.join(BLOG, 'search-index.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(out)
    print(f'{len(rows):,} posts -> {out} ({size/1024:.0f} kB)')
    if not rows:
        sys.exit('refusing to write an empty index')

if __name__ == '__main__':
    main()
