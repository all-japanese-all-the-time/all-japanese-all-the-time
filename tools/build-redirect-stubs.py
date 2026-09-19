#!/usr/bin/env python3
"""Leave a redirect at every URL the site had before the move into blog/.

GitHub Pages serves static files and cannot return a 301, so each old address
gets a small HTML page that sends the reader on. Three mechanisms, in the order
they fire:

  location.replace()  runs as the page parses, so the jump is immediate AND
                      leaves no history entry. That second part matters: with a
                      bare meta refresh, pressing Back lands on the stub, which
                      immediately pushes you forward again - the reader is
                      trapped and cannot go back.
  <meta refresh 0>    the fallback when JavaScript is off.
  a visible link      the fallback when neither runs.

<link rel="canonical"> points at the destination so search engines consolidate on
the real page rather than the stub.

Run from the repository root:  python3 tools/build-redirect-stubs.py
"""
import html, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOVE_COMMIT = '1087f640'
ORIGIN = 'https://alljapanesealltheti.me'

# Feeds and other machine endpoints are skipped: an HTML stub served where a
# reader expects RSS is worse than a 404, because a feed reader cannot parse it.
SKIP_FIRST = {'wp-content', 'wp-includes', 'wp-admin', 'wp-json', 'images',
              'data', 'audio', 'comments'}

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved: {title}</title>
<link rel="canonical" href="{origin}{dest}">
<meta name="referrer" content="no-referrer-when-downgrade">
<meta http-equiv="refresh" content="0; url={dest}">
<script>location.replace({dest_js} + location.search + location.hash);</script>
</head>
<body style="font-family:sans-serif;padding:2em;max-width:40em;margin:0 auto">
<p>This page now lives at <a href="{dest}">{origin}{dest}</a>.</p>
<p style="color:#666;font-size:.9em">The archive moved to <code>/blog/</code> to
restore the URLs the original site used, so that an old link needs only its
domain changed to work again.</p>
</body>
</html>
"""

def moved_paths():
    out = subprocess.run(
        ['git', '-c', 'core.quotepath=false', 'show', '--name-status',
         '--format=', '-M', MOVE_COMMIT],
        capture_output=True, text=True, cwd=ROOT).stdout
    for line in out.splitlines():
        p = line.split('\t')
        if len(p) != 3 or not p[0].startswith('R'):
            continue
        old, new = p[1], p[2]
        if not old.endswith('/index.html') or not new.startswith('blog/'):
            continue
        path = old[:-len('/index.html')]
        first = path.split('/')[0]
        if first in SKIP_FIRST or path.endswith('/feed') or '/feed/' in path + '/':
            continue
        yield path

def main():
    made = skipped = 0
    for path in sorted(set(moved_paths())):
        dest = '/blog/' + path + '/'
        target = os.path.join(ROOT, path, 'index.html')
        if os.path.exists(target):
            skipped += 1              # never overwrite something real
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write(TEMPLATE.format(
                title=html.escape(path.rsplit('/', 1)[-1].replace('-', ' '))[:90],
                dest=html.escape(dest),
                dest_js=repr(dest).replace("'", '"'),
                origin=ORIGIN))
        made += 1
    print(f'  stubs written : {made:,}')
    print(f'  skipped (a real file already there): {skipped}')

if __name__ == '__main__':
    main()
