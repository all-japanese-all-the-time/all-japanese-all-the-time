#!/usr/bin/env python3
"""Take ?replytocom=N off the comment Reply links.

WordPress gave every comment a Reply link of the form

    href='index.html?replytocom=327015#respond'

which on the live blog reloaded the page with the comment form moved under that
comment. The archive has no comment form - nothing can be posted to a static
mirror - so the link does nothing a reader can use, but each one is a distinct
URL to a crawler: 12,939 links, 12,697 distinct URLs, across 773 pages, each serving the same
bytes as the post. They were the bulk of what Search Console filed under
"Alternate page with proper canonical tag" and "Crawled - currently not
indexed", and every one a crawler fetches is one post it did not.

The links are already rel=nofollow; that was never enough to stop discovery.
Dropping the query string leaves each link pointing at the post's own #respond,
which is where the reader ends up anyway, and removes the URLs entirely. The
anchors themselves stay, so the page's markup and the theme's script that
expects them are untouched.

Run from the repository root:  python3 tools/drop-replytocom.py [--dry-run]
Idempotent: a second run finds nothing to change.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry-run' in sys.argv

# Inside an href only, whichever quote it uses.
REPLY = re.compile(r'''(\bhref=(["'])[^"']*?)\?replytocom=\d+''')

def main():
    pages = links = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'blog')):
        for name in filenames:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding='utf-8', errors='surrogateescape', newline='') as fh:
                text = fh.read()
            new, n = REPLY.subn(r'\1', text)
            if not n:
                continue
            pages += 1
            links += n
            if not DRY:
                with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as fh:
                    fh.write(new)
    verb = 'would be ' if DRY else ''
    print(f'  reply links {verb}cleaned: {links:,} on {pages:,} pages')

if __name__ == '__main__':
    main()
