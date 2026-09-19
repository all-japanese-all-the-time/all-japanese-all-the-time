#!/usr/bin/env python3
"""Take the site's own address back out of the mirrored pages.

Three ways a page said where it was, none of which it needs to:

  A  the "open external links in a new window" plugin, on 1,885 pages. It walks
     every link on load and decides internal from external by looking for the
     site's own name in the URL - on 55 pages literally
     (href.search('alljapanesealltheti.me')), and on the rest by the accident of
     what HTTrack rewrote that string into: href.search(/\\/index.html/), a test
     that calls any clean URL external. Both tests now ask the browser the
     question directly, a.hostname != location.hostname, which is what the
     plugin meant. Served from anywhere but the original domain - the local
     nginx mirror, a copy on a laptop - the old test made every internal link
     open a new window.

  B  links written with the full https://alljapanesealltheti.me/... in page
     bodies, in author and related-post links, and a handful that still name
     alljapaneseallthetime.com, the domain the site was written on. Rewritten
     to a path relative to the page holding them, which is the same destination
     with one redirect fewer on the live site and the only spelling that works
     at all in a downloaded copy. Existence-gated: a URL is only rewritten when
     the page it names is on disk, so a link to something the archive does not
     hold keeps pointing at the internet.

  C  URLs written from the server root, /blog/..., which assume the archive is
     published at exactly that path: the <script src> for the search, the
     search form's action, and the assets and links on the pages recovered
     from the Wayback Machine, whose markup was captured with the prefix in
     place. Same treatment, same gate.

     A link to a page gets index.html on the end, which is what HTTrack wrote
     everywhere else in the mirror and what a browser opening the archive off
     a disk needs: asked for file:///.../a-post/ it lists the directory rather
     than serving the index.html inside it. <link rel=canonical> is the one
     exception - it keeps naming the clean directory URL, because that is the
     URL the site wants indexed.

Left alone: CNAME, robots.txt and sitemap.txt, where an absolute URL is the
format; and the RSS files under */feed/, where the spec wants absolute links.

Run from the repository root; idempotent.

    python3 tools/drop-hardcoded-domain.py --dry-run
    python3 tools/drop-hardcoded-domain.py
"""
import os, re, sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')
DRY  = '--dry-run' in sys.argv

# A - the plugin's idea of "not us", in all three spellings the mirror contains
NOT_US = re.compile(
    r"all_links\.href\.search\((?:'alljapanesealltheti\.me'|/\\/index\.html/)\)\s*==\s*-1")
SAME_ORIGIN = 'all_links.hostname != location.hostname'

# B - our own domain, written out, in something the page points at
# The scheme is optional because a handful of these were written without one -
# href="www.alljapaneseallthetime.com/blog/..." is a relative URL to a browser,
# so those links have been 404ing since they were typed.
OWN = re.compile(r'((?:href|src)=(["\']))(?:https?://)?(?:www\.)?'
                 r'(?:alljapanesealltheti\.me|alljapaneseallthetime\.com)(/[^"\']*)\2')

def is_html(raw):
    head = raw[:200].lstrip().lower()
    return head.startswith(b'<!doctype html') or head.startswith(b'<html')

# C - a URL that assumes the archive sits at /blog/ on the server root
CANONICAL = re.compile(r'(<link\b[^>]*\brel=["\']canonical["\'][^>]*\bhref=(["\']))'
                       r'(/blog/[^"\']*)\2', re.I)
ROOTED    = re.compile(r'((?:href|src|action)=(["\']))(/blog/[^"\']*)\2')
# url(/blog/...) inside the theme's inline CSS - the body background lives there
CSS_URL   = re.compile(r'(url\((["\']?))(/blog/[^"\')]*)(\2\))')

def target_of(url_path):
    """The repo path a site path names, or None when we do not hold it.

    Old links carry the flat URLs the site used before the move into blog/, so
    /dick-and-jane/ is blog/dick-and-jane/ here; the few that already carry the
    prefix are taken as they are.
    """
    clean = url_path.split('#')[0].split('?')[0].strip('/')
    rel = clean if clean == 'blog' or clean.startswith('blog/') else 'blog/' + clean
    on_disk = os.path.join(ROOT, unquote(rel))
    if os.path.isfile(on_disk) or os.path.isfile(os.path.join(on_disk, 'index.html')):
        return rel
    return None

def process(path, src):
    n = dict(A=0, B=0, C=0)
    src, n['A'] = NOT_US.subn(SAME_ORIGIN, src)

    page_dir = os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/')

    def relink(m):
        rel = target_of(m.group(3))
        if not rel:
            return m.group(0)                 # not ours to fix
        n['B'] += 1
        suffix = ''
        for sep in ('#', '?'):                # keep the fragment or query intact
            if sep in m.group(3):
                _, _, rest = m.group(3).partition(sep)
                suffix = sep + rest + suffix
        # pure string arithmetic on the percent-encoded path, so the encoding
        # the page was written with survives
        href = os.path.relpath(rel, page_dir).replace(os.sep, '/')
        if not os.path.splitext(href)[1]:
            href += '/'
        return m.group(1) + href + suffix + m.group(2)

    src = OWN.sub(relink, src)

    def reroot(m, name_the_file=True, close=None):
        rel = target_of(m.group(3))
        if not rel:
            return m.group(0)                 # nothing of ours at that path
        n['C'] += 1
        suffix = ''
        for sep in ('#', '?'):
            if sep in m.group(3):
                _, _, rest = m.group(3).partition(sep)
                suffix = sep + rest + suffix
        href = os.path.relpath(rel, page_dir).replace(os.sep, '/')
        if os.path.isdir(os.path.join(ROOT, unquote(rel))):
            href += '/index.html' if name_the_file else '/'
        return m.group(1) + href + suffix + (close if close is not None else m.group(2))

    # canonical first, so the general rule never sees it
    src = CANONICAL.sub(lambda m: reroot(m, False), src)
    src = ROOTED.sub(reroot, src)
    src = CSS_URL.sub(lambda m: reroot(m, close=m.group(4)), src)
    return src, n

def main():
    total = dict(A=0, B=0, C=0); touched = 0
    for dirpath, _, names in os.walk(BLOG):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            raw = open(path, 'rb').read()
            if (b'alljapanesealltheti' not in raw and b'/index.html/' not in raw
                    and b'="/blog/' not in raw and b"='/blog/" not in raw
                    and b'url("/blog/' not in raw):
                continue
            if not is_html(raw):                     # */feed/index.html is RSS
                continue
            src = raw.decode('utf-8', 'surrogateescape')
            out, n = process(path, src)
            if out == src:
                continue
            touched += 1
            for k in n:
                total[k] += n[k]
            if not DRY:
                with open(path, 'wb') as fh:
                    fh.write(out.encode('utf-8', 'surrogateescape'))
    print(('would change' if DRY else 'changed') + f' {touched:,} pages')
    print(f"  A external-link tests made same-origin {total['A']:,}")
    print(f"  B own-domain links made relative       {total['B']:,}")
    print(f"  C root-absolute /blog/ URLs made relative {total['C']:,}")

if __name__ == '__main__':
    main()
