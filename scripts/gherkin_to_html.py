#!/usr/bin/env python3
"""Render a project's Gherkin files, as they are, into one easy-to-read HTML page.

Shipped with the gherkin-bdd skill so anyone on the project can read what the
application does without opening individual ``.feature`` files. Stdlib-only:
it scans the project for ``*.feature`` files (skipping hidden and dependency
directories), parses the common Gherkin constructs — Feature, Rule, Background,
Scenario, Scenario Outline, steps, tags, data tables, doc strings, Examples —
for English and Simplified Chinese (``# language: zh-CN``), and writes a single
self-contained HTML page: no server, no network, no external assets. Nothing is
summarized or left out.

A file that cannot be parsed as Gherkin is still listed, shown as plain text
with a parse warning, so the page never hides a spec.

Usage:

    python3 gherkin_to_html.py [--project-dir DIR] [--out FILE]

The default output is ``<project-dir>/docs/gherkin.html``. The ``docs``
directory is created when it does not already exist.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUT = "gherkin.html"
DEFAULT_OUT_DIR = "docs"
EXCLUDED_DIRS = {"node_modules", "__pycache__", "venv", "vendor", "dist", "build", "target"}

LANGUAGE_PATTERN = re.compile(r"^#\s*language\s*:\s*([\w-]+)", re.IGNORECASE)

ENGLISH_SECTION_KEYWORDS = {
    "Feature": "Feature",
    "Rule": "Rule",
    "Background": "Background",
    "Scenario Outline": "Scenario Outline",
    "Scenario Template": "Scenario Outline",
    "Scenarios": "Examples",
    "Scenario": "Scenario",
    "Examples": "Examples",
    "Example": "Scenario",
}
ENGLISH_STEP_KEYWORDS = {
    "Given": "Given",
    "When": "When",
    "Then": "Then",
    "And": "And",
    "But": "But",
    "*": "*",
}
ZH_CN_SECTION_KEYWORDS = {
    "功能": "Feature",
    "Rule": "Rule",
    "规则": "Rule",
    "背景": "Background",
    "场景大纲": "Scenario Outline",
    "剧本大纲": "Scenario Outline",
    "场景": "Scenario",
    "剧本": "Scenario",
    "例子": "Examples",
}
ZH_CN_STEP_KEYWORDS = {
    "假如": "Given",
    "假设": "Given",
    "假定": "Given",
    "当": "When",
    "那么": "Then",
    "而且": "And",
    "并且": "And",
    "同时": "And",
    "但是": "But",
    "*": "*",
}
LANGUAGE_KEYWORDS = {
    "en": (ENGLISH_SECTION_KEYWORDS, ENGLISH_STEP_KEYWORDS),
    "en-us": (ENGLISH_SECTION_KEYWORDS, ENGLISH_STEP_KEYWORDS),
    "en-gb": (ENGLISH_SECTION_KEYWORDS, ENGLISH_STEP_KEYWORDS),
    "zh-cn": (ZH_CN_SECTION_KEYWORDS, ZH_CN_STEP_KEYWORDS),
}


class GherkinParseError(ValueError):
    pass


@dataclass
class Step:
    keyword: str
    phase: str
    text: str
    table: list[list[str]] = field(default_factory=list)
    doc_string: str | None = None


@dataclass
class Examples:
    name: str
    keyword: str = "Examples"
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Block:
    kind: str  # "Background", "Scenario", "Scenario Outline", or "Rule"
    keyword: str
    name: str
    tags: list[str] = field(default_factory=list)
    description: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    examples: list[Examples] = field(default_factory=list)


@dataclass
class FeatureDoc:
    path: str
    name: str = ""
    keyword: str = "Feature"
    tags: list[str] = field(default_factory=list)
    description: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    error: str | None = None
    raw: str = ""

    @property
    def scenario_count(self) -> int:
        return sum(1 for b in self.blocks if b.kind in ("Scenario", "Scenario Outline"))

    @property
    def outline_count(self) -> int:
        return sum(1 for b in self.blocks if b.kind == "Scenario Outline")

    @property
    def step_count(self) -> int:
        return sum(len(b.steps) for b in self.blocks)

    @property
    def examples_count(self) -> int:
        return sum(max(len(ex.rows) - 1, 0) for b in self.blocks for ex in b.examples)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"Not a directory: {project_dir}")
    feature_files = find_feature_files(project_dir)
    out = Path(args.out) if args.out else default_output_path(project_dir, feature_files)
    docs = [parse_feature_file(path, project_dir) for path in feature_files]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_page(project_dir.name, docs), encoding="utf-8")
    print(f"Gherkin HTML: {out}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gherkin_to_html",
        description="Render the project's Gherkin files into one self-contained HTML page.",
    )
    parser.add_argument("--project-dir", default=".", help="Project to scan (default: current directory).")
    parser.add_argument(
        "--out",
        default=None,
        help=f"Output file (default: <project-dir>/{DEFAULT_OUT_DIR}/{DEFAULT_OUT}).",
    )
    return parser.parse_args(argv)


# --- Discovery ----------------------------------------------------------------


def find_feature_files(project_dir: Path) -> list[Path]:
    """All Gherkin files, skipping hidden and dependency directories."""
    found: list[Path] = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in EXCLUDED_DIRS)
        found.extend(Path(root) / name for name in sorted(files) if name.endswith(".feature"))
    return sorted(found, key=lambda path: path.relative_to(project_dir).as_posix())


def default_output_path(project_dir: Path, _feature_files: list[Path]) -> Path:
    """Default generated reader location."""
    return project_dir / DEFAULT_OUT_DIR / DEFAULT_OUT


# --- Parsing ------------------------------------------------------------------


def parse_feature_file(path: Path, project_dir: Path) -> FeatureDoc:
    rel = path.relative_to(project_dir).as_posix()
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return FeatureDoc(path=rel, error=f"could not be read ({error})")
    try:
        return parse_gherkin(rel, raw)
    except GherkinParseError as error:
        return FeatureDoc(path=rel, error=str(error), raw=raw)


def parse_gherkin(rel: str, raw: str) -> FeatureDoc:
    doc = FeatureDoc(path=rel, raw=raw)
    pending_tags: list[str] = []
    block: Block | None = None
    examples: Examples | None = None
    feature_seen = False
    language = "en"
    section_keywords, step_keywords = LANGUAGE_KEYWORDS[language]

    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        index += 1
        if not stripped:
            continue
        if stripped.startswith("#"):
            language_match = LANGUAGE_PATTERN.match(stripped)
            if language_match:
                language = language_match.group(1).lower()
                if language not in LANGUAGE_KEYWORDS:
                    raise GherkinParseError(
                        f"declares language '{language_match.group(1)}'; supported languages are en and zh-CN"
                    )
                section_keywords, step_keywords = LANGUAGE_KEYWORDS[language]
            continue
        if stripped.startswith("@"):
            pending_tags.extend(tag for tag in stripped.split() if tag.startswith("@"))
            continue
        if stripped[:3] in ('"""', "```"):
            index, text = read_doc_string(lines, index, stripped[:3])
            if block is not None and block.steps:
                block.steps[-1].doc_string = text
            continue
        if stripped.startswith("|"):
            cells = split_table_row(stripped)
            if examples is not None:
                examples.rows.append(cells)
            elif block is not None and block.steps:
                block.steps[-1].table.append(cells)
            continue

        section = match_section(stripped, section_keywords)
        if section:
            keyword, canonical, title = section
            if canonical == "Feature":
                if feature_seen:
                    raise GherkinParseError(f"holds more than one {keyword}: header")
                feature_seen = True
                doc.name, doc.keyword, doc.tags, pending_tags = title, keyword, pending_tags, []
            elif canonical == "Examples":
                examples = Examples(name=title, keyword=keyword)
                if block is not None:
                    block.examples.append(examples)
                continue
            else:
                if not feature_seen:
                    raise GherkinParseError(f"opens with {keyword}: before any Feature: header")
                block = Block(kind=canonical, keyword=keyword, name=title, tags=pending_tags)
                pending_tags = []
                doc.blocks.append(block)
            examples = None
            continue

        step = match_step(stripped, step_keywords)
        if step and block is not None:
            keyword, phase, text = step
            block.steps.append(Step(keyword=keyword, phase=phase, text=text))
            examples = None
            continue

        # Plain prose: a description for whatever is currently open.
        if block is not None:
            block.description.append(stripped)
        elif feature_seen:
            doc.description.append(stripped)
        else:
            raise GherkinParseError("starts with text that is not Gherkin")

    if not feature_seen:
        raise GherkinParseError("has no Feature: header")
    return doc


def match_section(
    stripped: str, section_keywords: dict[str, str]
) -> tuple[str, str, str] | None:
    for keyword in sorted(section_keywords, key=len, reverse=True):
        prefix = f"{keyword}:"
        if stripped.startswith(prefix):
            return keyword, section_keywords[keyword], stripped[len(prefix) :].strip()
    return None


def match_step(stripped: str, step_keywords: dict[str, str]) -> tuple[str, str, str] | None:
    for keyword in sorted(step_keywords, key=len, reverse=True):
        if keyword == "*":
            if stripped.startswith("* "):
                return keyword, step_keywords[keyword], stripped[2:].strip()
            continue
        prefix = f"{keyword} "
        if stripped.startswith(prefix):
            return keyword, step_keywords[keyword], stripped[len(prefix) :].strip()
    return None


def read_doc_string(lines: list[str], index: int, delimiter: str) -> tuple[int, str]:
    collected: list[str] = []
    while index < len(lines) and lines[index].strip()[:3] != delimiter:
        collected.append(lines[index])
        index += 1
    return index + 1, textwrap.dedent("\n".join(collected))


def split_table_row(stripped: str) -> list[str]:
    return [cell.strip() for cell in stripped.strip("|").split("|")]


# --- Rendering ----------------------------------------------------------------


def render_page(project_name: str, docs: list[FeatureDoc]) -> str:
    scenario_total = sum(doc.scenario_count for doc in docs)
    if docs:
        summary = f"{len(docs)} Gherkin file{'s' if len(docs) != 1 else ''}, {scenario_total} scenario{'s' if scenario_total != 1 else ''}"
        body = f"{render_tabs(docs)}\n<main class=\"content\" id=\"content\">\n{''.join(render_feature(doc, index == 0) for index, doc in enumerate(docs))}<p class=\"empty search-empty\" hidden data-i18n=\"emptySearch\">No matching scenarios.</p></main>"
    else:
        summary = "0 Gherkin files"
        body = (
            '<main class="content"><p class="empty" data-i18n="emptyProject">This project has no Gherkin files yet. '
            "Describe a behavior in a <code>.feature</code> file and regenerate this page.</p></main>"
        )
    return PAGE_TEMPLATE.format(
        title=esc(f"Gherkin Reader - {project_name}"),
        project=esc(project_name),
        summary=esc(summary),
        style=STYLE,
        body=body,
        script=APP_SCRIPT if docs else "",
    )


def render_tabs(docs: list[FeatureDoc]) -> str:
    items = []
    for index, doc in enumerate(docs):
        label = esc(Path(doc.path).name)
        note = "could not be parsed" if doc.error else plural_scenarios(doc.scenario_count)
        active = " active" if index == 0 else ""
        items.append(
            f'<a class="tab{active}" href="#{slug(doc.path)}" data-feature-tab data-target="{slug(doc.path)}" '
            f'data-feature-name="{search_attr(doc.path + " " + (doc.name or ""))}" aria-current="{"page" if index == 0 else "false"}">'
            f'<span class="tab-name">{label}</span>'
            f'<span class="tab-badge">{doc.scenario_count}</span>'
            f'<span class="tab-matchdot" hidden></span>'
            f'<small>{esc(note)}</small></a>'
        )
    return '<nav class="tabs" aria-label="Gherkin files">\n' + "\n".join(items) + "\n</nav>"


def plural_scenarios(count: int) -> str:
    return f"{count} scenario{'s' if count != 1 else ''}"


def render_feature(doc: FeatureDoc, active: bool = False) -> str:
    active_class = " active" if active else ""
    hidden = "" if active else " hidden"
    if doc.error:
        return (
            f'<section class="feature-panel unparsed{active_class}" id="{slug(doc.path)}" data-feature-panel '
            f'data-feature-name="{search_attr(doc.path)}"{hidden}>\n'
            f"<header class=\"feature-head\"><h1 class=\"feature-title\"><span class=\"feature-kw\" data-i18n=\"fileLabel\">File</span>{esc(doc.path)}</h1></header>\n"
            f'<p class="warning">This file could not be parsed as Gherkin: it {esc(doc.error)}. '
            "Shown as plain text.</p>\n"
            f"<pre>{esc(doc.raw)}</pre>\n</section>\n"
        )
    parts = [
        f'<section class="feature-panel{active_class}" id="{slug(doc.path)}" data-feature-panel '
        f'data-feature-name="{search_attr(doc.path + " " + doc.name + " " + " ".join(doc.tags) + " " + " ".join(doc.description))}"{hidden}>',
        '<header class="feature-head">',
    ]
    parts.append(render_tags(doc.tags))
    parts.append(
        f'<h1 class="feature-title">{keyword_span("feature-kw", doc.keyword)}{esc(doc.name)}</h1>'
    )
    parts.append(f'<p class="path"><code>{esc(doc.path)}</code></p>')
    parts.append(render_description(doc.description))
    parts.append(render_stats(doc))
    parts.append('<p class="search-status" hidden data-search-status></p>')
    parts.append("</header>")
    parts.extend(render_block(block) for block in doc.blocks)
    parts.append("</section>\n")
    return "\n".join(filter(None, parts))


def render_stats(doc: FeatureDoc) -> str:
    parts = [
        '<div class="stats">',
        stat_pill(doc.scenario_count, "scenarios", "Scenarios"),
    ]
    if doc.outline_count:
        parts.append(stat_pill(doc.outline_count, "outlines", "Outlines"))
    parts.append(stat_pill(doc.step_count, "steps", "Steps"))
    if doc.examples_count:
        parts.append(stat_pill(doc.examples_count, "examples", "Examples"))
    parts.append(
        '<span class="stats-spacer"></span>'
        '<span class="expand-controls">'
        '<button type="button" data-expand="all" data-i18n="expandAll">Expand all</button>'
        '<span class="divider"></span>'
        '<button type="button" data-collapse="all" data-i18n="collapseAll">Collapse all</button>'
        "</span></div>"
    )
    return "".join(parts)


def stat_pill(value: int, key: str, label: str) -> str:
    return (
        '<span class="stat-pill">'
        f'<span class="stat-value">{value}</span>'
        f'<span class="stat-label" data-i18n="{key}">{label}</span>'
        "</span>"
    )


def render_block(block: Block) -> str:
    if block.kind == "Rule":
        heading = f'<h2 class="rule">{keyword_span("kind", block.keyword)}: {esc(block.name)}</h2>'
        return heading + render_description(block.description)
    if block.kind == "Background":
        parts = ['<section class="background">']
        parts.append('<div class="background-head">')
        parts.append(keyword_span("background-kw", block.keyword))
        if block.name:
            parts.append(f'<span class="background-name">{esc(block.name)}</span>')
        parts.append("</div>")
        parts.append(render_description(block.description))
        parts.append('<div class="background-body">')
        parts.append(render_steps(block.steps))
        parts.append("</div></section>")
        return "\n".join(filter(None, parts))

    parts = [
        '<details class="scenario" data-scenario open>',
        '<summary class="scenario-head">',
        '<span class="chevron" aria-hidden></span>',
    ]
    parts.append(render_tags(block.tags))
    title = esc(block.name) if block.name else ""
    parts.append(keyword_span("scenario-kw", block.keyword))
    parts.append(f'<span class="scenario-name">{title}</span>')
    parts.append(f'<span class="scenario-meta"><span class="step-count">{len(block.steps)} <span data-i18n="stepUnit">steps</span></span></span>')
    parts.append("</summary>")
    parts.append('<div class="scenario-body">')
    parts.append(render_description(block.description))
    if block.steps:
        parts.append(render_steps(block.steps))
    parts.extend(render_examples(examples) for examples in block.examples)
    parts.append("</div></details>")
    return "\n".join(filter(None, parts))


def render_steps(steps: list[Step]) -> str:
    parts: list[str] = []
    prev_phase: str | None = None
    seen_step = False
    for step in steps:
        phase_start = False
        if step.phase in ("Given", "When", "Then"):
            if seen_step and step.phase != prev_phase:
                phase_start = True
            prev_phase = step.phase
        seen_step = True
        parts.append(render_step(step, phase_start))
    return "".join(parts)


def render_step(step: Step, phase_start: bool = False) -> str:
    css = "step phase-start" if phase_start else "step"
    parts = [
        f'<div class="{css}">',
        '<div class="step-main">',
        keyword_span(f"step-kw {kw_class(step.phase)}", step.keyword),
        f'<span class="step-text">{render_step_text(step.text)}</span>',
        "</div>",
    ]
    if step.table:
        parts.append(render_table(step.table, header=False))
    if step.doc_string is not None:
        parts.append(f'<pre class="docstring">{esc(step.doc_string)}</pre>')
    parts.append("</div>")
    return "".join(parts)


def render_examples(examples: Examples) -> str:
    title = keyword_span("", examples.keyword)
    if examples.name:
        title += f": {esc(examples.name)}"
    return (
        f'<div class="examples"><h3 class="examples-label">{title}</h3>'
        + render_table(examples.rows, header=True)
        + "</div>"
    )


def render_table(rows: list[list[str]], header: bool) -> str:
    rendered = []
    for row_index, row in enumerate(rows):
        cell_tag = "th" if header and row_index == 0 else "td"
        cells = "".join(f"<{cell_tag}>{esc(cell)}</{cell_tag}>" for cell in row)
        rendered.append(f"<tr>{cells}</tr>")
    return '<div class="table-wrap"><table class="gherkin-table">' + "".join(rendered) + "</table></div>"


def render_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    return '<p class="tags">' + " ".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags) + "</p>"


def render_description(description: list[str]) -> str:
    if not description:
        return ""
    return f'<p class="description">{esc(" ".join(description))}</p>'


def slug(rel_path: str) -> str:
    return "f-" + re.sub(r"[^a-zA-Z0-9]+", "-", rel_path).strip("-").lower()


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def search_attr(text: str) -> str:
    return esc(" ".join(text.lower().split()))


def kw_class(keyword: str) -> str:
    if keyword == "Given":
        return "kw-given"
    if keyword == "When":
        return "kw-when"
    if keyword == "Then":
        return "kw-then"
    return "kw-conj"


def keyword_span(css: str, keyword: str) -> str:
    class_attr = f' class="{esc(css)}"' if css else ""
    return f'<span{class_attr} data-gherkin-keyword="{esc(keyword)}">{esc(keyword)}</span>'


STEP_TOKEN_PATTERN = re.compile(r'("(?:[^"\\]|\\.)*"|<[^>]+>)')


def render_step_text(text: str) -> str:
    parts: list[str] = []
    last = 0
    for match in STEP_TOKEN_PATTERN.finditer(text):
        if match.start() > last:
            parts.append(esc(text[last : match.start()]))
        token = match.group(0)
        css = "tok-param" if token.startswith("<") else "tok-string"
        parts.append(f'<span class="{css}">{esc(token)}</span>')
        last = match.end()
    if last < len(text):
        parts.append(esc(text[last:]))
    return "".join(parts)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
<div class="app theme-editorial" id="app">
<header class="topbar">
<div class="brand">
<span class="brand-mark" aria-hidden="true"></span>
<div>
<h1>Gherkin Reader</h1>
<p class="summary">{summary}</p>
</div>
<span class="dir-chip" title="Project">{project}</span>
</div>
<div class="topbar-right">
<div class="search">
<span class="search-icon" aria-hidden="true">⌕</span>
<input id="filter" type="search" placeholder="Search Gherkin files or scenarios..." aria-label="Search Gherkin files or scenarios" autocomplete="off">
<button class="search-clear" type="button" aria-label="Clear" hidden>×</button>
</div>
<div class="lang-switch" role="group" aria-label="Language">
<button type="button" class="lang-btn active" data-lang="en">EN</button>
<button type="button" class="lang-btn" data-lang="zh">中</button>
</div>
<div class="style-switch" role="group" aria-label="Style">
<button type="button" class="style-btn active" data-theme="editorial">Editorial</button>
<button type="button" class="style-btn" data-theme="console">Console</button>
<button type="button" class="style-btn" data-theme="warm">Warm</button>
</div>
</div>
</header>
{body}
</div>
{script}
</body>
</html>
"""

STYLE = """
:root {
  color-scheme: light;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { min-height: 100%; margin: 0; }
body {
  font: 1rem/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.app {
  --bg: oklch(0.99 0.004 95);
  --surface: oklch(0.985 0.003 95);
  --panel: oklch(0.998 0.002 95);
  --border: oklch(0.91 0.005 95);
  --border-strong: oklch(0.83 0.007 95);
  --text: oklch(0.28 0.015 260);
  --muted: oklch(0.52 0.012 260);
  --faint: oklch(0.66 0.01 260);
  --accent: oklch(0.54 0.14 264);
  --accent-soft: oklch(0.95 0.03 264);
  --given: oklch(0.48 0.12 150);
  --when: oklch(0.5 0.13 250);
  --then: oklch(0.5 0.14 305);
  --conj: oklch(0.6 0.02 260);
  --string: oklch(0.52 0.13 55);
  --param: oklch(0.54 0.16 350);
  --tag-bg: oklch(0.96 0.025 264);
  --tag-text: oklch(0.5 0.1 264);
  --warn-bg: oklch(0.95 0.055 75);
  --warn-text: oklch(0.42 0.09 55);
  --mono: ui-monospace, SFMono-Regular, "Cascadia Code", Menlo, Consolas, monospace;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
.app.theme-console {
  --bg: oklch(0.955 0.006 250);
  --surface: oklch(0.975 0.004 250);
  --panel: oklch(0.995 0.002 250);
  --border: oklch(0.87 0.008 250);
  --border-strong: oklch(0.78 0.01 250);
  --accent: oklch(0.55 0.15 230);
  --accent-soft: oklch(0.93 0.04 230);
}
.app.theme-warm {
  --bg: oklch(0.975 0.013 75);
  --surface: oklch(0.987 0.01 78);
  --panel: oklch(0.996 0.006 80);
  --border: oklch(0.9 0.016 70);
  --border-strong: oklch(0.84 0.022 65);
  --text: oklch(0.32 0.02 50);
  --muted: oklch(0.52 0.02 55);
  --accent: oklch(0.58 0.13 48);
  --accent-soft: oklch(0.95 0.03 60);
}
a { color: inherit; }
button, input { font: inherit; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 0.8rem 1.5rem;
  background: var(--panel);
  border-bottom: thin solid var(--border);
  position: sticky;
  top: 0;
  z-index: 3;
}
.brand, .topbar-right, .search, .lang-switch, .style-switch {
  display: flex;
  align-items: center;
}
.brand { gap: 0.75rem; min-width: 16rem; }
.brand-mark {
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 0.4rem;
  background: var(--accent);
  flex: none;
  position: relative;
}
.brand-mark::after {
  content: "";
  position: absolute;
  inset: 0.38rem;
  height: 0.18rem;
  border-radius: 999rem;
  background: var(--panel);
  box-shadow: 0 0.32rem 0 var(--panel), 0 -0.06rem 0 var(--panel);
}
.brand h1 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.2;
  letter-spacing: 0;
}
.summary {
  margin: 0.1rem 0 0;
  color: var(--muted);
  font-size: 0.82rem;
}
.dir-chip {
  display: inline-flex;
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0.24rem 0.65rem;
  border-radius: 999rem;
  border: thin solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.75rem;
}
.topbar-right { gap: 0.75rem; flex-wrap: wrap; justify-content: flex-end; }
.search {
  gap: 0.45rem;
  width: min(22rem, 42vw);
  min-width: 14rem;
  padding: 0 0.75rem;
  min-height: 2.25rem;
  border-radius: 999rem;
  border: thin solid var(--border);
  background: var(--surface);
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.theme-console .search { border-radius: 0.35rem; }
.search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 0.2rem var(--accent-soft);
}
.search-icon { color: var(--faint); }
#filter {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  min-width: 0;
}
#filter::placeholder { color: var(--faint); }
.search-clear {
  border: 0;
  color: var(--muted);
  background: var(--border);
  min-width: 1.15rem;
  min-height: 1.15rem;
  border-radius: 999rem;
  cursor: pointer;
  display: grid;
  place-items: center;
  padding: 0;
}
.search-clear:hover { background: var(--border-strong); color: var(--text); }
.lang-switch, .style-switch {
  gap: 0.12rem;
  padding: 0.18rem;
  border-radius: 999rem;
  border: thin solid var(--border);
  background: var(--surface);
}
.theme-console .lang-switch, .theme-console .style-switch { border-radius: 0.35rem; }
.lang-btn, .style-btn {
  border: 0;
  background: transparent;
  cursor: pointer;
  border-radius: 999rem;
  padding: 0.34rem 0.72rem;
  color: var(--muted);
  font-weight: 700;
  font-size: 0.78rem;
  white-space: nowrap;
}
.theme-console .lang-btn, .theme-console .style-btn { border-radius: 0.22rem; }
.lang-btn:hover, .style-btn:hover { color: var(--text); }
.lang-btn.active, .style-btn.active {
  background: var(--panel);
  color: var(--accent);
  box-shadow: 0 0.05rem 0.14rem oklch(0.45 0.02 260 / 0.08);
}
.tabs {
  display: flex;
  gap: 0.25rem;
  overflow-x: auto;
  padding: 0 1rem;
  background: var(--panel);
  border-bottom: thin solid var(--border);
  scrollbar-width: thin;
  position: sticky;
  top: 3.9rem;
  z-index: 2;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: var(--muted);
  padding: 0.72rem 0.85rem;
  border-bottom: 0.15rem solid transparent;
  white-space: nowrap;
  font-family: var(--mono);
  font-size: 0.78rem;
}
.tab:hover { color: var(--text); }
.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.tab.dimmed { opacity: 0.4; }
.tab-badge {
  min-width: 1.15rem;
  min-height: 1.15rem;
  display: grid;
  place-items: center;
  padding: 0 0.3rem;
  border-radius: 999rem;
  border: thin solid var(--border);
  background: var(--surface);
  color: var(--faint);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-size: 0.66rem;
  font-weight: 800;
}
.tab small { color: var(--faint); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }
.tab.active .tab-badge { color: var(--accent); background: var(--accent-soft); border-color: transparent; }
.tab-matchdot {
  width: 0.38rem;
  height: 0.38rem;
  border-radius: 999rem;
  background: var(--accent);
}
.theme-console .tabs {
  gap: 0.12rem;
  padding: 0.36rem 0.75rem 0;
}
.theme-console .tab {
  border: thin solid transparent;
  border-bottom: 0;
  border-radius: 0.35rem 0.35rem 0 0;
  padding: 0.55rem 0.8rem;
}
.theme-console .tab.active {
  background: var(--bg);
  border-color: var(--border);
}
.theme-warm .tabs {
  padding: 0.6rem 1rem;
  gap: 0.38rem;
  border-bottom-color: transparent;
}
.theme-warm .tab {
  border: 0;
  border-radius: 999rem;
  padding: 0.5rem 0.85rem;
}
.theme-warm .tab.active { background: var(--accent-soft); }
.content {
  max-width: 58rem;
  margin: 0 auto;
  padding: 2.6rem 2rem 7rem;
}
.feature-panel[hidden], .search-empty[hidden], .tab-matchdot[hidden] { display: none; }
.feature-head { margin-bottom: 1.8rem; }
.feature-title {
  margin: 0;
  font-size: 1.9rem;
  line-height: 1.2;
  letter-spacing: 0;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.feature-kw {
  font-family: var(--mono);
  font-size: 0.78rem;
  font-weight: 800;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--accent-soft);
  padding: 0.25rem 0.6rem;
  border-radius: 0.42rem;
}
.path { margin: 0.45rem 0 0; }
.path code {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.82rem;
}
.description {
  color: var(--muted);
  max-width: 68ch;
  margin: 0.9rem 0 0;
}
.stats {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
  margin-top: 1.55rem;
  padding-top: 1.25rem;
  border-top: thin solid var(--border);
}
.stat-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 0.38rem;
}
.stat-pill + .stat-pill {
  border-left: thin solid var(--border);
  padding-left: 0.65rem;
}
.stat-value { font-size: 1.12rem; font-weight: 800; }
.stat-label {
  color: var(--faint);
  font-family: var(--mono);
  font-size: 0.78rem;
}
.stats-spacer { flex: 1; }
.expand-controls {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.expand-controls button {
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  border-radius: 0.45rem;
  padding: 0.38rem 0.62rem;
  font-size: 0.84rem;
  font-weight: 700;
  white-space: nowrap;
}
.expand-controls button:hover { background: var(--surface); color: var(--accent); }
.divider {
  width: 0.0625rem;
  height: 1rem;
  background: var(--border);
}
.search-status {
  margin: 1rem 0 0;
  padding: 0.62rem 0.82rem;
  border-radius: 0.5rem;
  background: var(--accent-soft);
  color: var(--muted);
  font-size: 0.9rem;
}
.rule {
  margin: 1.6rem 0 0.75rem;
  font-size: 1.1rem;
}
.kind { color: var(--muted); }
.background {
  margin-top: 1.5rem;
  padding: 1rem 1.15rem;
  background: var(--surface);
  border: thin dashed var(--border-strong);
  border-radius: 0.75rem;
}
.background-head {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.65rem;
}
.background-kw {
  font-family: var(--mono);
  font-size: 0.76rem;
  font-weight: 800;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.background-name { font-weight: 700; }
.scenario {
  margin-top: 0.9rem;
  background: var(--panel);
  border: thin solid var(--border);
  border-radius: 0.75rem;
  overflow: hidden;
}
.theme-warm .scenario {
  box-shadow: 0 0.08rem 0.18rem oklch(0.5 0.03 60 / 0.06), 0 0.5rem 1.5rem -0.85rem oklch(0.5 0.04 60 / 0.14);
}
.scenario-head {
  display: flex;
  align-items: center;
  gap: 0.72rem;
  cursor: pointer;
  padding: 0.9rem 1.05rem;
  list-style: none;
}
.scenario-head::-webkit-details-marker { display: none; }
.scenario-head:hover { background: var(--surface); }
.chevron::before {
  content: "▸";
  color: var(--faint);
  font-size: 0.82rem;
}
.scenario[open] .chevron::before { content: "▾"; }
.scenario-kw {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex: none;
}
.scenario-name {
  font-weight: 700;
  flex: 1;
  min-width: 10rem;
}
.scenario-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  flex: none;
}
.step-count {
  font-family: var(--mono);
  font-size: 0.7rem;
  color: var(--faint);
  background: var(--surface);
  border: thin solid var(--border);
  border-radius: 999rem;
  padding: 0.18rem 0.5rem;
  white-space: nowrap;
}
.scenario-body { padding: 0.25rem 1.05rem 1rem 2.65rem; }
.step { padding: 0.28rem 0; }
.step.phase-start { margin-top: 1rem; }
.scenario-body .step:first-child.phase-start,
.background-body .step:first-child.phase-start { margin-top: 0; }
.step-main {
  display: flex;
  gap: 0.65rem;
  align-items: baseline;
  line-height: 1.55;
}
.step-kw {
  font-family: var(--mono);
  font-weight: 800;
  font-size: 0.84rem;
  min-width: 3.25rem;
  text-align: right;
  flex: none;
}
.kw-given { color: var(--given); }
.kw-when { color: var(--when); }
.kw-then { color: var(--then); }
.kw-conj { color: var(--conj); }
.step-text { color: var(--text); }
.tok-string { color: var(--string); font-weight: 700; }
.tok-param {
  color: var(--param);
  font-family: var(--mono);
  font-size: 0.88em;
  font-weight: 800;
}
.theme-console .scenario-body { padding-left: 2.35rem; }
.theme-console .step-main {
  padding-left: 0.85rem;
  border-radius: 0.35rem;
}
.theme-console .step:hover .step-main { background: var(--surface); }
.table-wrap {
  margin: 0.62rem 0 0.35rem 3.9rem;
  overflow-x: auto;
}
.gherkin-table {
  border-collapse: separate;
  border-spacing: 0;
  font-family: var(--mono);
  font-size: 0.78rem;
  border: thin solid var(--border);
  border-radius: 0.5rem;
  overflow: hidden;
}
.gherkin-table th,
.gherkin-table td {
  padding: 0.42rem 0.85rem;
  text-align: left;
  border-bottom: thin solid var(--border);
  white-space: nowrap;
}
.gherkin-table th {
  background: var(--surface);
  color: var(--text);
  font-weight: 800;
  border-bottom-color: var(--border-strong);
}
.gherkin-table td { color: var(--muted); }
.gherkin-table tr:last-child td { border-bottom: 0; }
.gherkin-table tbody tr:hover td,
.gherkin-table tr:hover td { background: var(--surface); color: var(--text); }
.docstring,
pre {
  background: var(--surface);
  border: thin solid var(--border);
  border-radius: 0.55rem;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.82rem;
  line-height: 1.5;
  overflow-x: auto;
  padding: 0.75rem 0.9rem;
}
.docstring {
  margin: 0.55rem 0 0.55rem 3.9rem;
  white-space: pre-wrap;
}
.examples { margin-top: 0.9rem; }
.examples-label {
  margin: 0 0 0.25rem 3.9rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.tags {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.32rem;
  margin: 0 0 0.85rem;
}
.scenario-head .tags { margin: 0; }
.tag {
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 800;
  color: var(--tag-text);
  background: var(--tag-bg);
  padding: 0.16rem 0.5rem;
  border-radius: 999rem;
  white-space: nowrap;
}
.theme-console .tag { border-radius: 0.22rem; }
.warning {
  display: inline-block;
  background: var(--warn-bg);
  color: var(--warn-text);
  border-radius: 0.5rem;
  padding: 0.55rem 0.75rem;
}
.empty {
  color: var(--muted);
  font-size: 1.05rem;
  margin: 2.5rem auto;
  max-width: 42rem;
  text-align: center;
}
@media (max-width: 52rem) {
  .topbar { position: static; align-items: flex-start; flex-direction: column; }
  .brand { min-width: 0; width: 100%; flex-wrap: wrap; }
  .topbar-right { width: 100%; justify-content: flex-start; }
  .search { width: 100%; min-width: 0; }
  .tabs { position: static; }
  .content { padding: 1.8rem 1rem 5rem; }
  .feature-title { font-size: 1.55rem; }
  .scenario-meta { display: none; }
  .scenario-body { padding-left: 1rem; }
  .step-main { align-items: flex-start; }
  .step-kw { min-width: 3rem; }
  .table-wrap, .docstring, .examples-label { margin-left: 0; }
}
"""

APP_SCRIPT = """<script>
(function () {
  var app = document.getElementById("app");
  var input = document.getElementById("filter");
  var clear = document.querySelector(".search-clear");
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-feature-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-feature-panel]"));
  var i18n = {
    en: {
      searchPlaceholder: "Search Gherkin files or scenarios...",
      searchLabel: "Search Gherkin files or scenarios",
      clear: "Clear",
      expandAll: "Expand all",
      collapseAll: "Collapse all",
      scenarios: "Scenarios",
      outlines: "Outlines",
      steps: "Steps",
      examples: "Examples",
      stepUnit: "steps",
      fileLabel: "File",
      gherkinKeywords: {
        Feature: "Feature",
        "功能": "Feature",
        Rule: "Rule",
        "规则": "Rule",
        Background: "Background",
        "背景": "Background",
        Scenario: "Scenario",
        "场景": "Scenario",
        "剧本": "Scenario",
        "Scenario Outline": "Scenario Outline",
        "场景大纲": "Scenario Outline",
        "剧本大纲": "Scenario Outline",
        Examples: "Examples",
        "例子": "Examples",
        Given: "Given",
        "假如": "Given",
        "假设": "Given",
        "假定": "Given",
        When: "When",
        "当": "When",
        Then: "Then",
        "那么": "Then",
        And: "And",
        "而且": "And",
        "并且": "And",
        "同时": "And",
        But: "But",
        "但是": "But",
        "*": "*"
      },
      match: function (file, count) { return count + " matching scenario" + (count === 1 ? "" : "s") + " in " + file; },
      emptySearch: "No matching scenarios."
    },
    zh: {
      searchPlaceholder: "搜索 Gherkin 文件或场景...",
      searchLabel: "搜索 Gherkin 文件或场景",
      clear: "清除",
      expandAll: "展开全部",
      collapseAll: "折叠全部",
      scenarios: "场景",
      outlines: "大纲",
      steps: "步骤",
      examples: "示例",
      stepUnit: "步",
      fileLabel: "文件",
      gherkinKeywords: {
        Feature: "功能",
        "功能": "功能",
        Rule: "规则",
        "规则": "规则",
        Background: "背景",
        "背景": "背景",
        Scenario: "场景",
        "场景": "场景",
        "剧本": "场景",
        "Scenario Outline": "场景大纲",
        "场景大纲": "场景大纲",
        "剧本大纲": "场景大纲",
        Examples: "例子",
        "例子": "例子",
        Given: "假如",
        "假如": "假如",
        "假设": "假如",
        "假定": "假如",
        When: "当",
        "当": "当",
        Then: "那么",
        "那么": "那么",
        And: "而且",
        "而且": "而且",
        "并且": "而且",
        "同时": "而且",
        But: "但是",
        "但是": "但是",
        "*": "*"
      },
      match: function (file, count) { return "在 " + file + " 中找到 " + count + " 个匹配的 scenario"; },
      emptySearch: "没有匹配的 scenario。"
    }
  };

  function activeLang() {
    return localStorage.getItem("gherkin-reader-lang") || "en";
  }

  function setLanguage(lang) {
    var dict = i18n[lang] || i18n.en;
    localStorage.setItem("gherkin-reader-lang", lang);
    document.documentElement.lang = lang;
    input.placeholder = dict.searchPlaceholder;
    input.setAttribute("aria-label", dict.searchLabel);
    clear.setAttribute("aria-label", dict.clear);
    document.querySelectorAll("[data-i18n]").forEach(function (node) {
      var key = node.getAttribute("data-i18n");
      if (dict[key]) node.textContent = dict[key];
    });
    document.querySelectorAll("[data-gherkin-keyword]").forEach(function (node) {
      var keyword = node.getAttribute("data-gherkin-keyword");
      node.textContent = dict.gherkinKeywords[keyword] || keyword;
    });
    document.querySelectorAll(".lang-btn").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-lang") === lang);
    });
    applyFilter();
  }

  function setTheme(theme) {
    localStorage.setItem("gherkin-reader-theme", theme);
    app.className = "app theme-" + theme;
    document.querySelectorAll(".style-btn").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-theme") === theme);
    });
  }

  function activate(target) {
    tabs.forEach(function (tab) {
      var active = tab.getAttribute("data-target") === target;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-current", active ? "page" : "false");
    });
    panels.forEach(function (panel) {
      panel.hidden = panel.id !== target;
      panel.classList.toggle("active", panel.id === target);
    });
    applyFilter();
  }

  function scenarioMatches(scenario, query) {
    return !query || scenario.textContent.toLowerCase().indexOf(query) !== -1;
  }

  function featureMatches(panel, tab, query) {
    if (!query) return false;
    var featureName = (panel.getAttribute("data-feature-name") || "") + " " + (tab.getAttribute("data-feature-name") || "");
    return featureName.toLowerCase().indexOf(query) !== -1;
  }

  function applyFilter() {
    var query = input.value.trim().toLowerCase();
    var dict = i18n[activeLang()] || i18n.en;
    clear.hidden = !query;
    var anyVisibleInActive = false;

    tabs.forEach(function (tab) {
      var panel = document.getElementById(tab.getAttribute("data-target"));
      var featureHit = featureMatches(panel, tab, query);
      var scenarios = Array.prototype.slice.call(panel.querySelectorAll("[data-scenario]"));
      var count = scenarios.filter(function (scenario) { return scenarioMatches(scenario, query); }).length;
      tab.classList.toggle("dimmed", !!query && !featureHit && count === 0);
      var dot = tab.querySelector(".tab-matchdot");
      if (dot) dot.hidden = !query || (!featureHit && count === 0);
      if (!panel.hidden) {
        var visibleCount = 0;
        scenarios.forEach(function (scenario) {
          var visible = !query || featureHit || scenarioMatches(scenario, query);
          scenario.hidden = !visible;
          if (visible) {
            visibleCount += 1;
            if (query) scenario.open = true;
          }
        });
        anyVisibleInActive = featureHit || visibleCount > 0;
        var status = panel.querySelector("[data-search-status]");
        if (status) {
          status.hidden = !query;
          status.textContent = query ? dict.match(tab.querySelector(".tab-name").textContent, visibleCount) : "";
        }
      }
    });

    var empty = document.querySelector(".search-empty");
    if (empty) {
      empty.hidden = !query || anyVisibleInActive;
      empty.textContent = dict.emptySearch;
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function (event) {
      event.preventDefault();
      history.replaceState(null, "", "#" + tab.getAttribute("data-target"));
      activate(tab.getAttribute("data-target"));
    });
  });
  input.addEventListener("input", applyFilter);
  clear.addEventListener("click", function () {
    input.value = "";
    input.focus();
    applyFilter();
  });
  document.querySelectorAll(".lang-btn").forEach(function (button) {
    button.addEventListener("click", function () { setLanguage(button.getAttribute("data-lang")); });
  });
  document.querySelectorAll(".style-btn").forEach(function (button) {
    button.addEventListener("click", function () { setTheme(button.getAttribute("data-theme")); });
  });
  document.addEventListener("click", function (event) {
    var expand = event.target.closest("[data-expand]");
    var collapse = event.target.closest("[data-collapse]");
    if (!expand && !collapse) return;
    var panel = event.target.closest("[data-feature-panel]");
    if (!panel) return;
    panel.querySelectorAll("[data-scenario]").forEach(function (scenario) {
      scenario.open = !!expand;
    });
  });

  var initial = location.hash ? location.hash.slice(1) : tabs[0].getAttribute("data-target");
  if (!document.getElementById(initial)) initial = tabs[0].getAttribute("data-target");
  setTheme(localStorage.getItem("gherkin-reader-theme") || "editorial");
  setLanguage(activeLang());
  activate(initial);
})();
</script>"""


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
