"""Le pometki di Paolo: builds the site and RSS feed from the posts and sends
new posts to Telegram.

Usage:
  python3 build.py                     build _site/ (feed.xml, images/)
  python3 build.py --post FILE.md ...  send the given posts to Telegram
  python3 build.py --check FILE.md ... check posts or drafts before publishing:
                                       print the Telegram text and its length

Each published post is a file posts/YYYY-MM-DD-slug.md. Its first line is
"# Title"; the rest is plain Markdown. Images live in images/ and are written
as ![description](../images/photo.jpg): the relative path works both in the
GitHub preview and when sending to Telegram. The first image of a post
becomes the photo of the Telegram message.
Drafts live in drafts/ and are never published.
"""
import datetime
import email.utils
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import markdown

BASE_URL = "https://electricant.github.io/pometki/"
TIMEZONE = ZoneInfo("Europe/Rome")

# Shown on the page and in the feed; the content is in Italian
TITLE = "Le pometki di Paolo"
TAGLINE = "Una curiosità a settimana: annotazioni prese al volo leggendo."
# Web view of the public Telegram channel, used as the feed's home page
CHANNEL_URL = "https://t.me/+pm5yqpHBmiFjYTI8"
OUTPUT_DIR = pathlib.Path("_site")

# Telegram limits: 1024 characters for a photo caption, 4096 for a message
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096


class TelegramHTML(HTMLParser):
    """Reduce the HTML produced by Markdown to the tags Telegram accepts.

    Bold, italic, strikethrough, code, code blocks, quotes, line breaks and
    links are kept; headings become bold; list items become lines starting
    with a bullet. The first image is removed from the text and stored in
    self.image.
    """
    INLINE_TAGS = {"b", "strong", "i", "em", "s", "del", "code"}
    HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    BLOCKS = {"p", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.image = None
        self._in_ol = False
        self._ol_counter = 0
        self._in_pre = False
        self._quote_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "code" and attrs.get("class", "").startswith("language-"):
            self.parts.append(f'<code class="{html.escape(attrs["class"])}">')
        elif tag in self.INLINE_TAGS:
            self.parts.append(f"<{tag}>")
        elif tag == "a":
            self.parts.append(f'<a href="{html.escape(attrs.get("href", ""))}">')
        elif tag in self.HEADINGS:
            self.parts.append("<b>")
        elif tag == "ol":
            self._in_ol = True
            self._ol_counter = 0
        elif tag == "li":
            if self._in_ol:
                self._ol_counter += 1
                self.parts.append(f"{self._ol_counter}. ")
            else:
                self.parts.append("• ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "blockquote":
            # Telegram does not allow a quote inside a quote: only the
            # outermost one is kept
            self._quote_depth += 1
            if self._quote_depth == 1:
                self.parts.append("<blockquote>")
        elif tag == "pre":
            self._in_pre = True
            self.parts.append("<pre>")
        elif tag == "img" and self.image is None:
            self.image = attrs.get("src")

    def handle_endtag(self, tag):
        if tag in self.INLINE_TAGS or tag == "a":
            self.parts.append(f"</{tag}>")
        elif tag == "blockquote":
            if self._quote_depth == 1:
                self._drop_trailing_newlines()
                self.parts.append("</blockquote>\n\n")
            self._quote_depth -= 1
        elif tag == "pre":
            self._in_pre = False
            self.parts.append("</pre>\n\n")
        elif tag in self.HEADINGS:
            self.parts.append("</b>\n\n")
        elif tag == "ol":
            self._in_ol = False
            self.parts.append("\n\n")
        elif tag in self.BLOCKS:
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("\n")

    def _drop_trailing_newlines(self):
        while self.parts and not self.parts[-1].strip("\n"):
            self.parts.pop()

    def handle_data(self, data):
        # Code blocks keep their line breaks, minus the one Markdown adds
        # at the end
        if self._in_pre:
            self.parts.append(html.escape(data.rstrip("\n"), quote=False))
            return
        # Newlines between blocks are only formatting of the HTML source
        if "\n" in data and not data.strip():
            return
        text = data.replace("\n", " ")
        # Markdown writes a newline after <br />: do not turn it into a space
        if self.parts[-1:] == ["\n"]:
            text = text.lstrip()
        self.parts.append(html.escape(text, quote=False))

    def text(self):
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def read_post(path, require_date=True):
    """Read a post. Drafts have no date in their name: pass require_date=False."""
    path = pathlib.Path(path)
    dated = re.fullmatch(r"\d{4}-\d{2}-\d{2}-.+", path.stem)
    if require_date and not dated:
        sys.exit(f"{path}: file name must start with the date YYYY-MM-DD-")
    first_line, _, body = path.read_text(encoding="utf-8").partition("\n")
    if not first_line.startswith("# "):
        sys.exit(f"{path}: first line must be '# Title'")
    return {
        "path": path,
        "slug": path.stem,
        "date": datetime.date.fromisoformat(path.stem[:10]) if dated else None,
        "title": first_line[2:].strip(),
        "html": markdown.markdown(body, extensions=["fenced_code"]),
    }


def all_posts():
    """All published posts, newest first."""
    posts = [read_post(p) for p in pathlib.Path("posts").glob("*.md")]
    return sorted(posts, key=lambda p: p["slug"], reverse=True)


def post_html(post):
    # Image paths are relative to the post file (../images/). In the feed
    # they become absolute URLs so that feed readers can load them.
    return post["html"].replace('src="../images/', f'src="{BASE_URL}images/')


def build():
    posts = all_posts()
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    shutil.copytree("images", OUTPUT_DIR / "images")

    # Each item is complete in itself: the text is in <description>, so
    # there is no <link>, and the guid is a plain identifier, not a URL
    items = []
    for p in posts:
        published = datetime.datetime.combine(p["date"], datetime.time(9), TIMEZONE)
        items.append(f"""<item><title>{html.escape(p['title'], quote=False)}</title>
<guid isPermaLink="false">{p['slug']}</guid>
<pubDate>{email.utils.format_datetime(published)}</pubDate>
<description>{html.escape(post_html(p))}</description></item>""")
    (OUTPUT_DIR / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{TITLE}</title>
<link>{CHANNEL_URL}</link><description>{TAGLINE}</description>
<language>it</language>
{chr(10).join(items)}
</channel></rss>
""", encoding="utf-8")
    print(f"Built {len(posts)} posts into {OUTPUT_DIR}/")


def send_to_telegram(path, check=False):
    """Send a post to Telegram. With check=True, only verify it: print the
    text and its length against the limit, and send nothing."""
    post = read_post(path, require_date=not check)
    parser = TelegramHTML()
    parser.feed(post["html"])
    text = f"<b>{html.escape(post['title'], quote=False)}</b>\n\n{parser.text()}"

    # The count includes HTML tags, so the check is conservative
    limit = CAPTION_LIMIT if parser.image else MESSAGE_LIMIT
    if check:
        print(text)
        print(f"\n{path}: {len(text)} of {limit} characters"
              + (", with photo" if parser.image else ", no photo"))
    if len(text) > limit:
        sys.exit(f"{path}: text is {len(text)} characters, limit is {limit}")
    if check:
        if parser.image:
            photo = post["path"].parent / parser.image
            if not photo.is_file():
                sys.exit(f"{path}: image not found: {photo}")
        print("OK: the post can be published")
        return

    api = f"https://api.telegram.org/bot{os.environ.get('TG_TOKEN', '')}/"
    # --form-string sends values literally: with -F a value starting with
    # "<" or "@" would be read as a file name
    cmd = ["curl", "-sS", "--fail",
           "--form-string", f"chat_id={os.environ.get('TG_CHAT', '')}",
           "--form-string", "parse_mode=HTML"]
    if parser.image:
        photo = os.path.normpath(post["path"].parent / parser.image)
        cmd += ["--form-string", f"caption={text}", "-F", f"photo=@{photo}",
                api + "sendPhoto"]
    else:
        cmd += ["--form-string", f"text={text}", api + "sendMessage"]

    if os.environ.get("DRY_RUN"):
        print(cmd[3:-1])
    else:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        print(f"Sent {path}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--post"]:
        for file in sys.argv[2:]:
            send_to_telegram(file)
    elif sys.argv[1:2] == ["--check"]:
        for file in sys.argv[2:]:
            send_to_telegram(file, check=True)
    else:
        build()
