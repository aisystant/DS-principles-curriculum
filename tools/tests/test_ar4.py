"""Тесты AR.4 (WP-374)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ar_rules import (
    AR4Config,
    check_ar4,
    extract_body,
    iter_subsection_files,
    DEFAULT_AR4_BLACKLIST,
    DEFAULT_AR4_WHITELIST,
)

CASES_DIR = Path(__file__).parent / "ar4_cases"


def test_pass_clean_subsection():
    """Чистый текст без маркеров → PASS (net=0)."""
    findings = check_ar4(CASES_DIR / "pass" / "clean_subsection.md")
    assert len(findings) == 1
    severity, rule, msg = findings[0]
    assert severity == "PASS"
    assert rule == "AR.4"
    assert "net=0" in msg


def test_fail_ai_stylistic():
    """Текст с 3+ маркерами ИИ-стилистики + тройной параллелью → FAIL (net≥3)."""
    findings = check_ar4(CASES_DIR / "fail" / "ai_stylistic.md")
    assert len(findings) == 1
    severity, _, msg = findings[0]
    assert severity == "FAIL"


def test_fail_triple_parallel_alone():
    """3 тройные параллели без blacklist → FAIL только через triples."""
    findings = check_ar4(CASES_DIR / "fail" / "triple_parallel.md")
    assert len(findings) == 1
    severity, _, msg = findings[0]
    assert severity == "FAIL"
    assert "triples=3" in msg, f"expected triples=3 in: {msg}"
    assert "blacklist=0" in msg


def test_parity_line_count_not_occurrences(tmp_path):
    """bash `grep -c` считает строки; Python тоже должен считать строки, не occurrences.

    Файл с одной строкой, содержащей фразу-маркер 3 раза → bash blacklist_hits=1,
    Python должен дать blacklist_hits=1 (не 3). Это критический parity-инвариант.
    """
    test_file = tmp_path / "duplicate_on_line.md"
    test_file.write_text(
        "---\ntitle: x\n---\n\n"
        "представьте себе ситуацию представьте себе ещё одну представьте себе третью\n",
        encoding="utf-8",
    )
    findings = check_ar4(test_file)
    severity, _, msg = findings[0]
    assert "blacklist=1" in msg, (
        f"line-count parity нарушен (occurrences vs lines): {msg}"
    )


def test_file_not_found_helpful_error(tmp_path):
    """Отсутствие data-файла должно давать понятную ошибку, не traceback."""
    import dataclasses
    config = dataclasses.replace(AR4Config(), blacklist_path=tmp_path / "missing.txt")
    test_file = tmp_path / "any.md"
    test_file.write_text("text", encoding="utf-8")
    with pytest.raises(FileNotFoundError) as exc:
        check_ar4(test_file, config)
    assert "AR.4 config missing" in str(exc.value)


def test_warn_single_marker():
    """Текст с одним маркером → WARN (net=1)."""
    findings = check_ar4(CASES_DIR / "warn" / "single_marker.md")
    assert len(findings) == 1
    severity, _, msg = findings[0]
    assert severity == "WARN"
    assert "net=1" in msg


def test_quotes_auto_excluded():
    """Цитата с маркером в «...» не должна попадать в счёт."""
    findings = check_ar4(CASES_DIR / "pass" / "quote_excluded.md")
    severity, _, _ = findings[0]
    assert severity == "PASS"


def test_extract_body_strips_frontmatter():
    """extract_body удаляет YAML frontmatter."""
    content = "---\ntitle: test\n---\n\nBody text"
    assert extract_body(content).strip() == "Body text"


def test_extract_body_strips_code_blocks():
    """extract_body удаляет code blocks."""
    content = "Before\n\n```python\nprint('давайте разберёмся')\n```\n\nAfter"
    body = extract_body(content)
    assert "давайте разберёмся" not in body
    assert "Before" in body
    assert "After" in body


def test_extract_body_strips_pack_blockquote():
    """extract_body удаляет блок-цитаты с Pack-ID."""
    content = "Normal text\n\n> Цитата PD.FORM.089 §6 — определение роли\n\nMore text"
    body = extract_body(content)
    assert "PD.FORM.089" not in body
    assert "Normal text" in body


def test_extract_body_strips_inline_pack():
    """extract_body удаляет inline `PD.X.NNN`."""
    content = "См. `PD.ROLE.042 v2` для контекста."
    body = extract_body(content)
    assert "PD.ROLE.042" not in body


def test_extract_body_strips_guillemet_quotes():
    """extract_body удаляет реплики в «...»."""
    content = "Человек говорит «представьте себе ситуацию» и уходит."
    body = extract_body(content)
    assert "представьте себе" not in body


def test_default_files_exist():
    """Default paths указывают на реальные файлы."""
    assert DEFAULT_AR4_BLACKLIST.exists(), f"missing: {DEFAULT_AR4_BLACKLIST}"
    assert DEFAULT_AR4_WHITELIST.exists(), f"missing: {DEFAULT_AR4_WHITELIST}"


def test_parity_with_wp362_baseline():
    """E2E: новая Python AR.4 даёт результат, идентичный wp362-style-grep.sh.

    Baseline для s1-batch (1-1-systemic-self-development/s1-culture-as-admission):
      [SUMMARY] PASS=11 WARN=0 FAIL=0  (11 .md файлов, без exclude'ов)
    """
    s1_batch = Path(
        "/Users/tserentserenov/IWE/docs/docs/ru/personal-design/"
        "1-1-systemic-self-development/s1-culture-as-admission"
    )
    if not s1_batch.exists():
        pytest.skip(f"s1-batch path not available: {s1_batch}")

    targets = iter_subsection_files([s1_batch], exclude_patterns=())
    pass_count = warn_count = fail_count = 0
    for target in targets:
        for severity, _, _ in check_ar4(target):
            if severity == "PASS":
                pass_count += 1
            elif severity == "WARN":
                warn_count += 1
            elif severity == "FAIL":
                fail_count += 1

    assert pass_count == 11, f"PASS count drift: expected 11, got {pass_count}"
    assert warn_count == 0
    assert fail_count == 0
