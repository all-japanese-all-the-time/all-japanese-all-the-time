#!/usr/bin/env python3
"""Remove the RSS feeds, and every reference to them.

HTTrack saved each WordPress feed as feed/index.html: a comment feed per post,
one per category, tag, series and author, the site feed and the site comments
feed - 1,236 directories, about 25 MB. None of them was usable as a feed.
They are snapshots that will never gain an item. GitHub Pages serves them as
text/html because of the file name, and their links are root-relative, which
RSS does not allow and readers cannot follow. The flat /<slug>/feed/ URLs have
404'd since the move into blog/, so nobody is subscribed. What they did do was
hand crawlers 1,236 more URLs of XML under an HTML content type, which Search
Console filed under "Crawled - currently not indexed".

Three steps:

  1  Delete every directory named feed/, including the stub at /feed/ that
     build-redirect-stubs.py wrote because its feed rule missed a top-level
     one (fixed there too).
  2  Remove the <link rel="alternate" type="application/rss+xml"> tags from
     page heads. Browsers do not render them; only feed discovery reads them,
     and there is nothing left to discover.
  3  Unwrap the few links to a feed in page bodies: WordPress's "RSS feed for
     comments on this post" on three recovered pages, and a 2007 comment
     pointing a reader at /comments/feed/. The words stay where they were;
     only the link goes.

Run from the repository root:  python3 tools/drop-feeds.py [--dry-run]
Idempotent: a second run finds nothing to change.
"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry-run' in sys.argv

# The tag on a line of its own takes its line with it; anywhere else, just the tag.
HEAD_LINK = re.compile(
    r'^[ \t]*<link\b[^>]*\btype=["\']application/rss\+xml["\'][^>]*>[ \t]*\r?\n'
    r'|<link\b[^>]*\btype=["\']application/rss\+xml["\'][^>]*>', re.M)
BODY_LINK = re.compile(
    r'<a\b[^>]*\bhref=["\'][^"\']*/feed(?:/[^"\']*)?["\'][^>]*>(.*?)</a>', re.S)

def feed_dirs():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for d in list(dirnames):
            if d == 'feed':
                dirnames.remove(d)
                yield os.path.join(dirpath, d)

def main():
    dirs = list(feed_dirs())
    for d in dirs:
        if not DRY:
            shutil.rmtree(d)
            parent = os.path.dirname(d)
            while parent != ROOT and not os.listdir(parent):
                os.rmdir(parent)
                parent = os.path.dirname(parent)

    pages = tags = links = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding='utf-8', errors='surrogateescape', newline='') as fh:
                text = fh.read()
            new, t = HEAD_LINK.subn('', text)
            new, l = BODY_LINK.subn(r'\1', new)
            if not (t or l):
                continue
            pages += 1
            tags += t
            links += l
            if not DRY:
                with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as fh:
                    fh.write(new)

    verb = 'would be ' if DRY else ''
    print(f'  feed directories {verb}removed: {len(dirs):,}')
    print(f'  head <link> tags {verb}removed: {tags:,}')
    print(f'  body links {verb}unwrapped   : {links:,}')
    print(f'  pages {verb}edited          : {pages:,}')

if __name__ == '__main__':
    main()
