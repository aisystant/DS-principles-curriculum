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

# A.11 Ontological Parsimony: предел «вводится» на подраздел (FPF A.11, WRITING-PIPELINE §«Распределение понятий»).
A11_INTRODUCES_LIMIT = 3

# A.1.1 Bounded Context: руководства 1-2 не вводят и не упоминают IWE-узел (WRITING-PIPELINE Этап 4 п.4).
GUIDES_FORBID_IWE = {1, 2}

# Кейсы и аналогии, которые не должны попадать в `вводится` (это иллюстрации, не понятия).
# Источник: 07-concept-candidates-v4.md «Кейсы (не понятия)». Сравнение через substring (lowercased).
# Корни выбраны так, чтобы покрыть русские формы (Земмельвейс / Земмельвейса) и при этом
# не давать ложных срабатываний на реальные понятия (Аудит Болида — это U.Method, не случай).
KNOWN_CASE_TOKENS = {
    "земмельвейс",   # «Эффект Земмельвейса» и пр.
    "хохланд",       # «Хохланд» (корпоративный кейс)
}

SUBSECTION_ID_RE = re.compile(r"PD\.GUIDE\.([1-4])\.S(\d+)\.SS(\d+)")
SECTION_HEADER_RE = re.compile(r"^##\s+Раздел\s+(\d+)\.")
SUBSECTION_HEADER_RE = re.compile(r"^###\s+(\d+)\.(\d+)\s+")
INLINE_YAML_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
CP_BH_RE = re.compile(r"\b(cp\.[a-z]+|bh\.[a-z]+)\b")
# Источник Pack: PD.FORM.NNN / PD.METHOD.NNN / PD.CAT.NNN. Без префикса PD. не считается.
PACK_SOURCE_RE = re.compile(r"\bPD\.(?:FORM|METHOD|CAT)\.\d+")
UTYPE_RE = re.compile(r"U\.[A-Za-z]+")


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
    """Разобрать блок **Понятия:** начиная с start_idx. Возвращает (concepts, raw_lines, next_idx).

    Каждый concept: {marker, name, raw, parent?, pack_source?, ref?}.
    raw_lines включают спец-маркеры `<unknown-marker:X>` и `<malformed-bullet:LINE>` для FAIL-репортинга.
    """
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
            if not m:
                raw.append(f"<malformed-bullet:{content[:60]}>")
                i += 1
                continue
            marker = m.group(1).strip()
            rest = m.group(2).strip()
            if marker not in CONCEPT_MARKERS:
                raw.append(f"<unknown-marker:{marker}>")
                i += 1
                continue
            concept = {"marker": marker, "raw": content}
            name = rest.split("→")[0].strip() if "→" in rest else rest
            # Parent — первый U.* ПОСЛЕ первого `→` (canonical format `имя → U.Type (комментарий)`).
            # Если `→` нет — ищем во всей строке как fallback (deprecated формат).
            after_arrow = rest.split("→", 1)[1] if "→" in rest else rest
            arrow_m = UTYPE_RE.search(after_arrow)
            if arrow_m:
                concept["parent"] = arrow_m.group(0)
            ref_m = re.search(r'(?:см\.\s+)?(\d+\.S\d+\.SS\d+)', rest)
            if ref_m:
                concept["ref"] = ref_m.group(1)
            pack_m = PACK_SOURCE_RE.search(rest)
            if pack_m:
                concept["pack_source"] = pack_m.group(0)
            name = re.split(r'\s+—|\s+\(|\s+\bсм\.', name)[0].strip()
            concept["name"] = name
            concepts.append(concept)
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
        check_introduces_limit(sections, findings)
        check_evidence_graph(sections, findings)
        check_triple_identification(sections, findings)
        check_cases_in_introduces(sections, findings)
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
    """Формат «Понятия:» — нет `(` в начале имени, маркер из словаря, нет malformed-bullet."""
    for sec in sections:
        for sub in sec.subsections:
            for raw_line in sub.raw_concept_lines:
                if raw_line.startswith("<unknown-marker"):
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: неизвестный маркер в «Понятия:» — {raw_line}. "
                        f"Допустимые: {sorted(CONCEPT_MARKERS)}",
                    ))
                elif raw_line.startswith("<malformed-bullet"):
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: строка в «Понятия:» без маркера-двоеточия — {raw_line}",
                    ))
            for concept in sub.concepts:
                name = concept.get("name", "")
                if name.startswith("("):
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: имя понятия начинается с `(` — парсер сломается: «{name}»",
                    ))


def check_introduces_limit(sections: list[Section], findings: list[Finding]) -> None:
    """A.11 Ontological Parsimony: ≤A11_INTRODUCES_LIMIT понятий «вводится» на подраздел."""
    for sec in sections:
        for sub in sec.subsections:
            intro_count = sum(1 for c in sub.concepts if c.get("marker") == "вводится")
            if intro_count > A11_INTRODUCES_LIMIT:
                names = [c.get("name", "?") for c in sub.concepts if c.get("marker") == "вводится"]
                findings.append(Finding(
                    "warning", sub.file, sub.line_start,
                    f"{sub.subsection_id}: вводится {intro_count} понятий (предел A.11 = "
                    f"{A11_INTRODUCES_LIMIT}). Список: {names}. Раздели на несколько подразделов "
                    f"или пометь часть как `используется`.",
                ))


def check_evidence_graph(sections: list[Section], findings: list[Finding]) -> None:
    """A.10 Evidence Graph: каждое «вводится» должно иметь источник Pack (PD.FORM/METHOD/CAT.NNN).

    На этапе перехода — WARN (Pack source отсутствует у ~80% существующих понятий в
    `01-structure-guide-1.md`). Промоция WARN → FAIL: открыть РП по миграции корпуса,
    при ≥95% покрытии и установившемся плато 1 неделю поменять severity на `error`.
    Критерий проверки: `python3 tools/v4-lint.py structure specs/v4-reference/ 2>&1 |
    grep -c "без источника Pack"` ≤ N (целевое <5 на весь корпус).
    """
    for sec in sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                if concept.get("marker") != "вводится":
                    continue
                if not concept.get("pack_source"):
                    name = concept.get("name", "?")
                    findings.append(Finding(
                        "warning", sub.file, sub.line_start,
                        f"{sub.subsection_id}: «{name}» вводится без источника Pack "
                        f"(ожидается `(PD.FORM.NNN)` или `(PD.METHOD.NNN)` в строке) — A.10 Evidence Graph.",
                    ))


def check_triple_identification(sections: list[Section], findings: list[Finding]) -> None:
    """Тройка идентификации: имя + parent U.* + источник Pack — для каждого «вводится».

    Имя отсутствует → FAIL (это аномалия парсинга / некорректная строка).
    Parent U.* отсутствует → WARN. Pack source отсутствует уже ловится `check_evidence_graph` —
    не дублируем (избегаем двойного WARN на одну строку).
    """
    for sec in sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                if concept.get("marker") != "вводится":
                    continue
                name = (concept.get("name") or "").strip()
                if not name:
                    findings.append(Finding(
                        "error", sub.file, sub.line_start,
                        f"{sub.subsection_id}: строка `вводится` без имени понятия — "
                        f"проверь формат.",
                    ))
                    continue
                if not concept.get("parent"):
                    findings.append(Finding(
                        "warning", sub.file, sub.line_start,
                        f"{sub.subsection_id}: «{name}» вводится без `parent U.*` "
                        f"(ожидается U.System / U.Episteme / U.Method и т.д.).",
                    ))


def check_cases_in_introduces(sections: list[Section], findings: list[Finding]) -> None:
    """Кейсы и аналогии не должны попадать в `вводится` — это иллюстрации, не понятия."""
    for sec in sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                if concept.get("marker") != "вводится":
                    continue
                name = (concept.get("name") or "").strip()
                if not name:
                    continue
                lowered = name.lower()
                for token in KNOWN_CASE_TOKENS:
                    if token in lowered:
                        findings.append(Finding(
                            "error", sub.file, sub.line_start,
                            f"{sub.subsection_id}: «{name}» зарегистрирован как кейс/аналогия "
                            f"(07-concept-candidates-v4.md), не должен вводиться как понятие. "
                            f"Используй маркер `кейс в тексте:` или `аналогия в тексте:`.",
                        ))
                        break


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
        if "iwe" in nodes and sub.guide in GUIDES_FORBID_IWE:
            findings.append(Finding(
                "error", sub.file, sub.line_start,
                f"{sub.subsection_id}: mastery_node `iwe` запрещён в руководствах "
                f"{sorted(GUIDES_FORBID_IWE)} (A.1.1 Bounded Context, "
                f"WRITING-PIPELINE Этап 4 п.4).",
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
# Subcommand: graph (заменяет упомянутый, но не реализованный build-structure-overview.py)
# ============================================================================

EDGE_MARKERS = {
    "используется": "uses",
    "противопоставлен": "contrast",
    "сослан": "see-also",
}


def cmd_graph(args: argparse.Namespace) -> int:
    """Диспетчер подкоманд graph (build / diff). Обёрнут в общий error handler."""
    return args.graph_func(args)


def cmd_graph_build(args: argparse.Namespace) -> int:
    """Построить концепт-граф из specs/v4-reference/: узлы = «вводится», рёбра = ссылки."""
    import json

    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="graph build")

    nodes: dict[str, dict] = {}  # name → {parent, pack_source, guide, subsection_id, mastery_node, stage_relevant}
    edges: list[dict] = []        # {source: subsection_id, target: concept_name, type: uses/contrast/see-also}

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        for sec in sections:
            for sub in sec.subsections:
                for concept in sub.concepts:
                    marker = concept.get("marker")
                    name = (concept.get("name") or "").strip()
                    if not name:
                        continue
                    if marker == "вводится":
                        if name in nodes:
                            # дубликат — оставляем первое, фиксируем как finding
                            findings.append(Finding(
                                "warning", sub.file, sub.line_start,
                                f"граф: понятие «{name}» уже введено в "
                                f"{nodes[name]['subsection_id']}; повторное введение игнорируется",
                            ))
                            continue
                        nodes[name] = {
                            "name": name,
                            "parent": concept.get("parent"),
                            "pack_source": concept.get("pack_source"),
                            "guide": sub.guide,
                            "subsection_id": sub.subsection_id,
                            "mastery_node": sub.frontmatter.get("mastery_node"),
                            "stage_relevant": sub.frontmatter.get("stage_relevant"),
                        }
                    elif marker in EDGE_MARKERS:
                        edges.append({
                            "source": sub.subsection_id,
                            "target": name,
                            "type": EDGE_MARKERS[marker],
                        })

    # Orphan edges: target не существует в nodes
    orphans = [e for e in edges if e["target"] not in nodes]

    graph = {
        "schema_version": 1,
        "generated_by": "v4-lint graph build",
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "orphan_edges": len(orphans),
        },
    }

    out_json = Path(args.out_json) if args.out_json else None
    out_dot = Path(args.out_dot) if args.out_dot else None

    stdout_holds_json = out_json is None
    if out_json:
        out_json.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[graph build] JSON → {out_json}  (nodes={len(nodes)}, edges={len(edges)})",
              file=sys.stderr)
    else:
        # JSON в stdout — findings уходят в stderr, чтобы не ломать pipe-потребителей.
        print(json.dumps(graph, ensure_ascii=False, indent=2))

    if out_dot:
        out_dot.write_text(_render_dot(graph), encoding="utf-8")
        print(f"[graph build] DOT  → {out_dot}", file=sys.stderr)

    return report(findings, label="graph build", findings_to_stderr=stdout_holds_json)


def _render_dot(graph: dict) -> str:
    """Минимальный Graphviz DOT-рендер: цвет узла = guide, стиль ребра = type."""
    lines = ["digraph concept_graph {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    guide_colors = {1: "lightblue", 2: "lightgreen", 3: "khaki", 4: "salmon"}
    for node in graph["nodes"]:
        name = node["name"].replace('"', '\\"')
        guide = node.get("guide")
        color = guide_colors.get(guide, "white")
        label_parts = [name]
        if node.get("parent"):
            label_parts.append(node["parent"])
        if node.get("pack_source"):
            label_parts.append(node["pack_source"])
        label = "\\n".join(label_parts).replace('"', '\\"')
        lines.append(f'  "{name}" [label="{label}", fillcolor="{color}", style=filled];')
    edge_style = {"uses": "solid", "contrast": "dashed", "see-also": "dotted"}
    for edge in graph["edges"]:
        src = edge["source"]
        tgt = edge["target"].replace('"', '\\"')
        style = edge_style.get(edge["type"], "solid")
        lines.append(f'  "{src}" -> "{tgt}" [style={style}, label="{edge["type"]}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def cmd_graph_diff(args: argparse.Namespace) -> int:
    """Сравнить два JSON-снимка графа: добавленные/удалённые узлы и рёбра, изменения атрибутов."""
    import json

    before = Path(args.before)
    after = Path(args.after)
    findings: list[Finding] = []
    if not before.exists():
        findings.append(Finding("error", before, None, "файл не существует"))
    if not after.exists():
        findings.append(Finding("error", after, None, "файл не существует"))
    if findings:
        return report(findings, label="graph diff")

    g_before = json.loads(before.read_text(encoding="utf-8"))
    g_after = json.loads(after.read_text(encoding="utf-8"))
    nodes_before = {n["name"]: n for n in g_before.get("nodes", [])}
    nodes_after = {n["name"]: n for n in g_after.get("nodes", [])}

    added_nodes = sorted(set(nodes_after) - set(nodes_before))
    removed_nodes = sorted(set(nodes_before) - set(nodes_after))
    changed_nodes: list[tuple[str, str, str, str]] = []
    for name in sorted(set(nodes_before) & set(nodes_after)):
        b = nodes_before[name]
        a = nodes_after[name]
        for field_name in ("parent", "pack_source", "subsection_id"):
            if b.get(field_name) != a.get(field_name):
                changed_nodes.append((name, field_name, str(b.get(field_name)), str(a.get(field_name))))

    # Рёбра: уникальный ключ = (source, target, type).
    def _edge_key(e: dict) -> tuple[str, str, str]:
        return (e.get("source", ""), e.get("target", ""), e.get("type", ""))

    edges_before = {_edge_key(e) for e in g_before.get("edges", [])}
    edges_after = {_edge_key(e) for e in g_after.get("edges", [])}
    added_edges = sorted(edges_after - edges_before)
    removed_edges = sorted(edges_before - edges_after)

    print(f"=== graph diff: {before} → {after} ===")
    print(f"Добавлено узлов: {len(added_nodes)}")
    for n in added_nodes:
        print(f"  + {n}")
    print(f"Удалено узлов: {len(removed_nodes)}")
    for n in removed_nodes:
        print(f"  - {n}")
    print(f"Изменено узлов: {len(changed_nodes)}")
    for name, field_name, old, new in changed_nodes:
        print(f"  ~ {name}: {field_name} «{old}» → «{new}»")
    print(f"Добавлено рёбер: {len(added_edges)}")
    for src, tgt, etype in added_edges:
        print(f"  + {src} --{etype}--> {tgt}")
    print(f"Удалено рёбер: {len(removed_edges)}")
    for src, tgt, etype in removed_edges:
        print(f"  - {src} --{etype}--> {tgt}")

    # exit 0 если diff пустой, 1 если есть изменения (полезно для CI «нет дрейфа?»)
    if added_nodes or removed_nodes or changed_nodes or added_edges or removed_edges:
        return 1
    return 0


# ============================================================================
# Отчёт
# ============================================================================

def report(findings: list[Finding], label: str, findings_to_stderr: bool = False) -> int:
    """Печать findings + summary, возврат exit-кода.

    findings_to_stderr=True: findings уходят в stderr (когда stdout занят данными,
    например JSON-снимком графа). По умолчанию — stdout.
    """
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    out_stream = sys.stderr if findings_to_stderr else sys.stdout
    for f in findings:
        print(f.fmt(), file=out_stream)
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

    p_graph = sub.add_parser("graph", help="Концепт-граф из specs/v4-reference/ (build/diff)")
    graph_sub = p_graph.add_subparsers(dest="graph_cmd", required=True)

    p_graph_build = graph_sub.add_parser("build", help="Собрать граф (узлы + рёбра)")
    p_graph_build.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_graph_build.add_argument("--out-json", help="Записать JSON-снимок графа (иначе — stdout)")
    p_graph_build.add_argument("--out-dot", help="Записать Graphviz DOT для визуализации")
    p_graph_build.set_defaults(func=cmd_graph, graph_func=cmd_graph_build)

    p_graph_diff = graph_sub.add_parser("diff", help="Сравнить два JSON-снимка графа")
    p_graph_diff.add_argument("before", help="Старый JSON-снимок")
    p_graph_diff.add_argument("after", help="Новый JSON-снимок")
    p_graph_diff.set_defaults(func=cmd_graph, graph_func=cmd_graph_diff)

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
