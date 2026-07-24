#!/usr/bin/env python3
"""
Regenerate the "Latest posts" section of a GitHub profile README from the
markdown posts in this blog repo.

Idempotent & incremental:
- The list is always fully rebuilt from the post files on disk (the source
  of truth), not appended to, so re-running never duplicates entries and
  always reflects the current top N posts.
- The section lives between two HTML marker comments. If the markers
  aren't found yet (first run), the section is appended at the end of the
  README. On every later run, the existing section between the markers is
  replaced in place.
- If nothing changed, the README is left untouched (byte-identical),
  so the workflow can skip the commit step.

Adjust the CONFIG block below to match your setup.
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

# ----------------------------- CONFIG -------------------------------------
POSTS_DIR = Path("content/posts")                       # where .md posts live
# profile repo checked out here
README_PATH = Path("profile-repo/README.md")
SITE_BASE_URL = "https://hyperphantasia.github.io"      # <-- change
PERMALINK_FMT = "{base}/{year}/{month:02d}/{day:02d}/{slug}/"
MAX_POSTS = 3
# ----------------------------------------------------------------------------

START_MARKER = "<!-- LATEST_POSTS:START -->"
END_MARKER = "<!-- LATEST_POSTS:END -->"

FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*['\"]?(.*?)['\"]?\s*$", re.MULTILINE)
DATE_RE = re.compile(r"^date:\s*['\"]?([\d-]{10})")


def parse_post(path: Path):
    m = FILENAME_RE.match(path.name)
    if not m:
        return None
    year, month, day, slug = m.groups()
    post_date = date(int(year), int(month), int(day))

    text = path.read_text(encoding="utf-8")
    title = slug.replace("-", " ").title()

    fm_match = FRONT_MATTER_RE.match(text)
    if fm_match:
        fm = fm_match.group(1)
        title_match = TITLE_RE.search(fm)
        if title_match:
            title = title_match.group(1).strip()
        date_match = DATE_RE.search(fm)
        if date_match:
            try:
                post_date = datetime.strptime(
                    date_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass

    url = PERMALINK_FMT.format(
        base=SITE_BASE_URL,
        year=post_date.year,
        month=post_date.month,
        day=post_date.day,
        slug=slug,
    )
    return {"title": title, "date": post_date, "url": url}


def collect_posts():
    if not POSTS_DIR.exists():
        return []
    posts = [p for p in (parse_post(f) for f in POSTS_DIR.glob("*.md")) if p]
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build_section(posts):
    lines = [START_MARKER, "", "*Latest posts:*", ""]
    if not posts:
        lines.append("_No posts yet._")
    else:
        for post in posts[:MAX_POSTS]:
            lines.append(
                f"- [{post['title']}]({post['url']}) — {post['date'].isoformat()}")
    lines += ["", END_MARKER]
    return "\n".join(lines)


def update_readme(section: str) -> bool:
    content = README_PATH.read_text(
        encoding="utf-8") if README_PATH.exists() else ""

    if START_MARKER in content and END_MARKER in content:
        pattern = re.compile(re.escape(START_MARKER) +
                             r".*?" + re.escape(END_MARKER), re.DOTALL)
        new_content = pattern.sub(section, content)
    else:
        new_content = (content.rstrip("\n") +
                       "\n\n" if content.strip() else "") + section + "\n"

    if new_content == content:
        print("No changes needed.")
        return False

    README_PATH.write_text(new_content, encoding="utf-8")
    print("README updated.")
    return True


def main():
    posts = collect_posts()
    section = build_section(posts)
    update_readme(section)
    sys.exit(0)


if __name__ == "__main__":
    main()
