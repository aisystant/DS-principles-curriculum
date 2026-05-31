"""Тесты AR.3 (WP-374)."""

import os
import sys
from pathlib import Path

import pytest

# tools/tests/ — sibling tests; import from parent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ar_rules import AR3Config, check_ar3, iter_subsection_files

CASES_DIR = Path(__file__).parent / "ar3_cases"


def test_pass_full_subsection():
    """Подраздел со всеми 11 блоками и word_count > 200 даёт PASS."""
    findings = check_ar3(CASES_DIR / "pass" / "full_subsection.md")
    severities = [f[0] for f in findings]
    assert "FAIL" not in severities
    assert "PASS" in severities
    # WARN могут быть (если случайно регулярка не совпала); проверим строго что PASS есть.


def test_fail_empty_subsection():
    """Короткий подраздел без блоков → FAIL (word_count<200 + missing>2)."""
    findings = check_ar3(CASES_DIR / "fail" / "empty_subsection.md")
    severities = [f[0] for f in findings]
    assert "FAIL" in severities


def test_warn_some_missing():
    """Подраздел с частью блоков → ни PASS, ни FAIL, только WARN-и."""
    findings = check_ar3(CASES_DIR / "warn" / "some_missing.md")
    severities = [f[0] for f in findings]
    assert "WARN" in severities
    assert "PASS" not in severities
    assert "FAIL" not in severities


def test_config_defaults_unchanged():
    """Defaults dataclass воспроизводят wp362-check-subsection.sh:159-198."""
    config = AR3Config()
    assert len(config.required_blocks) == 11
    assert config.required_blocks[0] == "В одном предложении"
    assert config.required_blocks[-1] == "Что дальше"
    assert config.min_word_count == 200
    assert config.max_missing_for_pass == 0
    assert config.fail_threshold_missing == 2


def test_config_from_yaml_override(tmp_path):
    """YAML-override меняет required_blocks и thresholds."""
    yaml_file = tmp_path / "ar3-rr.yaml"
    yaml_file.write_text(
        "required_blocks:\n"
        "  - Заголовок\n"
        "  - Тело\n"
        "min_word_count: 100\n"
        "fail_threshold_missing: 1\n",
        encoding="utf-8",
    )
    config = AR3Config.from_yaml(yaml_file)
    assert config.required_blocks == ("Заголовок", "Тело")
    assert config.min_word_count == 100
    assert config.fail_threshold_missing == 1
    # max_missing_for_pass отсутствует в YAML → defaults.
    assert config.max_missing_for_pass == 0


def test_config_from_yaml_partial(tmp_path):
    """Пустой YAML → все defaults сохраняются."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("", encoding="utf-8")
    config = AR3Config.from_yaml(yaml_file)
    defaults = AR3Config()
    assert config == defaults


def test_iter_subsection_files_dedup_abs_rel(tmp_path, monkeypatch):
    """Один файл, переданный как абсолютный и относительный путь, не дублируется."""
    (tmp_path / "1.01-content.md").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    targets = iter_subsection_files(
        [Path("1.01-content.md"), tmp_path / "1.01-content.md", tmp_path]
    )
    assert len(targets) == 1


def test_from_yaml_empty_list_override(tmp_path):
    """`required_blocks: []` в YAML даёт пустой кортеж, не fallback на defaults."""
    yaml_file = tmp_path / "empty-blocks.yaml"
    yaml_file.write_text("required_blocks: []\n", encoding="utf-8")
    config = AR3Config.from_yaml(yaml_file)
    assert config.required_blocks == ()


def test_iter_subsection_files_excludes(tmp_path):
    """iter_subsection_files исключает структурные/служебные файлы."""
    (tmp_path / "1.01-content.md").write_text("x", encoding="utf-8")
    (tmp_path / "01-structure-guide-1.md").write_text("x", encoding="utf-8")
    (tmp_path / "index.md").write_text("x", encoding="utf-8")
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    (tmp_path / "1.09-exercises.md").write_text("x", encoding="utf-8")
    (tmp_path / "1.10-review-questions.md").write_text("x", encoding="utf-8")

    targets = iter_subsection_files([tmp_path])
    names = [t.name for t in targets]
    assert names == ["1.01-content.md"]


def test_parity_with_wp362_baseline():
    """E2E: новая Python AR.3 даёт результат, идентичный baseline wp362-check-subsection.sh.

    Зафиксирован для s1-batch (1-1-systemic-self-development/s1-culture-as-admission):
      [SUMMARY] PASS=7 WARN=22 FAIL=0
    """
    s1_batch = Path(
        "/Users/tserentserenov/IWE/docs/docs/ru/personal-design/"
        "1-1-systemic-self-development/s1-culture-as-admission"
    )
    if not s1_batch.exists():
        pytest.skip(f"s1-batch path not available: {s1_batch}")

    targets = iter_subsection_files([s1_batch])
    pass_count = warn_count = fail_count = 0
    for target in targets:
        for severity, _, _ in check_ar3(target):
            if severity == "PASS":
                pass_count += 1
            elif severity == "WARN":
                warn_count += 1
            elif severity == "FAIL":
                fail_count += 1

    assert pass_count == 7, f"PASS count drift: expected 7, got {pass_count}"
    assert warn_count == 22, f"WARN count drift: expected 22, got {warn_count}"
    assert fail_count == 0, f"FAIL count drift: expected 0, got {fail_count}"
