#!/usr/bin/env python3
"""Нормализация structure-guide-N.md (WP-322 Ф0.13).

Цель: привести guide-2, guide-3, guide-4 к формату guide-1, чтобы parser
(parse_structure_file) видел их подразделы как Subsection-объекты.

Текущие форматы:
  - guide-1 (эталон): `### N.M Title` + ```yaml ... ``` block + **Понятия:** + ...
  - guide-2, guide-3:  `--- subsection_id: ... --- **Понятия:** ...` (frontmatter без header'ов)
  - guide-4: 110 yaml-блоков (как guide-1), но БЕЗ `### N.M` header'ов перед ними

Стратегия:
  1. Найти все блоки описания подраздела (по `subsection_id: PD.GUIDE.G.SX.SSY`)
  2. Для каждого извлечь N, M из subsection_id и title из поля title
  3. Перед блоком вставить `### N.M Title` (если ещё нет)
  4. Для guide-2/3: завернуть `---` frontmatter в ` ```yaml ... ``` ` (для совместимости
     с parser'ом, который ищет ```yaml в structure-файлах)

Usage:
  python3 normalize-structure-guide.py --mode lint <file.md> [<file.md> ...]
  python3 normalize-structure-guide.py --mode fix <file.md> [<file.md> ...]

Lint показывает diff (что бы изменилось). Fix применяет правки + создаёт .bak.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Поддержка обоих форматов id: PD.GUIDE.G.SX.SSY (эталон) и PD.GUIDE.G.SX.0Y (legacy guide-2/3)
SUBSECTION_ID_RE = re.compile(r"subsection_id:\s*PD\.GUIDE\.(\d+)\.S(\d+)\.(?:SS)?(\d+)")
SUBSECTION_ID_LINE_RE = re.compile(
    r"(subsection_id:\s*PD\.GUIDE\.\d+\.S\d+\.)(\d+)", re.MULTILINE
)
TITLE_RE = re.compile(r'title:\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)
HEADER_RE = re.compile(r"^### \d+\.\d+\s+", re.MULTILINE)


def normalize_subsection_id_in_text(text: str) -> tuple[str, int]:
    """Заменить `S1.01` → `S1.SS1`, `S1.10` → `S1.SS10`. Возвращает (new_text, count)."""
    count = 0
    def repl(m: re.Match) -> str:
        nonlocal count
        prefix = m.group(1)  # `subsection_id: PD.GUIDE.G.SX.`
        num = m.group(2)
        # Если уже SS — не трогаем (regex выше не матчит после SS, но на всякий)
        if prefix.endswith("SS"):
            return m.group(0)
        normalized_num = str(int(num))  # `01` → `1`, `10` → `10`
        count += 1
        return f"{prefix}SS{normalized_num}"
    new_text = SUBSECTION_ID_LINE_RE.sub(repl, text)
    return new_text, count


def find_blocks_format_dashes(text: str) -> list[tuple[int, int, str, str, str]]:
    """Для формата `--- subsection_id: ... ---` (guide-2/3).

    Возвращает список (start, end, frontmatter_text, subsection_id_full, title).
    """
    blocks = []
    # Frontmatter: between two `---` lines, where the content contains subsection_id
    pattern = re.compile(
        r"^---\s*\n((?:(?!^---\s*$).*\n)*?subsection_id:[^\n]*\n(?:(?!^---\s*$).*\n)*?)---\s*$",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        fm_content = m.group(1)
        sub_m = SUBSECTION_ID_RE.search(fm_content)
        title_m = TITLE_RE.search(fm_content)
        if sub_m and title_m:
            full_id = f"PD.GUIDE.{sub_m.group(1)}.S{sub_m.group(2)}.SS{sub_m.group(3)}"
            section_num = int(sub_m.group(2))
            ss_num = int(sub_m.group(3))
            title = title_m.group(1).strip().strip('"')
            blocks.append((m.start(), m.end(), fm_content, full_id, title, section_num, ss_num))
    return blocks


def find_blocks_format_yaml(text: str) -> list[tuple[int, int, str, str, str, int, int]]:
    """Для формата ```yaml...``` (guide-4).

    Возвращает список (start, end, yaml_text, subsection_id_full, title, section, ss).
    """
    blocks = []
    pattern = re.compile(r"^```yaml\n((?:(?!^```$).*\n)*?)```\s*$", re.MULTILINE)
    for m in pattern.finditer(text):
        yaml_content = m.group(1)
        sub_m = SUBSECTION_ID_RE.search(yaml_content)
        title_m = TITLE_RE.search(yaml_content)
        if sub_m and title_m:
            full_id = f"PD.GUIDE.{sub_m.group(1)}.S{sub_m.group(2)}.SS{sub_m.group(3)}"
            section_num = int(sub_m.group(2))
            ss_num = int(sub_m.group(3))
            title = title_m.group(1).strip().strip('"')
            blocks.append((m.start(), m.end(), yaml_content, full_id, title, section_num, ss_num))
    return blocks


def has_header_before(text: str, start: int, section: int, ss: int) -> bool:
    """Проверить, есть ли `### N.M ...` заголовок в 200 символах перед start."""
    window = text[max(0, start - 200):start]
    pattern = re.compile(rf"^### {section}\.{ss:02d}\s+", re.MULTILINE)
    return bool(pattern.search(window))


def detect_format(text: str) -> str:
    """yaml | dashes | mixed."""
    yaml_blocks = len(re.findall(r"^```yaml\n", text, re.MULTILINE))
    dash_subsec = len(re.findall(
        r"^---\s*\n(?:.*\n)*?subsection_id:[^\n]*\n(?:.*\n)*?^---\s*$",
        text, re.MULTILINE
    ))
    headers = len(HEADER_RE.findall(text))
    if yaml_blocks > 0 and headers >= yaml_blocks * 0.8:
        return "yaml-with-headers"  # эталон guide-1
    if yaml_blocks > 0 and headers < yaml_blocks * 0.2:
        return "yaml-no-headers"  # guide-4
    if dash_subsec > 0:
        return "dashes"  # guide-2/3
    return "unknown"


def process_file(path: Path, mode: str) -> int:
    """Returns count of changes."""
    text = path.read_text(encoding="utf-8")

    # Шаг 0: нормализовать subsection_id формат `S1.01` → `S1.SS1`
    text, ssid_fixes = normalize_subsection_id_in_text(text)
    if ssid_fixes:
        print(f"  subsection_id normalize: {ssid_fixes}", file=sys.stderr)

    fmt = detect_format(text)
    print(f"  Формат: {fmt}", file=sys.stderr)

    if fmt == "yaml-with-headers":
        if ssid_fixes and mode == "fix":
            # Уже в эталонном формате, но id были невалидными — сохраняем normalize
            bak = path.with_suffix(path.suffix + ".bak")
            shutil.copy(path, bak)
            path.write_text(text, encoding="utf-8")
            print(f"  {path.name}: subsection_id normalized ({ssid_fixes})", file=sys.stderr)
            return ssid_fixes
        print(f"  {path.name}: уже в эталонном формате — пропуск", file=sys.stderr)
        return ssid_fixes

    changes = ssid_fixes
    new_text = text

    if fmt == "yaml-no-headers":
        # guide-4: добавить ### N.M Title перед каждым yaml-блоком
        blocks = find_blocks_format_yaml(text)
        # Применяем в обратном порядке, чтобы offset'ы оставались валидными
        for start, end, yaml_text, full_id, title, section, ss in reversed(blocks):
            if has_header_before(new_text, start, section, ss):
                continue
            header = f"### {section}.{ss:02d} {title}\n\n"
            new_text = new_text[:start] + header + new_text[start:]
            changes += 1

    elif fmt == "dashes":
        # guide-2/3: конвертировать --- frontmatter --- в ### N.M Title + ```yaml ... ```
        blocks = find_blocks_format_dashes(text)
        for start, end, fm_content, full_id, title, section, ss in reversed(blocks):
            replacement = (
                f"### {section}.{ss:02d} {title}\n\n"
                f"```yaml\n{fm_content.rstrip()}\n```\n"
            )
            new_text = new_text[:start] + replacement + new_text[end:]
            changes += 1

    else:
        print(f"  {path.name}: формат `{fmt}` не поддерживается", file=sys.stderr)
        return 0

    if mode == "fix" and changes > 0:
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy(path, bak)
        path.write_text(new_text, encoding="utf-8")
        print(f"  {path.name}: +{changes} headers/conversions (бэкап .bak)", file=sys.stderr)
    elif mode == "lint":
        print(f"  {path.name}: было бы изменено {changes} блоков", file=sys.stderr)

    return changes


def main() -> int:
    p = argparse.ArgumentParser(description="Нормализация structure-guide-N.md")
    p.add_argument("--mode", choices=["lint", "fix"], default="lint")
    p.add_argument("files", nargs="+", help="structure-guide-N.md файлы")
    args = p.parse_args()

    total = 0
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"  {f}: не найден", file=sys.stderr)
            continue
        print(f"=== {path.name} ===", file=sys.stderr)
        total += process_file(path, args.mode)

    print(f"\nTOTAL: {total} изменений", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
