#!/usr/bin/env python3
"""Generate replacement pages for product pages that no longer exist anywhere.

Several AJATT product and sign-up pages were never captured by the Wayback
Machine — they sat behind order forms, so no crawler ever saw them — yet posts
across the archive still link to them. Those links have been dead for years.

Rather than leave them 404ing, each gets a page that says plainly what used to
be there, and either points at a surviving copy of the product or asks anyone
who still has one to get in touch.

The theme shell is taken from a real page in the archive, so these look native;
only the content region is ours. Run from the repository root:

    python3 tools/build-product-pages.py
"""
import html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'blog', 'not-nothing', 'index.html')
CONTACT = 'ajatt@alias.uchisen.com'

def shell():
    s = open(TEMPLATE, 'rb').read().decode('utf-8', 'surrogateescape')
    a = s.index('<div id="primary"')
    a = s.index('>', a) + 1
    b = s.index('</div><!-- #primary')
    head, tail = s[:a], s[b:]

    # Strip metadata that belongs to the template post rather than to the page
    # being generated. Left in, each new page would advertise a comments feed
    # that does not exist under its own directory, two oEmbed endpoints
    # describing a different post, and that post's WordPress id.
    head = re.sub(r'<link rel="alternate"[^>]*?\bComments Feed"[^>]*href="feed/[^>]*>', '', head, flags=re.I)
    head = re.sub(r'<link rel="alternate"[^>]*oembed[^>]*>', '', head, flags=re.I)
    head = re.sub(r"<link rel='shortlink'[^>]*>", '', head, flags=re.I)
    return head, tail

def mailto(subject):
    from urllib.parse import quote
    return f'mailto:{CONTACT}?subject={quote(subject)}'

def page(title, body_html):
    head, tail = shell()
    head = re.sub(r'<title>.*?</title>',
                  f'<title>{html.escape(title)} | AJATT | All Japanese All The Time</title>',
                  head, count=1, flags=re.S)
    article = f'''
			<article class="post">
				<header class="entry-header">
					<h1 class="entry-title">{html.escape(title)}</h1>
				</header>
				<div class="entry-content">
{body_html}
				</div><!-- .entry-content -->
			</article>
'''
    return (head + article + tail).encode('utf-8', 'surrogateescape')

def _note(body):
    return ('<p style="border-left:4px solid #ccc;padding:8px 14px;margin:0 0 20px;'
            'background:#f6f6f6;font-size:14px">' + body + '</p>')

# The framing has to match what was actually lost, or the page states something
# untrue about its own subject. A product page vanished behind an order form; a
# web service simply stopped existing; a shortcut to somewhere else was never a
# page here at all.
NOTE_SERVICE = _note(
    'This page is part of an archived copy of AJATT. What it describes was a '
    'separate service rather than a page on the blog, so there is nothing to '
    'restore here. What follows is a note from the people maintaining the '
    'archive, not original AJATT material.')
NOTE_LINK = _note(
    'This page is part of an archived copy of AJATT. The address you followed was '
    'a shortcut to somewhere else rather than a page on the blog. What follows is '
    'a note from the people maintaining the archive, not original AJATT material.')

NOTE = ('<p style="border-left:4px solid #ccc;padding:8px 14px;margin:0 0 20px;'
        'background:#f6f6f6;font-size:14px">This page is part of an archived copy of AJATT. '
        'The original page was lost — it was never captured by the Internet Archive, '
        'most likely because it sat behind an order form. What follows is a note from the '
        'people maintaining the archive, not original AJATT material.</p>')

def have_it(title, what, links):
    items = '\n'.join(
        f'					<li><a href="{u}"{" target=\"_blank\" rel=\"noopener\"" if u.startswith("http") else ""}>{html.escape(t)}</a></li>'
        for t, u in links)
    return page(title, f'''{NOTE}
				<p>The original page for <strong>{html.escape(what)}</strong> is gone, but the
				product itself has been tracked down and is preserved with this archive:</p>
				<ul>
{items}
				</ul>
				<p>If you have a better or more complete copy, please
				<a href="{mailto(f'AJATT archive: better copy of {what}')}">get in touch</a>.</p>''')

def service(title, what, extra=''):
    """A web service that lived off the blog and is gone entirely."""
    return page(title, f'''{NOTE_SERVICE}
				<p><strong>{html.escape(what)}</strong> was not a page on this blog \u2014 it ran as its
				own service, at its own address, and that address no longer exists. The
				shortcut that used to lead here has nothing left to lead to.</p>
				<p>Nothing of it has been found: not a working copy, not an export, not a
				page in the Internet Archive.</p>
				<p><strong>If you have anything at all \u2014 an archived page, an export of your
				data, even a screenshot \u2014 please get in touch.</strong> Screenshots are genuinely
				useful here: for a service with nothing left, a picture of the interface may be
				the only record that survives.</p>
				<p><a href="{mailto(f'AJATT archive: I have something from {what}')}">Email
				{CONTACT}</a></p>{extra}''')


def elsewhere(title, what, links, note):
    items = '\n'.join(
        f'					<li><a href="{u}"{" target=\"_blank\" rel=\"noopener\"" if u.startswith("http") else ""}>{html.escape(t)}</a></li>'
        for t, u in links)
    return page(title, f'''{NOTE_LINK}
				<p>{note}</p>
				<ul>
{items}
				</ul>''')


def wanted(title, what):
    return page(title, f'''{NOTE}
				<p>The original page for <strong>{html.escape(what)}</strong> is gone, and so far
				no copy of the product itself has been found. It is not in the Internet Archive,
				and it is not among the files recovered so far.</p>
				<p><strong>If you have a copy, please get in touch.</strong> The goal is simply to
				keep it from disappearing — nothing is being sold here.</p>
				<p><a href="{mailto(f'AJATT archive: I have a copy of {what}')}">Email
				{CONTACT}</a> and it will be added.</p>
				<p style="font-size:13px;color:#777">Subject lines are pre-filled so it is clear
				which item you are writing about.</p>''')

QRG_YT = 'https://www.youtube.com/watch?v=uxhnGvuXS14'
QRG_IA = 'https://archive.org/details/ajattqrgthemovie'
PRODUCTS = '/0-AJATT-Products/'

HAVE = {
    'preorder-qrg-the-movie-today-and-save': (
        'QRG: The Movie', 'QRG: The Movie',
        [('Watch on YouTube', QRG_YT),
         ('Watch on archive.org', QRG_IA),
         ('AJATT QRG (PDF, v1rev7)', PRODUCTS + 'AJATT%20QRG%20-%20v1rev7.pdf')]),
}

SERVICES = {
    'khatzumemo': ('KhatzuMemo', 'KhatzuMemo, the spaced-repetition system'),
    'khatzumemo-dev': ('KhatzuMemo (Development Version)',
                       'the development version of KhatzuMemo'),
}

WAYBACK_FF7 = ('https://web.archive.org/web/20150321162824/'
               'http://ajatt.com/finalfantasy/ff7p-index.htm')

ELSEWHERE = {
    'ff': ('FF7 Dialogue Chart', 'the FF7 dialogue chart',
           [('The index, preserved in the Internet Archive', WAYBACK_FF7)],
           'This shortcut led to a complete Japanese dialogue chart for Final '
           'Fantasy VII \u2014 an index and fourteen further pages \u2014 hosted alongside '
           'AJATT but transcribed by a reader, credited on the blog as R-star. '
           'It is game script rather than anything written for AJATT, so it is '
           'linked here rather than republished. The Internet Archive still has '
           'it:'),
    'twitter': ('AJATT on Twitter', 'AJATT on Twitter',
                [('The AJATT account on X / Twitter', 'https://x.com/ajatt'),
                 ('234 weekly tweet round-ups preserved in this archive',
                  '/blog/archives/')],
                'This shortcut pointed at the AJATT Twitter account rather than at a '
                'page on the blog, so there is nothing here to show you. The account '
                'is still where it was, and the weekly round-ups of it that were '
                'posted to the blog are part of this archive:'),
}

WANTED = {
    'join-ajatt-silverspoon-vanilla': ('Join AJATT SilverSpoon', 'AJATT SilverSpoon'),
    'join-silverspoon-bigboi-post-rtk1': ('Join SilverSpoon BigBoi', 'SilverSpoon BigBoi (post-RTK)'),
    'ajatt-silverspoon-bigboi-post-rtk-sign-up-d': ('SilverSpoon BigBoi — Sign-Up', 'SilverSpoon BigBoi (post-RTK)'),
    'pre-launch-silverspoon-bigboi-the-silverspoon-for-post-rtkers': ('SilverSpoon BigBoi — Pre-Launch', 'SilverSpoon BigBoi (post-RTK)'),
    'join-sinospoon-silverspoon-mandarin': ('Join SinoSpoon', 'SinoSpoon (SilverSpoon for Mandarin)'),
    'sinospoon-silverspoon-mandarin-sign-up-d': ('SinoSpoon — Sign-Up', 'SinoSpoon (SilverSpoon for Mandarin)'),
    'cantospoon-silverspoon-for-cantonese-because-this-is-what-bruce-lee-would-have-wanted': ('CantoSpoon', 'CantoSpoon (SilverSpoon for Cantonese)'),
    'pre-launch-50-percent-discount-join-cantospoon-silverspoon-cantonese': ('CantoSpoon — Pre-Launch', 'CantoSpoon (SilverSpoon for Cantonese)'),
    'pre-order-my-first-japanese-storybook-today-and-save': ('My First Japanese Storybook', 'My First Japanese Storybook'),
    'imx': ('IMX', 'IMX (IMX Japanese / IMX Polyglot)'),
    'ssinfo': ('Neutrino', 'Neutrino'),
}

def write(slug, data):
    d = os.path.join(ROOT, 'blog', slug)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'index.html')
    open(p, 'wb').write(data)
    return len(data)

def main():
    n = 0
    for slug, (title, what, links) in HAVE.items():
        n += 1; print(f'  have    {write(slug, have_it(title, what, links)):>7}B  {slug[:54]}')
    for slug, (title, what) in WANTED.items():
        n += 1; print(f'  wanted  {write(slug, wanted(title, what)):>7}B  {slug[:54]}')
    for slug, (title, what) in SERVICES.items():
        n += 1; print(f'  service {write(slug, service(title, what)):>7}B  {slug[:54]}')
    for slug, (title, what, links, note) in ELSEWHERE.items():
        n += 1; print(f'  link    {write(slug, elsewhere(title, what, links, note)):>7}B  {slug[:54]}')
    print(f'\n{n} product pages written')

if __name__ == '__main__':
    main()
