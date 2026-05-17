#!/usr/bin/env python3
"""
normalize-v4-subsection — нормализация legacy-подразделов v4.

Режимы:
  lint  — показать проблемы без изменения файлов
  fix   — применить исправления frontmatter (с бэкапом .md.bak)

Требует PyYAML. Если не установлен — создайте venv:
  python3 -m venv /tmp/yaml-venv && /tmp/yaml-venv/bin/pip install pyyaml
  /tmp/yaml-venv/bin/python tools/normalize-v4-subsection.py ...

Что исправляет (fix):
  • Добавляет wp: 300
  • Добавляет format_version: 4.1 (main) / 4.1-aux (auxiliary)
  • Добавляет time_reading, time_practice, word_count_target, status (main)
  • Убирает шифры Pack из introduces: (PD.FORM.NNN), (PD.METHOD.NNN)
  • Переводит prerequisites из §X.YY → PD.GUIDE.1.SX.SSY
  • Добавляет guide / section из subsection_id
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import OrderedDict
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML не установлен. Установите: python3 -m venv /tmp/yaml-venv && /tmp/yaml-venv/bin/pip install pyyaml", file=sys.stderr)
    sys.exit(1)

AUXILIARY_SUFFIXES = ("-concepts", "-exercises", "-review-questions", "-section-conclusions")
PACK_SHARD_RE = re.compile(r"\s*\(PD\.(FORM|METHOD|CAT)\.\d+[^)]*\)")
SECTION_REF_RE = re.compile(r"§(\d+)\.(\d+)")
FRONTMATTER_ORDER = [
    "wp", "guide", "section", "subsection_id", "title", "order",
    "introduces", "uses", "prerequisites", "mastery_node", "stage_relevant",
    "can_do", "cp_check", "bh_check", "bottleneck_hint",
    "time_reading", "time_practice", "word_count_target", "status", "format_version",
]


def is_auxiliary(path: Path) -> bool:
    return path.stem.endswith(AUXILIARY_SUFFIXES)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    block = parts[1].strip()
    body = parts[2]
    try:
        data = yaml.safe_load(block) or {}
    except yaml.YAMLError as e:
        print(f"[WARN] YAML parse error: {e}", file=sys.stderr)
        data = {}
    return data, body


def build_frontmatter(data: dict) -> str:
    ordered = OrderedDict()
    # Сначала ключи из FRONTMATTER_ORDER, потом остальные
    for k in FRONTMATTER_ORDER:
        if k in data:
            ordered[k] = data[k]
    for k, v in data.items():
        if k not in ordered:
            ordered[k] = v
    # yaml.safe_dump с дефолтным flow_style=False даёт многострочный yaml,
    # что ломает компактные списки. Используем custom representer для списков-строк.
    dump = yaml.safe_dump(dict(ordered), allow_unicode=True, sort_keys=False, default_flow_style=None, width=120)
    return "---\n" + dump + "---\n"


def clean_introduces(introduces: list[str]) -> list[str]:
    cleaned = []
    for item in introduces:
        item = PACK_SHARD_RE.sub("", item).strip()
        item = re.sub(r"\s+", " ", item)
        if item:
            cleaned.append(item)
    return cleaned


def translate_prerequisites(prereqs: list[str]) -> list[str]:
    translated = []
    for p in prereqs:
        m = SECTION_REF_RE.search(p)
        if m:
            sec, sub = int(m.group(1)), int(m.group(2))
            translated.append(f"PD.GUIDE.1.S{sec}.SS{sub}")
        else:
            translated.append(p)
    return translated


def normalize_file(path: Path, fix: bool) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if not fm:
        problems.append(f"  [ERROR] {path.name}: отсутствует frontmatter")
        return problems

    aux = is_auxiliary(path)
    changed = False

    # Определить guide/section из subsection_id
    sid = fm.get("subsection_id", "")
    m = re.search(r"PD\.GUIDE\.(\d+)\.S(\d+)\.SS(\d+)", sid)
    if m:
        if "guide" not in fm:
            fm["guide"] = int(m.group(1))
            changed = True
        if "section" not in fm:
            fm["section"] = int(m.group(2))
            changed = True
    else:
        problems.append(f"  [ERROR] {path.name}: невалидный subsection_id: {sid}")

    # wp
    if "wp" not in fm:
        fm["wp"] = 300
        changed = True
        problems.append(f"  [FIXED] {path.name}: добавлено wp: 300")

    # format_version
    if "format_version" not in fm:
        fm["format_version"] = "4.1-aux" if aux else "4.1"
        changed = True
        problems.append(f"  [FIXED] {path.name}: добавлен format_version: {fm['format_version']}")

    # meta-поля для main
    if not aux:
        for field in ["time_reading", "time_practice", "word_count_target", "status"]:
            if field not in fm:
                if field == "time_reading":
                    tm = re.search(r"\*\*Время:\*\*\s*(.+?)\n", body)
                    if tm:
                        fm[field] = tm.group(1).strip().split("=")[0].strip()
                    else:
                        fm[field] = "25 min"
                elif field == "time_practice":
                    tm = re.search(r"\*\*Время:\*\*\s*.+?=\s*(.+?)\n", body)
                    if tm:
                        fm[field] = tm.group(1).strip()
                    else:
                        fm[field] = "15 min"
                elif field == "word_count_target":
                    fm[field] = "500–1500"
                elif field == "status":
                    fm[field] = "pilot_draft"
                changed = True
                problems.append(f"  [FIXED] {path.name}: добавлено {field}: {fm[field]}")

    # Шифры в introduces
    if "introduces" in fm and isinstance(fm["introduces"], list):
        cleaned = clean_introduces(fm["introduces"])
        if cleaned != fm["introduces"]:
            removed = set(fm["introduces"]) - set(cleaned)
            fm["introduces"] = cleaned
            changed = True
            problems.append(f"  [FIXED] {path.name}: убраны шифры Pack из introduces: {removed}")

    # prerequisites §X.YY → PD.GUIDE...
    if "prerequisites" in fm and isinstance(fm["prerequisites"], list):
        translated = translate_prerequisites(fm["prerequisites"])
        if translated != fm["prerequisites"]:
            old = fm["prerequisites"]
            fm["prerequisites"] = translated
            changed = True
            problems.append(f"  [FIXED] {path.name}: prerequisites переведены {old} → {translated}")

    # Проверки без исправления
    if not aux:
        if "mastery_node" not in fm:
            problems.append(f"  [WARN] {path.name}: отсутствует mastery_node")
        if "stage_relevant" not in fm:
            problems.append(f"  [WARN] {path.name}: отсутствует stage_relevant")
        if "can_do" not in fm:
            problems.append(f"  [WARN] {path.name}: отсутствует can_do")
        if "cp_check" not in fm:
            problems.append(f"  [WARN] {path.name}: отсутствует cp_check")
        if "bh_check" not in fm:
            problems.append(f"  [WARN] {path.name}: отсутствует bh_check")

    if fix and changed:
        new_text = build_frontmatter(fm) + body
        # Бэкап
        shutil.copy2(path, path.with_suffix(".md.bak"))
        path.write_text(new_text, encoding="utf-8")
        problems.append(f"  [SAVED] {path.name} (бэкап .md.bak)")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Нормализация v4-подразделов")
    parser.add_argument("directory", type=Path, help="Директория с .md файлами")
    parser.add_argument("--mode", choices=["lint", "fix"], default="lint", help="Режим")
    parser.add_argument("--section", type=int, default=None, help="Обработать только одну секцию (например, 6)")
    args = parser.parse_args()

    if not args.directory.exists():
        print(f"[ERROR] Директория не существует: {args.directory}", file=sys.stderr)
        return 1

    all_problems: list[str] = []
    for path in sorted(args.directory.rglob("*.md")):
        if args.section is not None:
            if not re.search(rf"s{args.section}-", str(path.parent)):
                continue
        probs = normalize_file(path, fix=(args.mode == "fix"))
        all_problems.extend(probs)

    if all_problems:
        print(f"\nНайдено {len(all_problems)} замечаний:\n")
        for p in all_problems:
            print(p)
    else:
        print("\nВсе подразделы соответствуют v4-формату.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
