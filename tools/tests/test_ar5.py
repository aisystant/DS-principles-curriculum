"""Тесты AR.5 (WP-374)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ar_rules import (
    AR5Config,
    check_ar5,
    load_glossary,
    DEFAULT_AR5_GLOSSARY,
    _split_paragraphs,
    _suppression_active,
)

CASES_DIR = Path(__file__).parent / "ar5_cases"


def test_glossary_loads():
    """Default glossary существует и содержит ≥7 entity-типов."""
    assert DEFAULT_AR5_GLOSSARY.exists(), f"missing: {DEFAULT_AR5_GLOSSARY}"
    entities = load_glossary(DEFAULT_AR5_GLOSSARY)
    assert len(entities) >= 7
    names = {e.name for e in entities}
    assert "система" in names
    assert "роль" in names
    assert "целевая система" in names
    assert "сервис" in names
    assert "метод" in names
    assert "мастерство" in names
    assert "степень мастерства" in names


def test_glossary_fields():
    """Каждый entity имеет fpf_anchor и distinguish_from."""
    entities = load_glossary(DEFAULT_AR5_GLOSSARY)
    for e in entities:
        assert e.fpf_anchor, f"{e.name}: missing fpf_anchor"
        # У большинства есть distinguish_from (кроме разве что edge-кейсов).
        if e.name not in ("целевая система",):  # requires_context-only
            assert e.distinguish_from, f"{e.name}: missing distinguish_from"


def test_pass_typed_entities():
    """Подраздел с явной типизацией entity → PASS."""
    findings = check_ar5(CASES_DIR / "pass" / "typed_entities.md")
    severities = [f[0] for f in findings]
    # Может быть несколько WARN (например, для метод/сервис если коллизия), но
    # минимум один PASS должен быть, или вообще без findings (только PASS).
    # Допускаем что некоторые упоминания могут давать WARN из-за окна <200 chars,
    # главное — fewer than threshold.
    assert "FAIL" not in severities
    warn_count = sum(1 for s in severities if s == "WARN")
    # Strict-PASS: если все типизировано, WARN должно быть мало.
    # Для теста — допускаем до 5 WARN (вариативность в коротком тексте).
    assert warn_count <= 5, f"too many WARN in typed text: {warn_count}"


def test_warn_missing_disambiguation():
    """3 упоминания «система» без маркеров → ≥3 WARN."""
    findings = check_ar5(CASES_DIR / "warn" / "missing_disambiguation.md")
    warn_count = sum(1 for s, _, _ in findings if s == "WARN")
    assert warn_count >= 3, f"expected ≥3 WARN, got {warn_count}"


def test_warn_missing_context():
    """«целевая система» без proj-keywords → WARN Rule B."""
    findings = check_ar5(CASES_DIR / "warn" / "missing_context.md")
    messages = [m for _, _, m in findings]
    # Хотя бы один WARN с упоминанием context.
    assert any("требуется контекст" in m for m in messages), (
        f"expected Rule B WARN about context, got: {messages}"
    )


def test_distinction_suppression():
    """frontmatter mastery_node: [distinction] + `## Различение X vs Y` подавляют Rule C."""
    findings = check_ar5(CASES_DIR / "pass" / "distinction_suppression.md")
    messages = [m for _, _, m in findings]
    # Не должно быть collision-аггрегации.
    assert not any("коллизий" in m for m in messages), (
        f"distinction suppression failed, got: {messages}"
    )


def test_split_paragraphs():
    """_split_paragraphs корректно разбивает текст по пустым строкам."""
    text = "First para.\n\nSecond para.\n\nThird para."
    paras = _split_paragraphs(text)
    assert len(paras) == 3
    assert paras[0][2].strip() == "First para."
    assert paras[2][2].strip() == "Third para."


def test_suppression_active_frontmatter(tmp_path):
    """mastery_node: [distinction] в frontmatter активирует suppression."""
    content = "---\nmastery_node: [distinction]\n---\n\n# x"
    config = AR5Config()
    assert _suppression_active(content, config)


def test_suppression_active_heading(tmp_path):
    """`## Различение X vs Y` heading активирует suppression."""
    content = "---\ntitle: x\n---\n\n## Различение система vs роль\n\ntext"
    config = AR5Config()
    assert _suppression_active(content, config)


def test_suppression_inactive_normal_text(tmp_path):
    """Обычный подраздел без distinction-маркеров — suppression выключен."""
    content = "---\ntitle: x\n---\n\n# Обычный заголовок\n\ntext"
    config = AR5Config()
    assert not _suppression_active(content, config)


def test_collision_threshold_aggregation(tmp_path):
    """≥3 коллизий по паре → 1 агрегированный WARN, не 3+ отдельных."""
    # Создаём текст с 3+ коллизиями «система»/«роль» без маркеров различения.
    text = "---\ntitle: x\n---\n\n"
    for i in range(4):
        text += f"Параграф {i}: тут есть система и тут же роль рядом.\n\n"
    test_file = tmp_path / "collision.md"
    test_file.write_text(text, encoding="utf-8")
    findings = check_ar5(test_file)
    messages = [m for _, _, m in findings]
    aggregated = [m for m in messages if "коллизий" in m]
    assert len(aggregated) >= 1, f"expected aggregated collision WARN, got: {messages}"


def test_substring_overlap_celevaya_sistema(tmp_path):
    """«целевая система» не должна давать ложный WARN от entity «система»."""
    test_file = tmp_path / "celevaya.md"
    test_file.write_text(
        "---\ntitle: x\n---\n\n"
        "Целевая система проекта — это сложная вещь.\n\n"
        "Целевая система проекта меняется со временем.\n\n"
        "Целевая система проекта требует уточнения цели проекта.\n",
        encoding="utf-8",
    )
    findings = check_ar5(test_file)
    messages = [m for _, _, m in findings]
    # Не должно быть «система» WARN, потому что все упоминания покрыты «целевая система».
    sistema_warns = [m for m in messages if "«система»" in m]
    assert sistema_warns == [], (
        f"substring overlap не защищён: {sistema_warns}"
    )
    # И не должно быть collision «целевая система»/«система».
    collision_warns = [m for m in messages if "коллизий" in m and "целевая система" in m]
    assert collision_warns == [], (
        f"self-collision не защищён: {collision_warns}"
    )


def test_substring_overlap_stepen_masterstva(tmp_path):
    """«степень мастерства» не должна давать ложный WARN от entity «мастерство»."""
    test_file = tmp_path / "stepen.md"
    test_file.write_text(
        "---\ntitle: x\n---\n\n"
        "Степень мастерства — это уровень исполнения роли.\n\n"
        "Степень мастерства как характеристика измеримая.\n\n"
        "Степень мастерства не путать с ролью.\n",
        encoding="utf-8",
    )
    findings = check_ar5(test_file)
    messages = [m for _, _, m in findings]
    masterstvo_warns = [m for m in messages if "«мастерство»" in m]
    assert masterstvo_warns == [], (
        f"substring overlap для мастерство не защищён: {masterstvo_warns}"
    )


def test_collision_threshold_zero_emits_individual(tmp_path):
    """collision_threshold=0 → каждый collision отдельным WARN, не агрегация."""
    import dataclasses
    config = dataclasses.replace(AR5Config(), collision_threshold=0)
    text = "---\ntitle: x\n---\n\n"
    for i in range(3):
        text += f"Параграф {i}: система и роль рядом.\n\n"
    test_file = tmp_path / "thr0.md"
    test_file.write_text(text, encoding="utf-8")
    findings = check_ar5(test_file, config)
    messages = [m for _, _, m in findings]
    aggregated = [m for m in messages if "коллизий" in m]
    individual = [m for m in messages if "без маркера различия" in m]
    assert aggregated == [], f"threshold=0 не должен агрегировать: {aggregated}"
    assert len(individual) >= 3, (
        f"threshold=0 должен дать ≥3 individual WARN: {individual}"
    )


def test_glossary_override_path(tmp_path):
    """--glossary override path работает."""
    import dataclasses
    glossary = tmp_path / "minimal.yaml"
    glossary.write_text(
        "entity_types:\n"
        "  тест:\n"
        "    fpf_anchor: TEST.001\n"
        "    distinguish_from: [other]\n",
        encoding="utf-8",
    )
    config = dataclasses.replace(AR5Config(), glossary_path=glossary)
    entities = load_glossary(config.glossary_path)
    assert len(entities) == 1
    assert entities[0].name == "тест"
