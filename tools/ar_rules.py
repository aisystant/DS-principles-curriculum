"""AR rules for v4-lint (WP-374).

AR.3 (полнота), AR.4 (анти-ИИ-стиль), AR.5 (онтологическая чистота FPF).

Pure functions + dataclasses, импортируются из v4-lint.py для регистрации
subcommand'ов и из tests/ для pytest.

Источник: peer-session 2026-05-31-04-wp374-v4lint-ar3-ar4 (CONSENSUS turn 3).
Порт авторских правил из inbox/WP-362/scripts/ в общий v4-lint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


Severity = str  # 'PASS' | 'WARN' | 'FAIL'
Finding = tuple[Severity, str, str]  # (severity, rule_id, message)


# Исключения, общие для всех AR-правил при сканировании директории.
# Эти файлы не являются "подразделом руководства" — это служебные документы.
DEFAULT_EXCLUDE_PATTERNS: tuple[str, ...] = (
    r"^0.*-structure",        # 01-structure-guide-N.md
    r"^index\.md$",
    r"^README",
    r".*-exercises\.md$",
    r".*-review-questions\.md$",
)


def iter_subsection_files(
    paths: Iterable[Path],
    exclude_patterns: Sequence[str] = DEFAULT_EXCLUDE_PATTERNS,
) -> list[Path]:
    """Раскрутить список path'ов в плоский отсортированный список .md-файлов подразделов.

    Дедуп через `.resolve()` — один физический файл, переданный как абсолютный
    и относительный путь (или через симлинк), не дублируется.
    """
    targets: list[Path] = []
    seen: set[Path] = set()  # хранит resolved-пути
    excludes = [re.compile(p) for p in exclude_patterns]
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix == ".md":
            resolved = p.resolve()
            if not any(rx.match(p.name) for rx in excludes) and resolved not in seen:
                targets.append(p)
                seen.add(resolved)
        elif p.is_dir():
            for md_file in sorted(p.rglob("*.md")):
                if any(rx.match(md_file.name) for rx in excludes):
                    continue
                resolved = md_file.resolve()
                if resolved in seen:
                    continue
                targets.append(md_file)
                seen.add(resolved)
    return targets


# ============================================================================
# AR.3 — Полнота подраздела (порт из wp362-check-subsection.sh:159-198)
# ============================================================================


@dataclass(frozen=True)
class AR3Config:
    """Конфигурация AR.3.

    Defaults воспроизводят wp362-check-subsection.sh run_ar3 (8 апреля 2026
    cold review #3 → 11 required_blocks). YAML-override через AR3Config.from_yaml.
    """

    required_blocks: tuple[str, ...] = (
        "В одном предложении",
        "Понятия",
        "Мем, который снимается",
        "Определение из источника",
        "Развитие мысли",
        "Метод",
        "Пример из жизни",
        "Типичная ошибка",
        "Степени мастерства",
        "Проверка себя",
        "Что дальше",
    )
    min_word_count: int = 200
    max_missing_for_pass: int = 0
    fail_threshold_missing: int = 2  # word_count<min && missing>this → FAIL

    @classmethod
    def from_yaml(cls, path: Path) -> "AR3Config":
        """Загрузка из YAML с fallback на defaults для каждого поля.

        Различаем отсутствие ключа (`is None` → defaults) и явный пустой override
        (`required_blocks: []` → пустой кортеж). Это нужно для смоук-режима
        word-count-only, когда автор сознательно отключает проверку блоков.
        """
        import yaml  # lazy import — PyYAML опциональный для standalone ar_rules

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        defaults = cls()
        blocks = data.get("required_blocks")
        return cls(
            required_blocks=tuple(blocks) if blocks is not None else defaults.required_blocks,
            min_word_count=int(data.get("min_word_count", defaults.min_word_count)),
            max_missing_for_pass=int(
                data.get("max_missing_for_pass", defaults.max_missing_for_pass)
            ),
            fail_threshold_missing=int(
                data.get("fail_threshold_missing", defaults.fail_threshold_missing)
            ),
        )


def check_ar3(file_path: Path, config: AR3Config | None = None) -> list[Finding]:
    """Проверить AR.3 для одного .md-файла. Возвращает список findings.

    Воспроизводит логику wp362-check-subsection.sh run_ar3:
      - Для каждого блока проверяем наличие через regex `\\*\\*<block>`
      - Severity:
          word_count < min_word_count && missing > fail_threshold_missing → FAIL
          word_count >= min_word_count && missing == max_missing_for_pass → PASS
          иначе — только WARN-и без summary-line

    Known limitation (parity с bash baseline): regex `\\*\\*<block>` ловит любое
    bold-упоминание имени блока, не только заголовок-блок. Текст `... **Метод**
    решает проблему ...` в середине абзаца засчитается как присутствие блока
    «Метод». Для ужесточения нужно требовать start-of-line якорь `^\\s*\\*\\*<block>`,
    но это сломает parity (тогда тесты на s1-batch упадут). Ужесточение —
    отдельный РП после WP-374, с пересмотром baseline.
    """
    if config is None:
        config = AR3Config()

    content = file_path.read_text(encoding="utf-8")
    word_count = len(content.split())
    findings: list[Finding] = []
    missing = 0

    for block in config.required_blocks:
        pattern = r"\*\*" + re.escape(block)
        if not re.search(pattern, content):
            missing += 1
            findings.append(
                ("WARN", "AR.3", f"{file_path.name}: отсутствует блок «{block}»")
            )

    if word_count < config.min_word_count and missing > config.fail_threshold_missing:
        findings.append(
            (
                "FAIL",
                "AR.3",
                f"{file_path.name}: word_count={word_count} + {missing} блоков отсутствует",
            )
        )
    elif word_count >= config.min_word_count and missing == config.max_missing_for_pass:
        findings.append(("PASS", "AR.3", f"{file_path.name}: полный"))

    return findings
