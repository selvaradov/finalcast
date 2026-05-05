"""
Sync copy from web/copy/*.md into index.html.

Usage: python web/build.py

Reads section notes and descriptions from copy/*.md and updates
the corresponding text in index.html. This lets you edit the prose
in markdown without touching the HTML structure.

Each replaceable block in index.html is marked with:
  <!-- copy:filename.section-slug -->text here<!-- /copy -->

Run this script after editing any copy/*.md file.
"""

import re
from pathlib import Path

WEB = Path(__file__).parent
COPY_DIR = WEB / 'copy'
INDEX = WEB / 'index.html'


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def parse_md(content):
    """Parse markdown into sections keyed by slug of heading."""
    sections = {}
    current = 'intro'
    sections[current] = []

    for line in content.split('\n'):
        if line.startswith('# ') and current == 'intro':
            continue  # skip top-level heading
        elif line.startswith('## '):
            current = slugify(line[3:].strip())
            sections[current] = []
        elif line.startswith('# '):
            continue
        else:
            sections[current].append(line)

    # Clean trailing empty lines
    for k in sections:
        while sections[k] and not sections[k][-1].strip():
            sections[k].pop()
        sections[k] = '\n'.join(sections[k]).strip()

    return sections


def build():
    copy = {}
    for f in COPY_DIR.glob('*.md'):
        copy[f.stem] = parse_md(f.read_text())

    html = INDEX.read_text()

    # Replace <!-- copy:file.section -->...<!-- /copy --> blocks
    def replacer(m):
        key = m.group(1)  # e.g. "overview.firsts"
        file_key, section_key = key.split('.', 1)
        sections = copy.get(file_key, {})
        new_text = sections.get(section_key, None)
        if new_text is not None:
            return f'<!-- copy:{key} -->{new_text}<!-- /copy -->'
        print(f"  WARNING: no copy found for {key}")
        return m.group(0)

    new_html = re.sub(
        r'<!-- copy:([^ ]+) -->.*?<!-- /copy -->',
        replacer,
        html,
        flags=re.DOTALL
    )

    if new_html != html:
        INDEX.write_text(new_html)
        n = len(re.findall(r'<!-- copy:', new_html))
        print(f"Updated {n} copy blocks in index.html")
    else:
        print("No changes needed")


if __name__ == '__main__':
    build()
