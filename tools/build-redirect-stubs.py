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

Every URL in the stub is relative to the stub itself, the domain name nowhere in
the file. rel=canonical is an ordinary URL reference, resolved against the
document's base like any other, so on the live site it resolves to exactly the
absolute URL it used to be spelled out as - and a copy of this archive unzipped
on someone's laptop, or served from a subdirectory of another domain, redirects
just as well as the original does.

The three redirects name index.html; the canonical does not. A browser asked
for file:///.../a-post/ lists that directory instead of serving the index.html
inside it, so off a disk the jump has to name the file - while the URL the site
wants indexed is still the directory, which is what the canonical gives.

Run from the repository root:  python3 tools/build-redirect-stubs.py
Existing stubs are rewritten in place; anything that is not a stub is left alone.
"""
import html, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOVE_COMMIT = '1087f640'
DRY = '--dry-run' in sys.argv

# Feeds and other machine endpoints are skipped: an HTML stub served where a
# reader expects RSS is worse than a 404, because a feed reader cannot parse it.
SKIP_FIRST = {'wp-content', 'wp-includes', 'wp-admin', 'wp-json', 'images',
              'data', 'audio', 'comments', 'feed'}

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved: {title}</title>
<link rel="canonical" href="{dest}">
<meta name="referrer" content="no-referrer-when-downgrade">
<meta http-equiv="refresh" content="0; url={jump}">
<script>location.replace({jump_js} + location.search + location.hash);</script>
</head>
<body style="font-family:sans-serif;padding:2em;max-width:40em;margin:0 auto">
<p>This page now lives at <a href="{jump}">{site_path}</a>.</p>
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

def is_stub(target):
    """A page we generated, recognised the same way build-search-index.py does."""
    try:
        head = open(target, 'rb').read(2048)
    except OSError:
        return False
    return b'location.replace' in head and b'canonical' in head

def main():
    made = rewritten = skipped = 0
    for path in sorted(set(moved_paths())):
        # '/blog/a/b/' seen from '/a/b/', which is where this stub lives
        dest = '../' * len(path.split('/')) + 'blog/' + path + '/'
        target = os.path.join(ROOT, path, 'index.html')
        exists = os.path.exists(target)
        if exists and not is_stub(target):
            skipped += 1              # never overwrite something real
            continue
        page = TEMPLATE.format(
            title=html.escape(path.rsplit('/', 1)[-1].replace('-', ' '))[:90],
            dest=html.escape(dest),
            jump=html.escape(dest + 'index.html'),
            jump_js=repr(dest + 'index.html').replace("'", '"'),
            site_path=html.escape('/blog/' + path + '/'))
        if exists and open(target, encoding='utf-8').read() == page:
            continue                  # already current
        if not DRY:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w', encoding='utf-8') as fh:
                fh.write(page)
        if exists:
            rewritten += 1
        else:
            made += 1
    verb = 'would be ' if DRY else ''
    print(f'  stubs {verb}written : {made:,}')
    print(f'  stubs {verb}rewritten in place: {rewritten:,}')
    print(f'  skipped (a real file already there): {skipped}')

if __name__ == '__main__':
    main()
