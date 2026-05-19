#!/usr/bin/env python3
"""
check-pack-gap.py — Ф11 Pack-sufficiency gate (WP-322).

Проверяет, что каждое понятие из `вводится:` в structure-guide-N.md
зарегистрировано в §2 Глоссарий файла PACK-personal/ontology.md.

Использование:
  # Полная проверка всех руководств:
  python3 tools/check-pack-gap.py specs/v4-reference/ \\
      --ontology PACK-personal/ontology.md

  # Diff-режим (только новые `вводится` в PR, не в базовой ветке):
  python3 tools/check-pack-gap.py specs/v4-reference/ \\
      --ontology PACK-personal/ontology.md --diff HEAD~1

Exit codes: 0 = PASS, 1 = FAIL (есть понятия вне онтологии), 2 = INTERNAL_ERROR.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

INTRODUCES_RE = re.compile(
    r"^\s*-\s*вводится:\s*(.+?)(?:\s*→|\s*\(|$)",
    re.IGNORECASE,
)
ONTOLOGY_TERM_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*")
STRUCTURE_GUIDE_GLOB = "*-structure-guide-*.md"


def parse_ontology_terms(ontology_path: Path) -> set[str]:
    """Extract all term names from §2 glossary table of ontology.md."""
    text = ontology_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    in_section2 = False
    terms: set[str] = set()
    for line in lines:
        if re.match(r"^## 2\.", line):
            in_section2 = True
            continue
        if in_section2 and re.match(r"^## [3-9]\.", line):
            break
        if in_section2:
            m = ONTOLOGY_TERM_RE.match(line)
            if m:
                terms.add(m.group(1).strip())
    return terms


def extract_introduces_from_text(text: str) -> list[str]:
    """Return concept names from `- вводится: X` lines in text."""
    concepts = []
    for line in text.splitlines():
        m = INTRODUCES_RE.match(line)
        if m:
            raw = m.group(1).strip().rstrip("→").strip()
            if raw:
                concepts.append(raw)
    return concepts


def collect_full(guides_dir: Path) -> dict[str, list[str]]:
    """Map filename → list of concept names across all structure guides."""
    result: dict[str, list[str]] = {}
    for f in sorted(guides_dir.glob(STRUCTURE_GUIDE_GLOB)):
        concepts = extract_introduces_from_text(f.read_text(encoding="utf-8"))
        if concepts:
            result[str(f)] = concepts
    return result


def collect_diff(guides_dir: Path, base_ref: str) -> dict[str, list[str]]:
    """Map filename → new concept names added relative to base_ref."""
    try:
        proc = subprocess.run(
            ["git", "diff", base_ref, "--", str(guides_dir / STRUCTURE_GUIDE_GLOB)],
            capture_output=True, text=True, check=True,
        )
        diff_text = proc.stdout
    except subprocess.CalledProcessError as e:
        print(f"INTERNAL_ERROR: git diff failed: {e.stderr}", file=sys.stderr)
        sys.exit(2)

    result: dict[str, list[str]] = {}
    current_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if line.startswith("+") and not line.startswith("+++") and current_file:
            m = INTRODUCES_RE.match(line[1:])
            if m:
                raw = m.group(1).strip().rstrip("→").strip()
                if raw:
                    result.setdefault(current_file, []).append(raw)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guides_dir", type=Path,
                        help="Путь к папке specs/v4-reference/")
    parser.add_argument("--ontology", type=Path, required=True,
                        help="Путь к PACK-personal/ontology.md")
    parser.add_argument("--diff", metavar="BASE_REF",
                        help="Git-ref базовой ветки (только новые вводится из diff)")
    args = parser.parse_args()

    if not args.guides_dir.exists():
        print(f"INTERNAL_ERROR: guides_dir не найден: {args.guides_dir}", file=sys.stderr)
        return 2
    if not args.ontology.exists():
        print(f"INTERNAL_ERROR: ontology не найден: {args.ontology}", file=sys.stderr)
        return 2

    ontology_terms = parse_ontology_terms(args.ontology)
    if not ontology_terms:
        print("INTERNAL_ERROR: §2 онтологии пуст — проверьте формат файла", file=sys.stderr)
        return 2

    if args.diff:
        introduces_map = collect_diff(args.guides_dir, args.diff)
        mode_label = f"diff от {args.diff}"
    else:
        introduces_map = collect_full(args.guides_dir)
        mode_label = "полная проверка"

    gaps: list[tuple[str, str]] = []
    total = 0
    for filename, concepts in introduces_map.items():
        for concept in concepts:
            total += 1
            if concept not in ontology_terms:
                gaps.append((filename, concept))

    print(f"pack-gap ({mode_label}): {total} понятий проверено, {len(gaps)} вне онтологии")

    if gaps:
        print()
        print("❌ Понятия, отсутствующие в ontology.md §2:")
        for filename, concept in gaps:
            print(f"  {filename}: «{concept}»")
        print()
        print("Действие: добавить понятие в PACK-personal/ontology.md §2 (Глоссарий домена)")
        print("          или убедиться, что написание совпадает с записью в онтологии.")
        return 1

    print(f"✅ Все понятия зарегистрированы в ontology.md §2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
