from __future__ import annotations

import html
from html.parser import HTMLParser
import re

import mistune

from learning_os.core.glossary import CourseGlossary, GlossaryTerm, terms_in_content


_MARKDOWN = mistune.create_markdown(
    escape=True,
    plugins=["strikethrough", "table", "task_lists", "url"],
)
_SKIP_TAGS = {"a", "button", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_FALLBACK_STRONG = re.compile(r"\*\*(?=\S)(.+?\S)\*\*")


def _alias_pattern(alias: str) -> str:
    escaped = re.escape(alias)
    if re.fullmatch(r"[a-z0-9][a-z0-9 _-]*", alias.casefold()):
        return rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])"
    return escaped


def _term_button(term: GlossaryTerm, displayed_text: str, course_id: str) -> str:
    tooltip_id = f"glossary-inline-{course_id}-{term.id}"
    example = ""
    if term.example:
        example = (
            '<span class="glossary-inline-example">'
            f"예시 · {html.escape(term.example)}"
            "</span>"
        )
    return (
        '<button type="button" class="glossary-inline" '
        f'aria-label="{html.escape(term.name)} 용어 설명" '
        f'aria-describedby="{tooltip_id}">'
        f'<span class="glossary-inline-label">{html.escape(displayed_text)}</span>'
        f'<span class="glossary-inline-card" id="{tooltip_id}" role="tooltip">'
        f'<strong>{html.escape(term.name)}</strong>'
        f'<span>{html.escape(term.short_definition)}</span>'
        f"{example}"
        "</span>"
        "</button>"
    )


class _GlossaryHTMLAnnotator(HTMLParser):
    def __init__(
        self,
        matcher: re.Pattern[str],
        candidates: list[tuple[str, GlossaryTerm]],
        course_id: str,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.matcher = matcher
        self.candidates = candidates
        self.course_id = course_id
        self.output: list[str] = []
        self.tag_stack: list[str] = []
        self.skip_depth = 0
        self.used_term_ids: set[str] = set()

    @staticmethod
    def _attributes(attrs: list[tuple[str, str | None]]) -> str:
        rendered = []
        for name, value in attrs:
            if value is None:
                rendered.append(f" {html.escape(name)}")
            else:
                rendered.append(
                    f' {html.escape(name)}="{html.escape(value, quote=True)}"'
                )
        return "".join(rendered)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output.append(f"<{tag}{self._attributes(attrs)}>")
        if tag in _VOID_TAGS:
            return
        self.tag_stack.append(tag)
        if tag in _SKIP_TAGS:
            self.skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output.append(f"<{tag}{self._attributes(attrs)} />")

    def handle_endtag(self, tag: str) -> None:
        self.output.append(f"</{tag}>")
        if self.tag_stack:
            opened = self.tag_stack.pop()
            if opened in _SKIP_TAGS:
                self.skip_depth = max(0, self.skip_depth - 1)

    def _append_terms(self, data: str) -> None:
        cursor = 0
        for match in self.matcher.finditer(data):
            self.output.append(html.escape(data[cursor : match.start()], quote=False))
            group_name = match.lastgroup
            if group_name is None:
                self.output.append(html.escape(match.group(0), quote=False))
            else:
                _, term = self.candidates[int(group_name[1:])]
                if term.id in self.used_term_ids:
                    self.output.append(html.escape(match.group(0), quote=False))
                else:
                    self.used_term_ids.add(term.id)
                    self.output.append(
                        _term_button(term, match.group(0), self.course_id)
                    )
            cursor = match.end()
        self.output.append(html.escape(data[cursor:], quote=False))

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data.strip():
            self.output.append(html.escape(data, quote=False))
            return

        # CommonMark does not close emphasis immediately before some Korean
        # particles (for example ``**90%**로``). Streamlit's Markdown accepted
        # this authoring style, so preserve it while moving lesson rendering to
        # safe HTML for inline glossary annotations.
        cursor = 0
        for match in _FALLBACK_STRONG.finditer(data):
            self._append_terms(data[cursor : match.start()])
            self.output.append("<strong>")
            self._append_terms(match.group(1))
            self.output.append("</strong>")
            cursor = match.end()
        self._append_terms(data[cursor:])


def annotate_markdown_with_glossary(
    content: str,
    glossary: CourseGlossary,
    *,
    limit: int = 20,
) -> str:
    """Render Markdown safely and annotate first term occurrences outside code/links."""
    terms = terms_in_content(glossary, content, limit=limit)
    rendered_markdown = _MARKDOWN(content)
    if not terms:
        return f'<article class="lesson-markdown">{rendered_markdown}</article>'

    candidates: list[tuple[str, GlossaryTerm]] = []
    for term in terms:
        for alias in (term.name, *term.aliases):
            normalized = alias.strip()
            if len(normalized) >= 2:
                candidates.append((normalized, term))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    groups = [f"(?P<t{index}>{_alias_pattern(alias)})" for index, (alias, _) in enumerate(candidates)]
    matcher = re.compile("|".join(groups), re.IGNORECASE)
    parser = _GlossaryHTMLAnnotator(matcher, candidates, glossary.course_id)
    parser.feed(rendered_markdown)
    parser.close()
    return f'<article class="lesson-markdown">{"".join(parser.output)}</article>'
