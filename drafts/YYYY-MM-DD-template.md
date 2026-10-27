# Post title

<!--
Template: copy it to drafts/slug.md, write the post, delete these comments.
Comments are ignored by Telegram and not counted in the length.

- Keep the text under ~1000 characters: with an image it becomes the caption
  of the photo (limit 1024). Without an image the limit
  is 4096, so the image line can be removed.
- Check the result with: python3 build.py --check drafts/slug.md
  The check fails until the image file exists in images/.
- When it is ready: git mv drafts/slug.md posts/YYYY-MM-DD-slug.md
-->

![image description](../images/image-name.jpg)

A paragraph of plain text. Paragraphs are separated by a blank line.

Text can be **bold** or *italic*, and it can contain a [link](https://example.com).

<!-- End a line with two spaces to break the line without starting a new paragraph. -->

A line that ends with two spaces,  
followed by the next line of the same paragraph.

> A quote. It can span several lines
> and it is shown as a block quote on Telegram.

<!-- A bullet list and a numbered list need a line of text between them, or Markdown merges them into one list. -->

A bullet list:

- first point
- second point

A numbered list:

1. first step
2. second step

Some `inline code`, and a code block with its language:

```python
def hello():
    print("hello")
```

<!-- A link on its own line works as a source or reference. -->

[Source name](https://example.com)
