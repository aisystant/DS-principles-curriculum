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


# ============================================================================
# AR.4 — Анти-ИИ-стиль (порт из wp362-style-grep.sh)
# ============================================================================

# Дефолтные пути к ar4 data-файлам (относительно ar_rules.py).
_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_AR4_BLACKLIST = _DATA_DIR / "ar4-blacklist.txt"
DEFAULT_AR4_WHITELIST = _DATA_DIR / "ar4-whitelist.txt"

# Pre-compiled regex'ы для extract_body.
_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_PACK_BLOCKQUOTE_RE = re.compile(
    r"^>.*?(?:PD\.[A-Z]+\.\d+|FPF\.[A-Z]+).*?$", re.MULTILINE
)
_INLINE_PACK_RE = re.compile(r"`[A-Z]+\.[A-Z]+\.\d+[^`]*`")
_GUILLEMET_QUOTE_RE = re.compile(r"«[^»]*»")
# Тройные параллели «не X, не Y, не Z» (lowercase «не», cyrillic body).
# Parity с bash baseline `[а-я]+` (БЕЗ ё, U+0451 вне диапазона U+0430-U+044F).
# Если потребуется включить ё — отдельный РП с обновлением baseline.
_TRIPLE_PARALLEL_RE = re.compile(r"не [а-я]+, не [а-я]+, не [а-я]+")


def _load_phrases(path: Path) -> list[str]:
    """Загрузить фразы из файла (пропустить пустые и `#`-комментарии)."""
    phrases: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            phrases.append(stripped)
    return phrases


def extract_body(content: str) -> str:
    """Удалить из текста frontmatter, code blocks, Pack-цитаты, реплики «...».

    Воспроизводит логику wp362-style-grep.sh:43-74 (awk + sed). Порядок важен:
    сначала frontmatter, потом code blocks, потом блок-цитаты с Pack-ID,
    потом inline `PD.X.NNN`, потом реплики в «...».
    """
    body = _FRONTMATTER_RE.sub("", content, count=1)
    body = _CODE_BLOCK_RE.sub("", body)
    body = _PACK_BLOCKQUOTE_RE.sub("", body)
    body = _INLINE_PACK_RE.sub("", body)
    body = _GUILLEMET_QUOTE_RE.sub("", body)
    return body


@dataclass(frozen=True)
class AR4Config:
    """Конфигурация AR.4 (анти-ИИ-стилистика).

    Defaults воспроизводят wp362-style-grep.sh: WARN при net≥1, FAIL при net≥3.
    blacklist/whitelist — пути к текстовым файлам (одна фраза на строку,
    `#` — комментарий).
    """

    blacklist_path: Path = field(default_factory=lambda: DEFAULT_AR4_BLACKLIST)
    whitelist_path: Path = field(default_factory=lambda: DEFAULT_AR4_WHITELIST)
    warn_threshold: int = 1
    fail_threshold: int = 3


def _count_phrase_lines(body_lower: str, phrase: str) -> int:
    """Число строк в body_lower, содержащих phrase (parity с `grep -c`)."""
    p = phrase.lower()
    return sum(1 for line in body_lower.splitlines() if p in line)


def _count_triple_lines(body: str) -> int:
    """Число строк, на которых сматчился `_TRIPLE_PARALLEL_RE` (parity с `grep -cE`)."""
    return sum(1 for line in body.splitlines() if _TRIPLE_PARALLEL_RE.search(line))


def check_ar4(file_path: Path, config: AR4Config | None = None) -> list[Finding]:
    """Проверить AR.4 (анти-ИИ-стилистика) для одного .md-файла.

    Алгоритм (порт wp362-style-grep.sh, parity по counting-семантике):
      1. extract_body — убрать frontmatter / code / Pack-цитаты / «...» реплики
      2. blacklist_hits = число СТРОК (не occurrences) с фразами из blacklist
      3. whitelist_hits = аналогично
      4. triple_parallels = число строк с `не X, не Y, не Z`
      5. net = blacklist_hits − whitelist_hits + triple_parallels
      6. Severity:
           net >= fail_threshold (3) → FAIL
           net >= warn_threshold (1) → WARN
           иначе → PASS

    Важно: bash `grep -c` считает СТРОКИ-совпадения, не occurrences. Если одна
    строка содержит фразу 3 раза — bash вернёт 1. Эквивалентно реализовано через
    `_count_phrase_lines`/`_count_triple_lines`.
    """
    if config is None:
        config = AR4Config()

    try:
        blacklist = _load_phrases(config.blacklist_path)
        whitelist = _load_phrases(config.whitelist_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"AR.4 config missing: {e.filename}. "
            f"Создай файл или передай --blacklist/--whitelist override."
        ) from e

    content = file_path.read_text(encoding="utf-8")
    body = extract_body(content)
    body_lower = body.lower()

    blacklist_hits = sum(_count_phrase_lines(body_lower, p) for p in blacklist)
    whitelist_hits = sum(_count_phrase_lines(body_lower, p) for p in whitelist)
    triple_parallels = _count_triple_lines(body)

    net = blacklist_hits - whitelist_hits + triple_parallels

    if net >= config.fail_threshold:
        severity = "FAIL"
    elif net >= config.warn_threshold:
        severity = "WARN"
    else:
        severity = "PASS"

    msg = (
        f"{file_path.name}: net={net} "
        f"(blacklist={blacklist_hits}, whitelist={whitelist_hits}, triples={triple_parallels})"
    )
    return [(severity, "AR.4", msg)]
