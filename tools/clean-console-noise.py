#!/usr/bin/env python3
"""Silence the browser console on the mirrored pages under blog/.

Every page the crawler saved still carries the plumbing of a live WordPress
install: third-party trackers that no longer exist, a script WordPress builds
on the fly and HTTrack therefore never captured, and subresources written with
http:// URLs, which a browser on an https:// site refuses to load at all. None
of it does anything except fill the console, and two of them break the page's
appearance - the fonts and the icon set are both blocked as mixed content, so
the archive has been rendering in fallback faces with missing glyphs.

Run from the repository root; it is idempotent, so a re-mirror can replay it:

    python3 tools/clean-console-noise.py --dry-run
    python3 tools/clean-console-noise.py

  A  emoji loader  -> deleted. The inline script fetches
     /wp-includes/js/wp-emoji-release.min.js, which WordPress concatenated at
     request time and no mirror can hold: a 404 on every page. The style rule
     beside it stays, because post bodies do contain <img class="emoji"> tags
     and that rule is what sizes them.
  B  third-party scripts -> deleted. devicepx-jetpack (404 on wp.com, and four
     tracking-prevention warnings per page), stats.wp.com plus its _stq inline
     block, and the Gravatar hovercard script with its WPGroHo block. All of
     them phone home for a site that no longer exists.
  C  insecure subresources -> https. Only the hosts that still answer over TLS
     and only tags the browser fetches: the Google Fonts and Font Awesome
     stylesheets, Gravatar avatars, and YouTube frames. Link targets are left
     alone - an <a href> to a dead http:// page is history, not a bug.
  E  own-domain subresources -> root-relative. One post body loads an image
     from http://alljapanesealltheti.me/images/..., which is both mixed content
     and, since the /blog prefix came back, a 404. Rewritten only when the file
     is actually on disk under blog/.
  D  slider.mind934.js -> deleted. It ends in $('#slider-wrap').attr('class')
     and reads .indexOf on the result, and no page in the archive contains a
     #slider-wrap, so it can only ever throw. One file references it.

Left in place on purpose: the html5shiv <script> inside an <!--[if IE]> block,
which no current browser executes; the dns-prefetch <link>s, which are hints
rather than fetches; and jquery-migrate, whose console line is informational
and whose removal 2010-era plugins may not survive.
"""
import os, re, sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')
DRY  = '--dry-run' in sys.argv

# A - the emoji detector and the loader it calls
EMOJI = re.compile(r'[ \t]*<script[^>]*>\s*window\._wpemojiSettings\s*=.*?</script>[ \t]*\r?\n?',
                   re.S | re.I)

# B - scripts that only ever talked to somebody else's server
THIRD_PARTY_SRC = re.compile(
    r'[ \t]*<script[^>]*\bsrc\s*=\s*["\'][^"\']*'
    r'(?:devicepx-jetpack|stats\.wp\.com|s\.gravatar\.com/js/gprofiles)'
    r'[^"\']*["\'][^>]*>\s*</script>[ \t]*\r?\n?', re.I)
# the inline blocks that configure them, which are dead weight once the src is
INLINE_STQ    = re.compile(r'[ \t]*<script[^>]*>(?:(?!</script>).)*?_stq(?:(?!</script>).)*?</script>[ \t]*\r?\n?',
                           re.S | re.I)
INLINE_GROHO  = re.compile(r'[ \t]*<script[^>]*>(?:(?!</script>).)*?WPGroHo(?:(?!</script>).)*?</script>[ \t]*\r?\n?',
                           re.S | re.I)

# C - hosts that still serve over TLS, in the tags a browser actually fetches
SECURE_HOSTS = (r'fonts\.googleapis\.com', r'netdna\.bootstrapcdn\.com',
                r'(?:[0-9]+|s|secure)\.gravatar\.com',
                r'(?:www\.)?youtube(?:-nocookie)?\.com', r'(?:www\.)?youtu\.be')
FETCHED_TAG = re.compile(
    r'(<(?:link|img|iframe|embed|script|source)\b[^>]*?\b(?:src|href)\s*=\s*["\']?)http://('
    + '|'.join(SECURE_HOSTS) + r')', re.I)

# E - our own pages, addressed absolutely and without the /blog prefix
OWN = re.compile(r'(<(?:img|script|iframe|source|embed|link)\b[^>]*?\b(?:src|href)\s*=\s*["\']?)'
                 r'https?://(?:www\.)?alljapanesealltheti\.me(/[^"\'\s>]*)', re.I)

# D - the slider, which has nothing to slide
SLIDER = re.compile(r'[ \t]*<script[^>]*\bsrc\s*=\s*["\'][^"\']*slider\.min[^"\']*["\'][^>]*>'
                    r'\s*</script>[ \t]*\r?\n?', re.I)

def is_html(raw):
    head = raw[:200].lstrip().lower()
    return head.startswith(b'<!doctype html') or head.startswith(b'<html')

def own_local(path):
    """True when a /-rooted site path is a file we actually host under blog/."""
    return os.path.isfile(os.path.join(BLOG, unquote(path).lstrip('/').split('?')[0]))

def process(src):
    n = dict(A=0, B=0, C=0, D=0, E=0)
    src, k = EMOJI.subn('', src);         n['A'] += k
    src, k = THIRD_PARTY_SRC.subn('', src); n['B'] += k
    src, k = INLINE_STQ.subn('', src);    n['B'] += k
    src, k = INLINE_GROHO.subn('', src);  n['B'] += k
    src, k = FETCHED_TAG.subn(r'\1https://\2', src); n['C'] += k
    def reroot(m):
        if not own_local(m.group(2)):
            return m.group(0)             # not ours to fix; leave it as found
        n['E'] += 1
        return m.group(1) + '/blog' + m.group(2)
    src = OWN.sub(reroot, src)
    src, k = SLIDER.subn('', src);        n['D'] += k
    return src, n

def main():
    total = dict(A=0, B=0, C=0, D=0, E=0)
    touched = 0
    for dirpath, _, names in os.walk(BLOG):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            raw = open(path, 'rb').read()
            if not is_html(raw):          # feed/index.html is RSS, not a page
                continue
            src = raw.decode('utf-8', 'surrogateescape')
            out, n = process(src)
            if out == src:
                continue
            touched += 1
            for k in n:
                total[k] += n[k]
            if not DRY:
                with open(path, 'wb') as fh:
                    fh.write(out.encode('utf-8', 'surrogateescape'))
    print(('would change' if DRY else 'changed') + f' {touched:,} pages')
    print(f"  A emoji loaders removed      {total['A']:,}")
    print(f"  B third-party scripts removed {total['B']:,}")
    print(f"  C subresources upgraded to https {total['C']:,}")
    print(f"  D slider scripts removed     {total['D']:,}")
    print(f"  E own-domain subresources re-rooted {total['E']:,}")

if __name__ == '__main__':
    main()
