#!/usr/bin/env python3
"""Read-only broken-link scanner for the AJATT HTTrack mirror."""
import os, re, sys, csv, html, collections
from urllib.parse import urlsplit, unquote

ROOT = os.path.realpath(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT  = sys.argv[2] if len(sys.argv) > 2 else '.'

# attributes that carry a URL
# (?<![.\w]) keeps this from matching a JavaScript property assignment such as
# `location.href = "/blog/series/"`. Without it the scanner reported 1,789 phantom
# broken links for one inert dead-code block repeated across 1,788 pages — the
# string there is concatenated with a dropdown value at runtime and is never a URL
# on its own.
ATTR_RE = re.compile(
    r'''(?<![.\w])\b(href|src|data-src|data-lazy-src|action|poster)\s*=\s*(?:"([^"]*)"|'([^']*)')''',
    re.I)
SRCSET_RE = re.compile(r'''\bsrcset\s*=\s*(?:"([^"]*)"|'([^']*)')''', re.I)

# hosts that are really "this site"
SELF_HOSTS = {
    'alljapanesealltheti.me', 'www.alljapanesealltheti.me',
    'alljapaneseallthetime.com', 'www.alljapaneseallthetime.com',
    'ajatt.com', 'www.ajatt.com',
}

BENIGN_SCHEMES = ('mailto:', 'javascript:', 'tel:', 'data:', 'ftp:', 'irc:',
                  'skype:', 'itms:', 'feed:', 'about:')

def iter_html():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', '.vscode')]
        for fn in filenames:
            if fn.lower().endswith(('.html', '.htm')):
                yield os.path.join(dirpath, fn)

def extract(path):
    try:
        raw = open(path, 'rb').read().decode('utf-8', 'replace')
    except OSError:
        return
    for m in ATTR_RE.finditer(raw):
        attr = m.group(1).lower()
        val = m.group(2) if m.group(2) is not None else m.group(3)
        yield attr, val
    for m in SRCSET_RE.finditer(raw):
        val = m.group(1) if m.group(1) is not None else m.group(2)
        for cand in val.split(','):
            cand = cand.strip().split()
            if cand:
                yield 'srcset', cand[0]

def classify(val):
    """-> (kind, cleaned_path_or_None)  kind in internal/external/benign/empty"""
    v = html.unescape(val).strip()
    if v == '':
        return 'empty', None
    low = v.lower()
    if low.startswith('#'):
        return 'benign', None
    if low.startswith(BENIGN_SCHEMES):
        return 'benign', None
    if low.startswith('//'):
        sp = urlsplit('http:' + v)
        if sp.hostname and sp.hostname.lower() in SELF_HOSTS:
            return 'internal-abs', sp.path
        return 'external', None
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:', v):
        sp = urlsplit(v)
        if sp.scheme.lower() in ('http', 'https'):
            if sp.hostname and sp.hostname.lower() in SELF_HOSTS:
                return 'internal-abs', sp.path
            return 'external', None
        return 'benign', None
    # relative / root-relative
    sp = urlsplit(v)
    if sp.path == '':
        return 'benign', None          # pure ?query or #frag
    return 'internal-rel', sp.path

def resolve(src_file, kind, p):
    """Return (abs_target, ok)."""
    p = unquote(p)
    if kind == 'internal-abs' or p.startswith('/'):
        target = os.path.normpath(os.path.join(ROOT, p.lstrip('/')))
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(src_file), p))
    # must stay inside the repo
    if not (target == ROOT or target.startswith(ROOT + os.sep)):
        return target, 'escapes-root'
    if os.path.isfile(target):
        return target, 'ok'
    if os.path.isdir(target):
        if os.path.isfile(os.path.join(target, 'index.html')):
            return target, 'ok'
        return target, 'dir-no-index'
    return target, 'missing'

rows = []
counts = collections.Counter()
ext_domains = collections.Counter()
missing_group = collections.Counter()
missing_refs = collections.defaultdict(set)

nfiles = 0
for f in iter_html():
    nfiles += 1
    rel_src = os.path.relpath(f, ROOT)
    for attr, val in extract(f):
        kind, p = classify(val)
        counts[kind] += 1
        if kind == 'external':
            try:
                h = urlsplit(html.unescape(val) if not val.startswith('//')
                             else 'http:' + val).hostname or '?'
            except ValueError:
                h = '?'
            ext_domains[h.lower()] += 1
            continue
        if kind in ('benign', 'empty'):
            continue
        target, status = resolve(f, kind, p)
        if status != 'ok':
            rel_t = os.path.relpath(target, ROOT)
            rows.append((rel_src, attr, html.unescape(val), rel_t, status, kind))
            counts['BROKEN'] += 1
            missing_group[rel_t] += 1
            missing_refs[rel_t].add(rel_src)
        else:
            counts['resolved-ok'] += 1

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'broken-links.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['source_file', 'attr', 'raw_link', 'resolved_target', 'status', 'link_kind'])
    w.writerows(sorted(rows))

with open(os.path.join(OUT, 'missing-targets.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['missing_target', 'inbound_link_count', 'distinct_referring_pages'])
    for t, c in missing_group.most_common():
        w.writerow([t, c, len(missing_refs[t])])

with open(os.path.join(OUT, 'external-domains.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['domain', 'link_count'])
    for d, c in ext_domains.most_common():
        w.writerow([d, c])

print(f'HTML files scanned : {nfiles}')
for k in ('internal-rel', 'internal-abs', 'external', 'benign', 'empty',
          'resolved-ok', 'BROKEN'):
    print(f'{k:>14} : {counts[k]}')
print(f'distinct missing targets : {len(missing_group)}')
