#!/usr/bin/env python3
"""Give every page the same shell.

A page in this archive is a shared frame - the same stylesheets, the same
header and navigation, the same scripts, the same footer - around a title, a
post and its comments. Two groups of pages had drifted from it:

  A  11 pages recovered from the Wayback Machine carry the theme's markup but
     not its assets. That capture saved the HTML and none of the <link> or
     <script> tags, so those pages load without the theme stylesheet - no
     layout, just the customiser's colours - and without jQuery, bootstrap,
     harvey and themed934.js, which is what runs the mobile menu, the
     off-canvas navigation and the search toggle everywhere else. The missing
     tags are added back in the order the rest of the archive has them, each
     one gated on the file actually being on disk.

     Akismet's form script is deliberately not among them: it lives under
     wp-content/plugins/akismet/_inc/, and the underscore makes Jekyll drop it
     from the GitHub Pages build, so the tag would only ever 404.

  B  574 links back to the blog home, on 287 pages, are written href="", which
     means "this page" - clicking the site title or the footer's copyright
     line reloads what you are already reading instead of going home. HTTrack
     wrote them that way; every other page has a real relative path, and now
     these do too.

Run from the repository root; idempotent.

    python3 tools/share-the-shell.py --dry-run
    python3 tools/share-the-shell.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')
DRY  = '--dry-run' in sys.argv

# what every other page loads, in the order it loads it
STYLES_BEFORE_FONTS = [
    ("msfw-stylesheet-css", "wp-content/plugins/make-safe-for-work/stylesd934.css?ver=5.1.13"),
    ("wp-block-library-css", "wp-includes/css/dist/block-library/style.mind934.css?ver=5.1.13"),
    ("extra-style-css", "wp-content/plugins/organize-series-extra-tokens/orgSeries-extrad934.css?ver=5.1.13"),
    ("orgseries-default-css-css", "wp-content/plugins/organize-series/orgSeriesd934.css?ver=5.1.13"),
]
STYLE_THEME   = ("theme_stylesheet-css", "wp-content/themes/magazine-premium/styled934.css?ver=5.1.13")
STYLE_JETPACK = ("jetpack_css-css", "wp-content/plugins/jetpack/css/jetpackbf7d.css?ver=7.0.3")
SCRIPTS_HEAD = [
    "wp-includes/js/jquery/jqueryb8ff.js?ver=1.12.4",
    "wp-includes/js/jquery/jquery-migrate.min330a.js?ver=1.4.1",
    "wp-content/plugins/countdown-timer/js/webtoolkit.sprintf7c45.js?ver=3.0.6",
]
SCRIPTS_FOOT = [
    "wp-includes/js/comment-reply.mind934.js?ver=5.1.13",
    "wp-content/themes/magazine-premium/library/js/bootstrap.min605a.js?ver=2.2.2",
    "wp-content/themes/magazine-premium/library/js/harvey.mind934.js?ver=5.1.13",
    "wp-content/themes/magazine-premium/library/js/themed934.js?ver=5.1.13",
    "wp-content/plugins/countdown-timer/js/fergcorp_countdownTimer_java7c45.js?ver=3.0.6",
    "wp-includes/js/wp-embed.mind934.js?ver=5.1.13",
]

# anchored on the real stylesheet links, not the dns-prefetch hints that name
# the same hosts earlier in the head
FONTS   = re.compile(r"[ \t]*<link[^>]*rel='stylesheet'[^>]*fonts\.googleapis[^>]*>[ \t]*\r?\n?", re.I)
AWESOME = re.compile(r"[ \t]*<link[^>]*rel='stylesheet'[^>]*font-awesome[^>]*>[ \t]*\r?\n?", re.I)
SEARCHJS = re.compile(r'[ \t]*<script defer src="[^"]*search\.js"></script>', re.I)
HOME = re.compile(r'(<a\s+)href=""(\s+title="AJATT \| All Japanese All The Time"\s+rel="home")')

def rel_to(page_dir, asset):
    """asset is a path under blog/, as the page must address it from where it is."""
    return os.path.relpath(os.path.join('blog', asset.split('?')[0]), page_dir).replace(os.sep, '/') \
         + ('?' + asset.split('?')[1] if '?' in asset else '')

def on_disk(asset):
    return os.path.isfile(os.path.join(BLOG, asset.split('?')[0]))

def style_tag(page_dir, ident, asset):
    return (f"<link rel='stylesheet' id='{ident}' "
            f"href='{rel_to(page_dir, asset)}' type='text/css' media='all' />\n")

def script_tag(page_dir, asset):
    return f"<script type='text/javascript' src='{rel_to(page_dir, asset)}'></script>\n"

def needs_shell(src):
    """A page built on the theme that is missing the theme's own stylesheet."""
    return '<div id="primary"' in src and 'magazine-premium/style' not in src

def add_shell(src, page_dir):
    added = 0
    before = ''.join(style_tag(page_dir, i, a) for i, a in STYLES_BEFORE_FONTS if on_disk(a))
    m = FONTS.search(src)
    if not m:
        return src, 0                     # no anchor to hang the order on; leave it
    added += before.count('<link')
    src = src[:m.start()] + before + src[m.start():]

    m = FONTS.search(src)                 # the same link, now further along
    tail = ''
    if on_disk(STYLE_THEME[1]):
        tail += style_tag(page_dir, *STYLE_THEME); added += 1
    src = src[:m.end()] + tail + src[m.end():]

    m = AWESOME.search(src)
    if m:
        block = ''
        if on_disk(STYLE_JETPACK[1]):
            block += style_tag(page_dir, *STYLE_JETPACK); added += 1
        block += ''.join(script_tag(page_dir, a) for a in SCRIPTS_HEAD if on_disk(a))
        added += sum(1 for a in SCRIPTS_HEAD if on_disk(a))
        src = src[:m.end()] + block + src[m.end():]

    m = SEARCHJS.search(src)
    if m:
        block = ''.join(script_tag(page_dir, a) for a in SCRIPTS_FOOT if on_disk(a))
        added += sum(1 for a in SCRIPTS_FOOT if on_disk(a))
        src = src[:m.start()] + block + src[m.start():]
    return src, added

def main():
    shelled = tags = homes = pages = 0
    for dirpath, _, names in os.walk(BLOG):
        for name in names:
            if name != 'index.html':
                continue
            path = os.path.join(dirpath, name)
            raw = open(path, 'rb').read()
            head = raw[:200].lstrip().lower()
            if not (head.startswith(b'<!doctype html') or head.startswith(b'<html')):
                continue
            src = raw.decode('utf-8', 'surrogateescape')
            out = src
            page_dir = os.path.relpath(dirpath, ROOT).replace(os.sep, '/')

            if needs_shell(out):
                out, n = add_shell(out, page_dir)
                if n:
                    shelled += 1
                    tags += n

            home = rel_to(page_dir, 'index.html')
            out, n = HOME.subn(rf'\g<1>href="{home}"\g<2>', out)
            homes += n

            if out == src:
                continue
            pages += 1
            if not DRY:
                with open(path, 'wb') as fh:
                    fh.write(out.encode('utf-8', 'surrogateescape'))
    print(('would change' if DRY else 'changed') + f' {pages:,} pages')
    print(f'  A pages given the shared assets back {shelled} ({tags} tags)')
    print(f'  B empty links to the home page fixed {homes:,}')

if __name__ == '__main__':
    main()
