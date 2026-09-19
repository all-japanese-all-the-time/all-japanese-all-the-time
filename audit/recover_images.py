#!/usr/bin/env python3
"""Fetch images missing from the mirror from the Wayback Machine.

The `id_` modifier asks for the original bytes rather than a rewritten page, and
Wayback resolves the timestamp to the nearest capture, so one request per file is
enough. Every download is checked against the magic bytes for its extension
before being written — an HTML error page saved as .png would otherwise look like
a successful recovery.
"""
import json, os, re, sys, time, urllib.request
from urllib.parse import quote

ORIGIN = 'http://www.alljapaneseallthetime.com/blog/'
UA = {'User-Agent': 'Mozilla/5.0 (archival restoration; alljapanesealltheti.me)'}
SIG = {'png': [b'\x89PNG'], 'jpg': [b'\xff\xd8\xff'], 'jpeg': [b'\xff\xd8\xff'],
       'gif': [b'GIF8'], 'webp': [b'RIFF'], 'bmp': [b'BM'],
       'ico': [b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'], 'svg': [b'<svg', b'<?xm']}

def local_path(target):
    p = target.lstrip('/')
    return p if p.startswith('blog/') else 'blog/' + p

def remote_url(target, ts='2018'):
    rest = local_path(target)[len('blog/'):]
    return f'https://web.archive.org/web/{ts}id_/{ORIGIN}{quote(rest)}'

def valid(data, path):
    ext = path.rsplit('.', 1)[-1].lower()
    sigs = SIG.get(ext)
    if not sigs: return len(data) > 64
    return any(data.startswith(s) for s in sigs)

def main():
    targets = json.load(open(sys.argv[1]))
    root = os.path.abspath(sys.argv[2])
    ok = skip = fail = 0
    got = []
    for t in targets:
        dest = os.path.join(root, local_path(t))
        if os.path.isfile(dest):
            skip += 1; continue
        url = remote_url(t)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception as e:
            print(f'  MISS  {t[:66]}  ({type(e).__name__})', flush=True); fail += 1; time.sleep(3); continue
        if not valid(data, dest):
            print(f'  BAD   {t[:60]}  (not an image: {data[:6]!r}, {len(data)}B)', flush=True)
            fail += 1; time.sleep(3); continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'wb').write(data)
        print(f'  OK {len(data):>8}B  {t[:64]}', flush=True)
        got.append([t, len(data)]); ok += 1
        time.sleep(3)
    print(f'\nrecovered {ok}, already present {skip}, failed {fail}', flush=True)
    json.dump(got, open('/opt/docker/ajatt/audit/recovered-images.json', 'w'), ensure_ascii=False, indent=0)

if __name__ == '__main__':
    main()
