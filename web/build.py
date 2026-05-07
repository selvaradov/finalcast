"""
Build index.html from template.html + copy/*.md.

Usage: python web/build.py

Reads template.html (HTML structure with empty copy placeholders) and
fills in prose content from copy/*.md files to produce index.html.

Two slot types:
  <!-- copy:filename.section-slug --><!-- /copy -->
    Injects raw text from the markdown section.
  <!-- copy-html:filename.section-slug --><!-- /copy-html -->
    Renders the markdown section to HTML via mistune.

The .md files use ## headings to define sections (slugified to match).
Content before the first ## heading goes into the "intro" slot.
A special "body" section collects everything after the H1 (all ##+ sections).

Run this script after editing any copy/*.md file or template.html.
"""

import re
from pathlib import Path

import mistune

WEB = Path(__file__).parent
COPY_DIR = WEB / 'copy'
TEMPLATE = WEB / 'template.html'
INDEX = WEB / 'index.html'

md_render = mistune.create_markdown(plugins=['table'], escape=False)


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def parse_md(content):
    """Parse markdown into sections keyed by slug of heading."""
    sections = {}
    current = 'intro'
    sections[current] = []
    body_lines = []

    for line in content.split('\n'):
        if line.startswith('# ') and current == 'intro':
            continue
        elif line.startswith('## '):
            current = slugify(line[3:].strip())
            sections[current] = []
            body_lines.append(line)
        elif line.startswith('# '):
            continue
        else:
            sections[current].append(line)
            body_lines.append(line)

    for k in sections:
        while sections[k] and not sections[k][-1].strip():
            sections[k].pop()
        sections[k] = '\n'.join(sections[k]).strip()

    sections['body'] = '\n'.join(body_lines).strip()
    return sections


def build():
    copy = {}
    for f in COPY_DIR.glob('*.md'):
        copy[f.stem] = parse_md(f.read_text())

    html = TEMPLATE.read_text()

    def replacer(m):
        key = m.group(1)
        file_key, section_key = key.split('.', 1)
        sections = copy.get(file_key, {})
        new_text = sections.get(section_key, None)
        if new_text is not None:
            return f'<!-- copy:{key} -->{new_text}<!-- /copy -->'
        print(f"  WARNING: no copy found for {key}")
        return m.group(0)

    def html_replacer(m):
        key = m.group(1)
        file_key, section_key = key.split('.', 1)
        sections = copy.get(file_key, {})
        new_text = sections.get(section_key, None)
        if new_text is not None:
            rendered = md_render(new_text)
            return f'<!-- copy-html:{key} -->\n{rendered}<!-- /copy-html -->'
        print(f"  WARNING: no copy found for {key}")
        return m.group(0)

    new_html = re.sub(
        r'<!-- copy:([^ ]+) -->.*?<!-- /copy -->',
        replacer,
        html,
        flags=re.DOTALL
    )
    new_html = re.sub(
        r'<!-- copy-html:([^ ]+) -->.*?<!-- /copy-html -->',
        html_replacer,
        new_html,
        flags=re.DOTALL
    )

    INDEX.write_text(new_html)
    n_text = len(re.findall(r'<!-- copy:', new_html))
    n_html = len(re.findall(r'<!-- copy-html:', new_html))
    print(f"Built index.html ({n_text - n_html} text + {n_html} html blocks filled)")


if __name__ == '__main__':
    build()
