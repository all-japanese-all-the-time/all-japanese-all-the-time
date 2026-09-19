#!/usr/bin/env python3
"""Remove markup that provably cannot function on a static host.

Groups A-D of audit/STILL-BROKEN.md. Every removal is existence-gated: a tag is
dropped only when its target resolves nowhere on disk, so anything that actually
works is left alone.

  A  password-protected post forms -> unwrapped, not deleted. The box stays
     visible exactly as the comment forms were treated in 82ae6046; only the
     <form> element goes, so nothing can post to a dead endpoint.
  B  <link rel=alternate ...oembed> -> deleted. Invisible head metadata
     describing an endpoint that cannot exist without WordPress.
  C  ad-rotator <img> -> deleted. The rotator was a PHP script and the images
     behind it are not archived.
  D  <script src> / <link rel=stylesheet> / <img> for plugin and theme assets
     that were never mirrored -> deleted.
"""
import os, re, sys
from urllib.parse import unquote

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')

def resolves(base_dir, url):
    u = unquote(url.split('#')[0].split('?')[0])
    if not u or u.startswith(('http://', 'https://', '//', 'data:', 'mailto:')):
        return True                      # not ours to judge
    t = os.path.normpath(os.path.join(ROOT, u.lstrip('/')) if u.startswith('/')
                         else os.path.join(base_dir, u))
    return os.path.isfile(t) or os.path.isdir(t)

SCRIPT = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*>\s*</script>', re.I)
STYLE  = re.compile(r'<link\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>', re.I)
IMG    = re.compile(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*/?>', re.I)
OEMBED = re.compile(r'<link\b[^>]*oembed[^>]*>', re.I)
OEMB_HREF = re.compile(r'\bhref\s*=\s*["\']([^"\']+)["\']', re.I)
PWFORM = re.compile(r'<form\b[^>]*\baction\s*=\s*["\'][^"\']*wp-login\.php[^"\']*["\'][^>]*>', re.I)
DEADIMG = re.compile(r'rotate\.php|/youradhere/|adsense', re.I)

def process(path):
    raw = open(path, 'rb').read()
    s = raw.decode('utf-8', 'surrogateescape')
    d = os.path.dirname(path)
    n = dict(A=0, B=0, C=0, D=0)

    # B - oEmbed metadata, existence-gated like everything else. 2,307 of these
    # JSON files were mirrored and serve fine; only the ones pointing at the
    # query-string endpoint WordPress used to answer are dead.
    def drop_oembed(m):
        h = OEMB_HREF.search(m.group(0))
        if h and resolves(d, h.group(1)): return m.group(0)
        n['B'] += 1; return ''
    s = OEMBED.sub(drop_oembed, s)

    # A - password form: unwrap, keep the box
    while True:
        m = PWFORM.search(s)
        if not m: break
        close = s.find('</form>', m.end())
        if close == -1: break
        s = s[:m.start()] + s[m.end():close] + s[close + 7:]
        n['A'] += 1

    # C / D - scripts, stylesheets and images whose target resolves nowhere
    def drop_script(m):
        if resolves(d, m.group(1)): return m.group(0)
        n['D'] += 1; return ''
    s = SCRIPT.sub(drop_script, s)

    def drop_style(m):
        tag = m.group(0)
        if 'stylesheet' not in tag.lower(): return tag
        if resolves(d, m.group(1)): return tag
        n['D'] += 1; return ''
    s = STYLE.sub(drop_style, s)

    def drop_img(m):
        u = m.group(1)
        if resolves(d, u): return m.group(0)
        if DEADIMG.search(u): n['C'] += 1
        else: n['D'] += 1
        return ''
    s = IMG.sub(drop_img, s)

    if not any(n.values()): return n
    nb = s.encode('utf-8', 'surrogateescape')
    assert nb.count(b'\r') == raw.count(b'\r'), path
    open(path, 'wb').write(nb)
    return n

def main():
    tot = dict(A=0, B=0, C=0, D=0); files = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x not in ('.git', '.vscode', 'audit', 'tools')]
        for f in fn:
            if not f.lower().endswith(('.html', '.htm')): continue
            n = process(os.path.join(dp, f))
            if any(n.values()):
                files += 1
                for k in tot: tot[k] += n[k]
    print(f'  files touched                       : {files:,}')
    print(f'  A password forms unwrapped          : {tot["A"]}')
    print(f'  B oEmbed link tags removed          : {tot["B"]}')
    print(f'  C ad-rotator images removed         : {tot["C"]}')
    print(f'  D dead scripts/styles/images removed: {tot["D"]}')

if __name__ == '__main__':
    main()
