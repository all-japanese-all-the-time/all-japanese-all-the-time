# Restore the original `/blog/` URL scheme, and repair the archive

The site this mirrors lived at `alljapaneseallthetime.com/blog/`, not at the
domain root. HTTrack was pointed at `/blog/` and rooted the copy there, so every
slug landed flat on disk and the prefix was lost before the first commit — it was
never a directory in this repo, so this is not undoing an earlier change.

Restoring it means an old link needs only its domain swapped to work again:

    alljapaneseallthetime.com/blog/example/index.html
    alljapanesealltheti.me/blog/example/index.html

**No existing link breaks.** Every pre-move URL keeps working via a redirect, so
nothing outside this repository has to be updated on merge day.

## Headline numbers

| | before | after |
|---|---:|---:|
| broken internal references | 21,233 | **176** |
| posts | 1,172 | **1,291** |
| distinct missing link targets | 2,170 | ~95 |

## What changed

**The move** — 5,775 pure renames, no file content touched, verified by comparing
the complete blob set against master.

**Recovery** — 119 pages restored from the Wayback Machine, including 22
Japanese-titled posts that had been dead links from across the archive, plus 38
images. Snapshots span 2007–2023 across three themes; the older ones are
re-wrapped in the current theme so the archive is visually consistent.

**Repairs** — 25,506 root-relative links prefixed, 3,520 over-dotted CDN links
made absolute (Font Awesome had been missing sitewide), 621 `slug.html` links
repointed, 532 theme assets pointed at their mirrored copies, and 12 pages that
were **gzip served as `text/html`** decompressed — production had been returning
binary with a 200 status, which no link checker flags.

**Redirects** — 1,780 stubs, ~1.5 MB, at every pre-move URL. `location.replace()`
so the Back button still works, `<meta refresh>` as the no-JS fallback, query
strings and fragments carried across, `canonical` pointing at the real page.

**Search** — the theme's existing search box now works. Titles are filtered
client-side from a 38 kB index (instant, offline). The results page additionally
consults a full-text API and falls back to titles, saying so, when that is
unreachable. Includes spelling correction and phrase-proximity matching.

**Cleanup** — dead WordPress endpoints, oEmbed tags, ad rotators and never-mirrored
plugin assets removed; comment and password forms unwrapped so the boxes still
render but cannot post to endpoints that no longer exist.

## Deliberate decisions

- `0-AJATT-Products/` and `table-of-contents/` stay at the root — they were never
  URLs on the original site.
- Feeds get no redirect stub: HTML served where a reader expects RSS is worse
  than a 404.
- Product pages that exist nowhere, not even in the Internet Archive, get a page
  saying so and asking for copies. They state plainly that the text is from the
  archive's maintainers, not original AJATT material.

## Still open

~176 references to pages that were never archived anywhere. `audit/DEAD-PAGES.md`
lists them with full original URLs, Wayback lookup links, and how many distinct
pages link to each, so the few that matter can be told from the long tail.
