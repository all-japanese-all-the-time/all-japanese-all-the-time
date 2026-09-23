#!/usr/bin/env python3
"""Point every page's rel=canonical at its own clean URL, not at index.html.

HTTrack rewrote each WordPress canonical into a link to the local file, so
1,251 pages under blog/ said

    <link rel="canonical" href="index.html" />

which on /blog/<slug>/ resolves to /blog/<slug>/index.html - a different URL
from the one the page is served at, the one sitemap.txt lists, and the one every
redirect stub's canonical names. Google took the page at its word: the sitemap
URL was reported as "Alternate page with proper canonical tag" and left out of
the index in favour of the index.html spelling, which nothing else pointed at.
Every tool since has assumed the canonicals named the directory; they did not.

'./' is the directory the page lives in, so it resolves to /blog/<slug>/ on the
live site and names no host, like every other URL in the archive. The same
rewrite covers the second HTTrack captures (index-2.html, indexf0d6-2.html),
which are older copies of the post beside them and should defer to it.

Canonicals that already name something else - './', the percent-encoded
self-references on the Wayback-recovered pages, the vanity shortcuts pointing at
their targets, the redirect stubs - are left alone.

Run from the repository root:  python3 tools/fix-canonicals.py [--dry-run]
Idempotent: a second run finds nothing to change.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry-run' in sys.argv

# Only a canonical naming an index*.html file in the page's own directory.
CANONICAL = re.compile(
    r'(<link\b[^>]*\brel=["\']canonical["\'][^>]*\bhref=)(["\'])index[^"\'/]*\.html\2')

def main():
    changed = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'blog')):
        for name in filenames:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding='utf-8', errors='surrogateescape', newline='') as fh:
                text = fh.read()
            new, n = CANONICAL.subn(r'\1\2./\2', text, count=1)
            if not n:
                continue
            changed += 1
            if not DRY:
                with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as fh:
                    fh.write(new)
    verb = 'would be ' if DRY else ''
    print(f'  canonicals {verb}repointed at ./ : {changed:,}')

if __name__ == '__main__':
    main()
