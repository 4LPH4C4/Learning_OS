from __future__ import annotations

from pathlib import Path

from learning_os.config import load_settings
from learning_os.core.catalog import discover_courses
from learning_os.core.glossary import load_glossary, terms_in_content
from learning_os.ui.glossary import annotate_markdown_with_glossary


ROOT = Path(__file__).parents[1]


def test_all_registered_courses_have_valid_substantial_glossaries() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    expected_counts = {
        "ai-for-beginners": 20,
        "aice-associate": 35,
        "chinese-hsk": 31,
        "english-cefr": 15,
        "ncs-core": 37,
        "pspo-i": 26,
        "sqld": 21,
    }

    assert catalog.issues == ()
    for course in catalog.courses:
        glossary = load_glossary(course)
        assert len(glossary.terms) == expected_counts[course.id]
        assert all(term.short_definition and term.explanation for term in glossary.terms)
        assert all(term.source_url for term in glossary.terms)


def test_lesson_term_detection_supports_aliases_without_ascii_substring_noise() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    course = catalog.get("pspo-i")
    assert course is not None
    glossary = load_glossary(course)

    found = terms_in_content(
        glossary,
        "Product Owner는 경험주의를 사용한다. support라는 단어는 PO로 오인하면 안 된다.",
    )

    assert [term.id for term in found][:2] == ["product-owner", "empiricism"]
    assert len([term for term in found if term.id == "product-owner"]) == 1


def test_inline_glossary_annotation_is_safe_and_skips_code_and_links() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    course = catalog.get("pspo-i")
    assert course is not None
    glossary = load_glossary(course)
    content = """\
<script>alert('unsafe')</script>

Product Owner는 가치를 책임진다. Product Owner는 한 사람이다.

**중요한 판단이다.** 시험 목표는 **90%**로 둔다.

`Product Owner`와 [Product Owner](https://example.test)는 그대로 둔다.

```text
Product Owner
```
"""

    annotated = annotate_markdown_with_glossary(content, glossary)

    assert annotated.count('class="glossary-inline"') == 1
    assert "<strong>Product Owner</strong>" in annotated
    assert "Product Owner는 한 사람이다." in annotated
    assert "<strong>중요한 판단이다.</strong>" in annotated
    assert "<strong>90%</strong>로" in annotated
    assert "<code>Product Owner</code>" in annotated
    assert '<a href="https://example.test">Product Owner</a>' in annotated
    assert '<pre><code class="language-text">Product Owner\n</code></pre>' in annotated
    assert "<script>" not in annotated
    assert "&lt;script&gt;" in annotated
