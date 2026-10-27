# Le pometki di Paolo

A weekly curiosity column, published as an RSS feed at
<https://electricant.github.io/pometki/feed.xml> and as posts on the
Telegram channel <https://t.me/+pm5yqpHBmiFjYTI8>.

[![Publish](https://github.com/electricant/pometki/actions/workflows/publish.yml/badge.svg?branch=master)](https://github.com/electricant/pometki/actions/workflows/publish.yml)

## Layout

- `drafts/`: work in progress, never published.
- `posts/`: published posts, named `YYYY-MM-DD-slug.md`. The date is the one
  shown in the feed and sets the order of the posts.
- `images/`: pictures, referenced from posts as `../images/name.jpg`.
- `build.py`: builds `_site/` (the feed and the images) and sends posts to
  Telegram.
- `.github/workflows/publish.yml`: runs on every push to `main`.

## Post format

Text is written in markdown. Each page must begin with a `# Title` line.
Images are written as `![description](../images/name.jpg)`. The first image
becomes the photo of the Telegram message, whose caption is limited to 1024
characters (4096 for posts without an image). On Telegram, headings become
bold, lists become bullet lines, and quotes, code blocks and line breaks (a line
ending with two spaces) are kept. Tables and further images are reduced to plain
text or dropped, and so are nested lists, which are not supported yet. A bullet
list and a numbered list must be separated by a line of text, or they merge.

## Publishing

1. Write in `drafts/` and check the result in the GitHub preview.
2. Move it into `posts/` with today's date:
   `git mv drafts/slug.md posts/YYYY-MM-DD-slug.md`
   (in the GitHub web editor, rename the file to `../posts/YYYY-MM-DD-slug.md`).
3. Commit and push to `main`. The workflow deploys the site and then sends
   every post that was added to `posts/` or moved there from `drafts/`.

**NOTE:** Re-running a failed workflow run resends every new post of that push.

## Local build

    pip install -r requirements.txt
    python3 build.py
    python3 build.py --check drafts/slug.md
    DRY_RUN=1 python3 build.py --post posts/YYYY-MM-DD-slug.md

`--check` works on drafts and published posts and never sends anything.
`DRY_RUN=1` prints the full Telegram request instead of sending it.
