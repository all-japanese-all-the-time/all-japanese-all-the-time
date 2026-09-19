#!/usr/bin/env python3
"""Regenerate sitemap.txt.

Run from the repository root after adding or renaming a post:

    python3 tools/build-sitemap.py

The previous sitemap was written before the site moved into blog/ and listed
every post at its old flat URL, so all 1,180 entries were stale. Three of them
also carried the origin twice ("...me/https://...me/..."), which is what
prompted regenerating rather than patching.

URLs are directory form with a trailing slash, which is what GitHub Pages treats
as canonical — it 301s the extensionless form to it.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')
ORIGIN = 'https://alljapanesealltheti.me'

# Listing pages and mirrored WordPress plumbing are not canonical content.
SKIP = {
    'tag', 'category', 'series', 'author', 'archives', 'comments', 'feed',
    'page', 'search', 'wp-content', 'wp-includes', 'wp-admin', 'wp-json',
    'data', 'images', 'audio', 'store', 'deletions', 'emailsub',
}

def main():
    urls = [ORIGIN + '/blog/']
    for slug in sorted(os.listdir(BLOG)):
        if slug in SKIP or slug.startswith('.'):
            continue
        if os.path.isfile(os.path.join(BLOG, slug, 'index.html')):
            urls.append(f'{ORIGIN}/blog/{slug}/')

    if len(urls) < 100:
        sys.exit(f'refusing to write a sitemap with only {len(urls)} urls')

    out = os.path.join(ROOT, 'sitemap.txt')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(urls) + '\n')
    print(f'{len(urls):,} urls -> sitemap.txt ({os.path.getsize(out)/1024:.0f} kB)')

if __name__ == '__main__':
    main()
