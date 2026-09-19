#!/usr/bin/env python3
"""Add download links for the preserved product PDFs to the posts that describe them.

The PDFs are committed under 0-AJATT-Products/ but nothing pointed at them except
the QRG page, so a reader on the Little Red Dao posts had no way to know the
volumes they describe are sitting in this same archive.

The links go in a marked box at the top of the post rather than into its body.
Editing the writing itself would blur what Khatzumoto wrote and what the archive
added; a box that says which it is keeps that clear, and is the same framing used
by the replacement product pages.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = 'ajatt-archive-downloads'

BOX = ('<div class="' + MARKER + '" style="border-left:4px solid #ccc;'
       'padding:10px 14px;margin:0 0 22px;background:#f6f6f6;font-size:14px">'
       '<p style="margin:0 0 6px"><strong>Preserved in this archive.</strong> '
       'The files this post describes have been tracked down and are kept with '
       'it — note from the archive’s maintainers, not original AJATT text.</p>'
       '<ul style="margin:0;padding-left:1.4em">{items}</ul></div>')

LARD = [('The Little Red Dao of AJATT, Volume 0 (PDF)', 'AJATT LARD 0.pdf'),
        ('The Little Red Dao of AJATT, Volume 1 (PDF)', 'AJATT LARD 1.pdf'),
        ('The Little Red Dao of AJATT, Volume 2 (PDF)', 'AJATT LARD 2.pdf')]
QRG  = [('AJATT Quick Reference Guide, v1rev7 (PDF)', 'AJATT QRG - v1rev7.pdf')]

# The posts a reader actually lands on when looking for these, rather than every
# post that mentions them: the two Little Red Dao posts, the audiobook offer that
# sends people looking for the volumes, and the two QRG pages that present the
# guide itself. Teasers and progress updates are left alone.
TARGETS = {
    'lard-the-little-red-dao-of-ajatt-yours-is-here': LARD,
    'the-little-red-dao-of-ajatt': LARD,
    'free-lard-audiobook-special-offer': LARD,
    'qrg': QRG,
    'qrg-version-10-is-here': QRG,
}

def quote(name):
    from urllib.parse import quote as q
    return '/0-AJATT-Products/' + q(name)

def box_for(files):
    items = ''.join(
        f'<li><a href="{quote(f)}" target="_blank" rel="noopener">{t}</a></li>'
        for t, f in files
        if os.path.isfile(os.path.join(ROOT, '0-AJATT-Products', f)))
    return BOX.format(items=items) if items else None

OPEN = re.compile(r'(<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>)', re.I)

def main():
    done = missing = 0
    for slug, files in TARGETS.items():
        p = os.path.join(ROOT, 'blog', slug, 'index.html')
        if not os.path.isfile(p):
            print(f'  no such post: {slug[:56]}'); missing += 1; continue
        raw = open(p, 'rb').read()
        s = raw.decode('utf-8', 'surrogateescape')
        if MARKER in s:
            print(f'  already linked: {slug[:56]}'); continue
        box = box_for(files)
        if not box:
            print(f'  no files on disk for: {slug[:56]}'); continue
        m = OPEN.search(s)
        if not m:
            print(f'  no entry-content in: {slug[:56]}'); missing += 1; continue
        out = s[:m.end()] + '\n' + box + '\n' + s[m.end():]
        nb = out.encode('utf-8', 'surrogateescape')
        assert nb.count(b'\r') == raw.count(b'\r'), p
        open(p, 'wb').write(nb)
        print(f'  linked {len(files)} file(s): {slug[:56]}')
        done += 1
    print(f'\n{done} post(s) updated, {missing} not found')

if __name__ == '__main__':
    main()
