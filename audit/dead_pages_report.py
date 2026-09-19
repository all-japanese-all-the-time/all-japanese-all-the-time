#!/usr/bin/env python3
"""Prioritised inventory of dead internal page links.

Two numbers per target, because they mean different things:
  refs  - how many times it is linked in total
  pages - how many DISTINCT pages link to it

A target with many refs but one referring page is usually a repeated link inside
one post. A target reached from many distinct pages is in a menu or a widget,
and fixing it once in the template fixes it everywhere.
"""
import csv, collections, os, sys
from urllib.parse import unquote, quote

ORIGIN = 'http://www.alljapaneseallthetime.com/blog/'

def original_url(t):
    """Repo path -> the URL this page had on the live site, for searching."""
    p = t[5:] if t.startswith('blog/') else t
    p = p[:-len('index.html')] if p.endswith('index.html') else p
    p = p.strip('/')
    return ORIGIN + p + ('/' if p and '.' not in p.rsplit('/', 1)[-1] else '')

def wayback_url(t):
    return 'https://web.archive.org/web/*/' + quote(original_url(t), safe=':/')

SCAN, OUT = sys.argv[1], sys.argv[2]
ASSET = ('.png','.jpg','.jpeg','.gif','.css','.js','.php','.json','.mp3','.pdf',
         '.zip','.ico','.xml','.rtf','.xls','.doc','.webp','.svg')

def classify(t):
    p = t[5:] if t.startswith('blog/') else t
    seg = [s for s in p.split('/') if s]
    if not seg: return 'other'
    f = seg[0]
    if f in ('category','tag','series','author'): return f'taxonomy/{f}'
    if f == 'archives': return 'archives'
    if f == 'page' or 'page' in seg[:-1]: return 'pagination'
    if 'comment-page' in p or f == 'comments': return 'comment-pagination'
    if f == 'feed' or seg[-1] == 'feed': return 'feed'
    if f.startswith('web'): return 'wayback-leak'
    if f in ('wp-content','wp-includes','wp-admin','wp-json'): return 'wp-internal'
    if len(seg) == 1 or (len(seg) == 2 and seg[1] == 'index.html'): return 'ARTICLE'
    return 'other'

rows = list(csv.reader(open(os.path.join(SCAN,'deep-broken.csv'))))[1:]
refs = collections.Counter(); pages = collections.defaultdict(set)
for src, kind, raw, target, status in rows:
    t = unquote(target)
    if t.lower().rsplit('/',1)[-1].endswith(ASSET): continue
    refs[t] += 1
    pages[t].add(src)

groups = collections.defaultdict(list)
for t, c in refs.items():
    groups[classify(t)].append((t, c, len(pages[t])))

order = ['ARTICLE','feed','taxonomy/category','taxonomy/series','taxonomy/author',
         'taxonomy/tag','archives','pagination','comment-pagination','wayback-leak',
         'wp-internal','other']
lines = ['# Dead internal page links — by priority', '',
         'Two counts per target: **refs** = total links, **pages** = distinct pages linking to it.',
         'A target reached from many distinct pages is in a template or menu — fix once, fixes everywhere.',
         '',
         'The **original URL** column is the address this page had on the live site, shown in full and',
         'untruncated, so it can be pasted into a search engine or an archive. The **look up** link goes',
         'straight to the Wayback Machine\'s list of captures for that URL — an empty result there means',
         'the page was never archived under that address.',
         '']
lines += ['| category | refs | targets | reached from ≥5 pages | linked from exactly 1 page |',
          '|---|---:|---:|---:|---:|']
for g in order:
    if g not in groups: continue
    items = groups[g]
    lines.append(f'| {g} | {sum(c for _,c,_ in items):,} | {len(items)} | '
                 f'{sum(1 for _,_,p in items if p>=5)} | {sum(1 for _,_,p in items if p==1)} |')
lines.append('')

for g in order:
    if g not in groups: continue
    items = sorted(groups[g], key=lambda x: (-x[2], -x[1]))
    lines += [f'## {g} — {sum(c for _,c,_ in items):,} refs across {len(items)} targets', '',
              '| pages | refs | original URL | look up |', '|---:|---:|---|---|']
    for t, c, p in items[:45]:
        lines.append(f'| {p} | {c} | `{original_url(t)}` | [wayback]({wayback_url(t)}) |')
    if len(items) > 45:
        singles = sum(1 for _,_,p in items[45:] if p == 1)
        lines.append(f'| … | … | *{len(items)-45} more, of which {singles} are linked from a single page* |')
    lines.append('')

open(os.path.join(OUT,'DEAD-PAGES.md'),'w').write('\n'.join(lines))
with open(os.path.join(OUT,'dead-pages.csv'),'w',newline='') as fh:
    w=csv.writer(fh)
    w.writerow(['category','original_url','repo_path','refs','linking_pages','wayback_search','examples'])
    for g in order:
        for t,c,p in sorted(groups.get(g,[]),key=lambda x:(-x[2],-x[1])):
            w.writerow([g,original_url(t),t,c,p,wayback_url(t),' | '.join(sorted(pages[t])[:5])])

tot=sum(sum(c for _,c,_ in v) for v in groups.values())
print(f'{tot:,} refs across {sum(len(v) for v in groups.values())} targets\n')
print(f'{"category":<20}{"refs":>7}{"targets":>9}{">=5 pages":>11}{"1 page":>8}')
for g in order:
    if g not in groups: continue
    it=groups[g]
    print(f'{g:<20}{sum(c for _,c,_ in it):>7}{len(it):>9}'
          f'{sum(1 for _,_,p in it if p>=5):>11}{sum(1 for _,_,p in it if p==1):>8}')
