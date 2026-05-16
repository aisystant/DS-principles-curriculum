#!/usr/bin/env python3
"""
v4-lint — валидатор конвейера написания подразделов универсальных руководств v4.

Покрывает Этапы 2, 8, 10, 14 из specs/v4-reference/WRITING-PIPELINE.md.
Контракт инструмента: ~/IWE/DS-my-strategy/inbox/WP-321-v4-lint-validators.md

Подкоманды:
  structure   — синтаксис structure-guide-N.md (Этап 2)
  porter      — frontmatter подразделов для алгоритма Портного (Этап 8)
  cross-guide — один концепт = одно определение в 4 руководствах (Этап 10)
  pack-drift  — упоминания cp.*/bh.* соответствуют PD.FORM.089 (Этап 14)

Exit codes: 0 PASS, 1 FAIL, 2 INTERNAL_ERROR.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

VALID_MASTERY_NODES = {"мыслительное", "саморазвитие", "iwe"}
VALID_STAGES = {1, 2, 3, 4, 5}
CONCEPT_MARKERS = {
    "вводится", "используется", "противопоставлен", "сослан",
    "кейс в тексте", "аналогия в тексте",
}

SUBSECTION_ID_RE = re.compile(r"PD\.GUIDE\.([1-4])\.S(\d+)\.SS(\d+)")
SECTION_HEADER_RE = re.compile(r"^##\s+Раздел\s+(\d+)\.")
SUBSECTION_HEADER_RE = re.compile(r"^###\s+(\d+)\.(\d+)\s+")
INLINE_YAML_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
CP_BH_RE = re.compile(r"\b(cp\.[a-z]+|bh\.[a-z]+)\b")


@dataclass
class Subsection:
    """Распарсенный подраздел из structure-guide-N.md."""
    file: Path
    guide: int                    # 1..4
    section: int                  # 1..N
    order: int                    # порядковый внутри раздела
    subsection_id: str            # PD.GUIDE.G.SX.SSY
    title: str
    frontmatter: dict = field(default_factory=dict)
    concepts: list[dict] = field(default_factory=list)  # [{marker, name, parent, ref}]
    raw_concept_lines: list[str] = field(default_factory=list)
    line_start: int = 0


@dataclass
class Section:
    file: Path
    guide: int
    section: int
    title: str
    frontmatter: dict = field(default_factory=dict)
    subsections: list[Subsection] = field(default_factory=list)


@dataclass
class Finding:
    severity: str   # "error" | "warning"
    file: Path
    line: int | None
    message: str

    def fmt(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else str(self.file)
        sev = "FAIL" if self.severity == "error" else "WARN"
        return f"[{sev}] {loc}  {self.message}"


# ============================================================================
# Парсер
# ============================================================================

def _coerce_scalar(value: str):
    value = value.strip().strip('"').strip("'")
    try:
        return int(value)
    except ValueError:
        return value


def parse_yaml_block(block: str) -> dict:
    """YAML-парсер для inline-блоков: `key: value`, `key: [a, b]`, multi-line `- item`."""
    data: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        if not raw or raw.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r'^([a-z_][a-z0-9_]*)\s*:\s*(.*)$', raw)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_coerce_scalar(x) for x in inner.split(",")] if inner else []
            i += 1
            continue
        if not value:
            items: list = []
            j = i + 1
            while j < len(lines):
                child = lines[j]
                if not child.strip():
                    j += 1
                    continue
                cm = re.match(r'^(\s+)-\s+(.+)$', child)
                if cm:
                    items.append(_coerce_scalar(cm.group(2)))
                    j += 1
                    continue
                break
            data[key] = items if items else ""
            i = j
            continue
        data[key] = _coerce_scalar(value)
        i += 1
    return data


def parse_concepts_block(lines: list[str], start_idx: int) -> tuple[list[dict], list[str], int]:
    """Разобрать блок **Понятия:** начиная с start_idx. Возвращает (concepts, raw_lines, next_idx)."""
    concepts: list[dict] = []
    raw: list[str] = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("- "):
            raw.append(line)
            content = stripped[2:].strip()
            m = re.match(r'^([а-яА-Я ]+?):\s*(.+)$', content)
            if m:
                marker = m.group(1).strip()
                rest = m.group(2).strip()
                if marker in CONCEPT_MARKERS:
                    concept = {"marker": marker, "raw": content}
                    name = rest.split("→")[0].strip() if "→" in rest else rest
                    arrow_m = re.search(r'→\s*`?(U\.[A-Za-z]+)`?', rest)
                    if arrow_m:
                        concept["parent"] = arrow_m.group(1)
                    ref_m = re.search(r'(?:см\.\s+)?(\d+\.S\d+\.SS\d+)', rest)
                    if ref_m:
                        concept["ref"] = ref_m.group(1)
                    name = re.split(r'\s+—|\s+\(|\s+\bсм\.', name)[0].strip()
                    concept["name"] = name
                    concepts.append(concept)
                else:
                    raw.append(f"<unknown-marker:{marker}>")
            i += 1
            continue
        if not stripped:
            i += 1
            continue
        break
    return concepts, raw, i


def parse_structure_file(path: Path) -> tuple[list[Section], list[Finding]]:
    """Распарсить structure-guide-N.md, вернуть разделы + ошибки парсинга."""
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [], [Finding("error", path, None, f"не могу прочитать файл: {e}")]

    guide_match = re.search(r"PD\.GUIDE\.([1-4])\.STRUCTURE", text)
    if not guide_match:
        return [], [Finding("error", path, None, "не найден id PD.GUIDE.<N>.STRUCTURE")]
    guide = int(guide_match.group(1))

    sections: list[Section] = []
    lines = text.splitlines()
    current_section: Section | None = None
    current_subsection: Subsection | None = None
    order_in_section = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        sec_m = SECTION_HEADER_RE.match(line)
        sub_m = SUBSECTION_HEADER_RE.match(line)

        if sec_m:
            current_section = Section(file=path, guide=guide,
                                      section=int(sec_m.group(1)),
                                      title=line.lstrip("# ").strip())
            sections.append(current_section)
            order_in_section = 0
            current_subsection = None
            if i + 2 < len(lines) and lines[i + 2].strip() == "```yaml":
                end = i + 3
                while end < len(lines) and lines[end].strip() != "```":
                    end += 1
                yaml_text = "\n".join(lines[i + 3:end])
                current_section.frontmatter = parse_yaml_block(yaml_text)
                i = end + 1
                continue
        elif sub_m and current_section is not None:
            order_in_section += 1
            current_subsection = Subsection(
                file=path, guide=guide, section=current_section.section,
                order=order_in_section, subsection_id="", title=line.lstrip("# ").strip(),
                line_start=i + 1,
            )
            current_section.subsections.append(current_subsection)
            if i + 2 < len(lines) and lines[i + 2].strip() == "```yaml":
                end = i + 3
                while end < len(lines) and lines[end].strip() != "```":
                    end += 1
                yaml_text = "\n".join(lines[i + 3:end])
                current_subsection.frontmatter = parse_yaml_block(yaml_text)
                current_subsection.subsection_id = current_subsection.frontmatter.get("subsection_id", "")
                i = end + 1
                continue
        elif "**Понятия:**" in line and current_subsection is not None:
            concepts, raw, next_i = parse_concepts_block(lines, i + 1)
            current_subsection.concepts = concepts
            current_subsection.raw_concept_lines = raw
            i = next_i
            continue
        i += 1

    return sections, findings


def parse_pack_form089(path: Path) -> dict:
    """Извлечь множество валидных cp.* / bh.* из FORM.089."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"cp": set(), "bh": set()}
    cp_set: set[str] = set()
    bh_set: set[str] = set()
    for m in CP_BH_RE.finditer(text):
        token = m.group(1)
        if token.startswith("cp."):
            cp_set.add(token)
        elif token.startswith("bh."):
            bh_set.add(token)
    return {"cp": cp_set, "bh": bh_set}


# ============================================================================
# Subcommand: structure (Этап 2)
# ============================================================================

def cmd_structure(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="structure")
    all_subsections_by_guide: dict[int, list[Subsection]] = defaultdict(list)

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        check_section_ordering(f, sections, findings)
        check_subsection_completeness(f, sections, findings)
        check_concept_format(sections, findings)
        for sec in sections:
            for sub in sec.subsections:
                all_subsections_by_guide[sub.guide].append(sub)

    check_homonyms(all_subsections_by_guide, findings)

    return report(findings, label="structure")


def collect_structure_files(targets: list[Path], strict: bool = True) -> tuple[list[Path], list[Finding]]:
    """Собрать structure-guide-N.md из путей. При strict=True пустой результат → Finding(error)."""
    files: list[Path] = []
    findings: list[Finding] = []
    for t in targets:
        if not t.exists():
            findings.append(Finding("error", t, None, f"путь не существует: {t}"))
            continue
        if t.is_dir():
            matches = sorted(t.glob("0?-structure-guide-*.md"))
            if not matches:
                findings.append(Finding(
                    "warning", t, None,
                    f"в директории нет файлов вида 0?-structure-guide-*.md",
                ))
            files.extend(matches)
        elif t.is_file():
            files.append(t)
    if strict and not files and not findings:
        findings.append(Finding("error", Path("."), None, "не найдено ни одного файла для проверки"))
    return files, findings


def check_section_ordering(file: Path, sections: list[Section], findings: list[Finding]) -> None:
    """Численная сортировка S1, S2, ..., S10 (не S1, S10, S2)."""
    nums = [s.section for s in sections]
    expected = sorted(nums)
    if nums != expected:
        findings.append(Finding(
            "error", file, None,
            f"разделы не отсортированы численно: {nums} (ожидалось {expected})",
        ))


def check_subsection_completeness(file: Path, sections: list[Section], findings: list[Finding]) -> None:
    """SS-номера непрерывны в каждом разделе (нет пропусков)."""
    for sec in sections:
        if not sec.subsections:
            findings.append(Finding(
                "warning", file, None,
                f"раздел S{sec.section} не содержит подразделов",
            ))
            continue
        ids: list[int] = []
        for sub in sec.subsections:
            m = SUBSECTION_ID_RE.search(sub.subsection_id)
            if m:
                ids.append(int(m.group(3)))
            else:
                findings.append(Finding(
                    "error", file, sub.line_start,
                    f"подраздел без subsection_id (заголовок: {sub.title})",
                ))
        if ids:
            expected_ids = list(range(1, max(ids) + 1))
            missing = set(expected_ids) - set(ids)
            if missing:
                findings.append(Finding(
                    "error", file, None,
                    f"раздел S{sec.section}: пропущены SS-номера: {sorted(missing)}",
                ))


def check_concept_format(sections: list[Section], findings: list[Finding]) -> None:
    """Формат «Понятия:» — нет `(` в начале имени, маркер из словаря."""
    for sec in sections:
        for sub in sec.subsections:
            for raw_line in sub.raw_concept_lines:
                if raw_line.startswith("<unknown-marker"):
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: неизвестный маркер в «Понятия:» — {raw_line}",
                    ))
            for concept in sub.concepts:
                name = concept.get("name", "")
                if name.startswith("("):
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: имя понятия начинается с `(` — парсер сломается: «{name}»",
                    ))


def check_homonyms(by_guide: dict[int, list[Subsection]], findings: list[Finding]) -> None:
    """Одно имя с разным parent U.* без квалификатора = омоним → FAIL."""
    name_to_parents: dict[str, set[str]] = defaultdict(set)
    name_to_locations: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for guide, subs in by_guide.items():
        for sub in subs:
            for concept in sub.concepts:
                if concept.get("marker") != "вводится":
                    continue
                name = concept.get("name", "").strip()
                parent = concept.get("parent")
                if not name or not parent:
                    continue
                name_to_parents[name].add(parent)
                name_to_locations[name].append((sub.file, sub.subsection_id))

    for name, parents in name_to_parents.items():
        if len(parents) > 1:
            locs = ", ".join(f"{loc[0].name}#{loc[1]}" for loc in name_to_locations[name])
            findings.append(Finding(
                "error", name_to_locations[name][0][0], None,
                f"омоним «{name}» вводится с разными родителями {sorted(parents)} в [{locs}] — добавь квалификатор",
            ))


# ============================================================================
# Subcommand: porter (Этап 8)
# ============================================================================

PORTER_REQUIRED_FIELDS = ["subsection_id", "title", "cp_check", "bh_check"]
PORTER_RECOMMENDED_FIELDS = ["mastery_node", "stage_relevant", "introduces", "uses",
                              "prerequisites", "can_do", "bottleneck_hint"]


def cmd_porter(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="porter")

    known_ids: set[str] = set()
    all_subs: list[Subsection] = []
    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        for sec in sections:
            for sub in sec.subsections:
                if sub.subsection_id:
                    known_ids.add(sub.subsection_id)
                all_subs.append(sub)

    for sub in all_subs:
        check_porter_frontmatter(sub, known_ids, findings)

    return report(findings, label="porter")


def check_porter_frontmatter(sub: Subsection, known_ids: set[str], findings: list[Finding]) -> None:
    fm = sub.frontmatter

    for field_name in PORTER_REQUIRED_FIELDS:
        if field_name not in fm or fm[field_name] in (None, "", []):
            findings.append(Finding(
                "error", sub.file, sub.line_start,
                f"{sub.subsection_id or '<no-id>'}: отсутствует обязательное поле `{field_name}`",
            ))

    mastery = fm.get("mastery_node")
    if mastery:
        nodes = mastery if isinstance(mastery, list) else [mastery]
        for node in nodes:
            if node not in VALID_MASTERY_NODES:
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: mastery_node «{node}» не из словаря {sorted(VALID_MASTERY_NODES)}",
                ))

    stage = fm.get("stage_relevant")
    if stage:
        stages = stage if isinstance(stage, list) else [stage]
        for s in stages:
            if not isinstance(s, int) or s not in VALID_STAGES:
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: stage_relevant содержит невалидное значение «{s}» (ожидается 1-5)",
                ))

    can_do = fm.get("can_do")
    if can_do:
        items = can_do if isinstance(can_do, list) else [can_do]
        for item in items:
            if isinstance(item, str) and not item.lstrip().lower().startswith("могу"):
                findings.append(Finding(
                    "warning", sub.file, sub.line_start,
                    f"{sub.subsection_id}: can_do элемент не начинается с «Могу»: «{item[:60]}»",
                ))

    introduces = fm.get("introduces", [])
    if isinstance(introduces, list):
        for name in introduces:
            if isinstance(name, str) and name.startswith("U."):
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: в `introduces` указан U.*-тип «{name}» — должно быть каноническое имя",
                ))

    prereqs = fm.get("prerequisites", [])
    if isinstance(prereqs, list):
        for ref in prereqs:
            if not isinstance(ref, str):
                continue
            m = SUBSECTION_ID_RE.search(ref)
            if m and known_ids and ref not in known_ids:
                findings.append(Finding(
                    "warning", sub.file, sub.line_start,
                    f"{sub.subsection_id}: prerequisite «{ref}» не найден среди известных подразделов",
                ))


# ============================================================================
# Subcommand: cross-guide (Этап 10)
# ============================================================================

def cmd_cross_guide(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="cross-guide")

    introduces_map: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    all_known_ids: set[str] = set()
    uses_list: list[tuple[str, Path, str]] = []  # (name, file, subsection_id)

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        for sec in sections:
            for sub in sec.subsections:
                if sub.subsection_id:
                    all_known_ids.add(sub.subsection_id)
                for concept in sub.concepts:
                    name = concept.get("name", "").strip()
                    if not name:
                        continue
                    marker = concept.get("marker")
                    if marker == "вводится":
                        introduces_map[name].append((f, sub.subsection_id))
                    elif marker == "используется":
                        uses_list.append((name, f, sub.subsection_id))

    for name, locations in introduces_map.items():
        if len(locations) > 1:
            locs_fmt = ", ".join(f"{loc[0].name}#{loc[1]}" for loc in locations)
            findings.append(Finding(
                "error", locations[0][0], None,
                f"понятие «{name}» вводится {len(locations)}× — должно быть одно определение: [{locs_fmt}]",
            ))

    for name, file, sub_id in uses_list:
        if name not in introduces_map:
            findings.append(Finding(
                "warning", file, None,
                f"{sub_id}: «{name}» помечено как `используется`, но `вводится` нигде не найдено",
            ))

    return report(findings, label="cross-guide")


# ============================================================================
# Subcommand: pack-drift (Этап 14)
# ============================================================================

def cmd_pack_drift(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="pack-drift")

    if args.pack:
        pack_path = Path(args.pack)
        if not pack_path.exists():
            findings.append(Finding(
                "error", pack_path, None,
                f"Pack-файл не найден: {pack_path}",
            ))
            return report(findings, label="pack-drift")
        pack_data = parse_pack_form089(pack_path)
        known_cp = pack_data["cp"]
        known_bh = pack_data["bh"]
        if not known_cp and not known_bh:
            findings.append(Finding(
                "error", pack_path, None,
                "Pack-файл не содержит cp.*/bh.* упоминаний — проверьте корректность пути",
            ))
            return report(findings, label="pack-drift")
    else:
        findings.append(Finding(
            "error", Path("."), None,
            "pack-drift требует --pack <путь к PD.FORM.089-learner-rcs.md>. "
            "Семенной словарь не используется как fallback (избегаем silent stale-data).",
        ))
        return report(findings, label="pack-drift")

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        for sec in sections:
            for sub in sec.subsections:
                check_pack_drift_in_frontmatter(sub, known_cp, known_bh, findings)
                check_pack_drift_in_text(sub, known_cp, known_bh, findings)

    return report(findings, label="pack-drift")


def check_pack_drift_in_frontmatter(sub: Subsection, known_cp: set[str], known_bh: set[str],
                                     findings: list[Finding]) -> None:
    for key in ("cp_check", "bh_check"):
        values = sub.frontmatter.get(key, [])
        if not isinstance(values, list):
            values = [values]
        valid_set = known_cp if key == "cp_check" else known_bh
        for v in values:
            if not isinstance(v, str):
                continue
            if v not in valid_set:
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: {key} содержит неизвестный индекс «{v}» — не найден в Pack",
                ))


def check_pack_drift_in_text(sub: Subsection, known_cp: set[str], known_bh: set[str],
                              findings: list[Finding]) -> None:
    text_blob = " ".join(sub.raw_concept_lines) + " " + sub.title
    for m in CP_BH_RE.finditer(text_blob):
        token = m.group(1)
        if token.startswith("cp.") and token not in known_cp:
            findings.append(Finding(
                "warning", sub.file, sub.line_start,
                f"{sub.subsection_id}: упомянут неизвестный «{token}» — не найден в Pack",
            ))
        if token.startswith("bh.") and token not in known_bh:
            findings.append(Finding(
                "warning", sub.file, sub.line_start,
                f"{sub.subsection_id}: упомянут неизвестный «{token}» — не найден в Pack",
            ))


# ============================================================================
# Отчёт
# ============================================================================

def report(findings: list[Finding], label: str) -> int:
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    for f in findings:
        print(f.fmt())
    summary = f"\n[{label}] errors={len(errors)} warnings={len(warnings)}"
    print(summary, file=sys.stderr)
    if errors:
        return 1
    return 0


# ============================================================================
# CLI
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="v4-lint",
        description="Валидатор конвейера v4 руководств (см. WRITING-PIPELINE.md этапы 2/8/10/14)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_struct = sub.add_parser("structure", help="Этап 2: синтаксис structure-guide-N.md")
    p_struct.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_struct.set_defaults(func=cmd_structure)

    p_porter = sub.add_parser("porter", help="Этап 8: frontmatter подразделов для Портного")
    p_porter.add_argument("paths", nargs="+")
    p_porter.set_defaults(func=cmd_porter)

    p_cross = sub.add_parser("cross-guide", help="Этап 10: один концепт = одно определение")
    p_cross.add_argument("paths", nargs="+")
    p_cross.set_defaults(func=cmd_cross_guide)

    p_drift = sub.add_parser("pack-drift", help="Этап 14: cp/bh упоминания vs Pack FORM.089")
    p_drift.add_argument("paths", nargs="+")
    p_drift.add_argument("--pack", help="Путь к PD.FORM.089-learner-rcs.md")
    p_drift.set_defaults(func=cmd_pack_drift)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"[INTERNAL ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
