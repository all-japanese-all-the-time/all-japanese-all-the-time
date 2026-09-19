#!/usr/bin/env python3
"""Deeper audit than linkscan.py: covers the reference kinds the attribute-only
scanner never looked at, plus files that exist but are not what they claim."""
import os, re, sys, csv, html, json, collections, struct
from urllib.parse import unquote, urlsplit

ROOT = os.path.realpath(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/deep'
os.makedirs(OUT, exist_ok=True)

SELF = {'alljapanesealltheti.me','www.alljapanesealltheti.me','alljapaneseallthetime.com',
        'www.alljapaneseallthetime.com','ajatt.com','www.ajatt.com'}
BENIGN = ('mailto:','javascript:','tel:','data:','ftp:','irc:','skype:','itms:','feed:','about:')

ATTR   = re.compile(r'(?<![.\w])\b(href|src|data-src|data-lazy-src|action|poster)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
SRCSET = re.compile(r'\bsrcset\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
LINKEL = re.compile(r'<link>([^<]+)</link>', re.I)          # RSS element text
CSSURL = re.compile(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', re.I)
STYLE  = re.compile(r'\bstyle\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)

def refs(path, raw):
    txt = raw.decode('utf-8', 'surrogateescape')
    for m in ATTR.finditer(txt):
        yield m.group(1).lower(), (m.group(2) if m.group(2) is not None else m.group(3))
    for m in SRCSET.finditer(txt):
        for cand in (m.group(1) or m.group(2) or '').split(','):
            c = cand.strip().split()
            if c: yield 'srcset', c[0]
    if path.endswith(('.html','.htm')):
        for m in LINKEL.finditer(txt):
            yield 'link-element-text', m.group(1).strip()
        for m in STYLE.finditer(txt):
            for u in CSSURL.finditer(m.group(1) or m.group(2) or ''):
                yield 'inline-style-url', u.group(1)
    if path.endswith('.css'):
        for m in CSSURL.finditer(txt):
            yield 'css-url', m.group(1)

def classify(v):
    v = html.unescape(v).strip()
    if not v or v[0] == '#': return None
    low = v.lower()
    if low.startswith(BENIGN): return None
    if low.startswith('//'):
        h = urlsplit('http:'+v).hostname
        return urlsplit('http:'+v).path if h and h.lower() in SELF else None
    if re.match(r'^[a-zA-Z][\w+.\-]*:', v):
        sp = urlsplit(v)
        if sp.scheme.lower() in ('http','https') and sp.hostname and sp.hostname.lower() in SELF:
            return sp.path
        return None
    p = urlsplit(v).path
    return p or None

def resolve(base_dir, p):
    p = unquote(p)
    if p.startswith('/'):
        t = os.path.normpath(os.path.join(ROOT, p.lstrip('/')))
    else:
        t = os.path.normpath(os.path.join(base_dir, p))
    if not (t == ROOT or t.startswith(ROOT + os.sep)):
        segs = []
        for s in p.split('/'):
            if s == '..':
                if segs: segs.pop()
            elif s not in ('', '.'): segs.append(s)
        t = os.path.join(ROOT, *segs)
    if os.path.isfile(t): return t, 'ok'
    if os.path.isdir(t):
        return (t, 'ok') if os.path.isfile(os.path.join(t,'index.html')) else (t,'dir-no-index')
    return t, 'missing'

broken = []
bykind = collections.Counter()
scanned = 0
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ('.git','.vscode')]
    for f in fn:
        if not f.lower().endswith(('.html','.htm','.css')): continue
        p = os.path.join(dp, f); scanned += 1
        raw = open(p,'rb').read()
        for kind, val in refs(p, raw):
            path = classify(val)
            if path is None: continue
            t, st = resolve(dp, path)
            if st != 'ok':
                broken.append((os.path.relpath(p,ROOT), kind, html.unescape(val),
                               os.path.relpath(t,ROOT), st))
                bykind[kind] += 1

# --- files that exist but are not what their extension claims ---
SIG = {b'\x89PNG':'png', b'\xff\xd8\xff':'jpg', b'GIF8':'gif', b'RIFF':'webp',
       b'%PDF':'pdf', b'\x1f\x8b\x08':'GZIP', b'ID3':'mp3', b'\xff\xfb':'mp3', b'OggS':'ogg'}
EXTMAP = {'png':'png','jpg':'jpg','jpeg':'jpg','gif':'gif','webp':'webp','pdf':'pdf','mp3':'mp3'}
bad_media, empty = [], []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ('.git','.vscode')]
    for f in fn:
        p = os.path.join(dp,f); ext = f.rsplit('.',1)[-1].lower() if '.' in f else ''
        try: sz = os.path.getsize(p)
        except OSError: continue
        if sz == 0: empty.append(os.path.relpath(p,ROOT)); continue
        if ext not in EXTMAP: continue
        head = open(p,'rb').read(12)
        actual = next((v for k,v in SIG.items() if head.startswith(k)), None)
        if actual != EXTMAP[ext]:
            bad_media.append((os.path.relpath(p,ROOT), ext, actual or repr(head[:6]), sz))

with open(os.path.join(OUT,'deep-broken.csv'),'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['source','ref_kind','raw','target','status']); w.writerows(sorted(broken))
with open(os.path.join(OUT,'bad-media.csv'),'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['file','claims','actually','bytes']); w.writerows(sorted(bad_media))

print(f'files scanned      : {scanned:,}')
print(f'broken references  : {len(broken):,}')
for k,v in bykind.most_common(): print(f'    {v:>6}  {k}')
print(f'zero-byte files    : {len(empty)}')
print(f'mislabelled media  : {len(bad_media)}')
for r in bad_media[:6]: print(f'    {r[0][:70]} claims .{r[1]} is {r[2]}')
