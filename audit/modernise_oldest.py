#!/usr/bin/env python3
"""Re-wrap recovered pages that use AJATT's oldest theme (#wrapper/#content).

The Wayback recovery already cleaned these — no archive links remain — but they
still carry a 2008-era layout that looks nothing like the rest of the archive.
The post is lifted out of #content and placed in the current theme's shell, and
the ad block and share widget that sat inside #content are dropped: they are
dead weight (the ad network is gone, the share service is gone) and they are not
part of the writing.
"""
import os, re, sys, subprocess

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')

def inner_div(s, start):
    j = s.index('>', start) + 1
    depth, end = 1, len(s)
    for m in re.finditer(r'<(/?)div\b', s[j:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            end = j + m.start(); break
    return s[j:end], end

def strip_block(s, cls):
    """Remove every <div class="...cls..."> ... </div>, nesting-aware."""
    while True:
        m = re.search(r'<div[^>]*class="[^"]*\b' + cls + r'[^"]*"[^>]*>', s, re.I)
        if not m: return s
        _, end = inner_div(s, m.start())
        close = s.find('</div>', end)
        s = s[:m.start()] + s[(close + 6) if close != -1 else end:]

def shell():
    t = open(os.path.join(ROOT, 'blog', 'not-nothing', 'index.html'), 'rb').read()
    s = t.decode('utf-8', 'surrogateescape')
    a = s.index('<div id="primary"'); a = s.index('>', a) + 1
    b = s.index('</div><!-- #primary')
    head, tail = s[:a], s[b:]
    head = re.sub(r'<link rel="alternate"[^>]*?\bComments Feed"[^>]*href="feed/[^>]*>', '', head, flags=re.I)
    head = re.sub(r'<link rel="alternate"[^>]*oembed[^>]*>', '', head, flags=re.I)
    head = re.sub(r"<link rel='shortlink'[^>]*>", '', head, flags=re.I)
    return head, tail

def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def convert(path):
    s = open(path, 'rb').read().decode('utf-8', 'surrogateescape')
    if 'id="primary"' in s or '<div id="content"' not in s:
        return None
    body, _ = inner_div(s, s.index('<div id="content"'))
    # title: the old theme's <h2 id="post-NNN">
    h = re.search(r'<h2[^>]*id="post-\d+"[^>]*>(.*?)</h2>', body, re.S | re.I)
    title = re.sub(r'<[^>]+>', '', h.group(1)).strip() if h else ''
    if h:
        body = body[:h.start()] + body[h.end():]
    if not title:
        t = re.search(r'<title>([^<|]+)', s)
        title = t.group(1).strip() if t else 'Recovered page'
    for cls in ('adsense-left', 'adsense', 'sociable_tagline', 'sociable'):
        body = strip_block(body, cls)
    head, tail = shell()
    head = re.sub(r'<title>.*?</title>',
                  f'<title>{esc(title)} | AJATT | All Japanese All The Time</title>',
                  head, count=1, flags=re.S)
    art = (f'\n\t\t\t<article class="post">\n\t\t\t\t<header class="entry-header">'
           f'\n\t\t\t\t\t<h1 class="entry-title">{esc(title)}</h1>'
           f'\n\t\t\t\t</header>\n\t\t\t\t<div class="entry-content">\n{body}\n'
           f'\t\t\t\t</div><!-- .entry-content -->\n\t\t\t</article>\n')
    return (head + art + tail).encode('utf-8', 'surrogateescape'), title

def main():
    out = subprocess.run(['git', '-c', 'core.quotepath=false', 'status', '--porcelain', '-z'],
                         capture_output=True, text=True, cwd=ROOT).stdout
    dirs = [e[3:] for e in out.split('\0') if e.startswith('?? ') and e[3:].startswith('blog/')]
    n = 0
    for d in dirs:
        p = os.path.join(ROOT, d.rstrip('/'), 'index.html')
        if not os.path.isfile(p): continue
        r = convert(p)
        if not r: continue
        data, title = r
        open(p, 'wb').write(data)
        print(f'  {len(data):>7}B  {title[:44]:<46} {d[5:60]}')
        n += 1
    print(f'\n{n} oldest-theme pages re-wrapped')

if __name__ == '__main__':
    main()
