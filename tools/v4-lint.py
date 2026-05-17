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
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

VALID_MASTERY_NODES = {"мыслительное", "саморазвитие", "iwe"}
VALID_STAGES = {1, 2, 3, 4, 5}
CONCEPT_MARKERS = {
    "вводится", "используется", "противопоставлен", "сослан",
    "кейс в тексте", "аналогия в тексте",
}

# STRUCT-PARSIMONY (legacy code-side A.11) Ontological Parsimony: предел «вводится» на подраздел (FPF A.11, WRITING-PIPELINE §«Распределение понятий»).
# NB: CHECKLIST-subsection A.11 — другое правило (формат `prerequisites`). Code-side переименовано в STRUCT-PARSIMONY для устранения коллизии (Ф0.8, 17 мая).
STRUCT_PARSIMONY_INTRODUCES_LIMIT = 3
A11_INTRODUCES_LIMIT = STRUCT_PARSIMONY_INTRODUCES_LIMIT  # backwards-compat alias, удалить после миграции внешних потребителей

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
    """Распарсенный подраздел из structure-guide-N.md ИЛИ одиночного SS-файла."""
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
    from_single_ss: bool = False  # True если распарсен через parse_single_subsection (content-файл в aisystant/docs)


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


def parse_single_subsection(path: Path) -> tuple[Subsection | None, list[Finding]]:
    """Распарсить одиночный SS-файл (например, content в aisystant/docs).

    В отличие от parse_structure_file, здесь frontmatter находится в начале файла
    (между `---` маркерами), а сам файл = подраздел (без структуры разделов).

    Используется cmd_porter для проверки одиночного SS (CHECKLIST-режим
    `v4-lint.py porter <ss-file.md>`).
    """
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, [Finding("error", path, None, f"не могу прочитать файл: {e}")]

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, [Finding(
            "error", path, 1,
            f"одиночный SS-файл должен начинаться с frontmatter `---`",
        )]

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, [Finding(
            "error", path, 1,
            "frontmatter не закрыт (нет второго `---`)",
        )]

    yaml_text = "\n".join(lines[1:end_idx])
    frontmatter = parse_yaml_block(yaml_text)

    subsection_id = frontmatter.get("subsection_id", "")
    guide_num = 0
    section_num = 0
    order = 0
    m = SUBSECTION_ID_RE.search(subsection_id)
    if m:
        guide_num = int(m.group(1))
        section_num = int(m.group(2))
        order = int(m.group(3))

    sub = Subsection(
        file=path,
        guide=guide_num,
        section=section_num,
        order=order,
        subsection_id=subsection_id,
        title=frontmatter.get("title", ""),
        frontmatter=frontmatter,
        line_start=1,
        from_single_ss=True,
    )
    return sub, findings


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
    """STRUCT-PARSIMONY (legacy code A.11): ≤STRUCT_PARSIMONY_INTRODUCES_LIMIT понятий «вводится» на подраздел.

    NB: CHECKLIST-subsection A.11 — другое правило (формат `prerequisites`). Не путать.
    """
    for sec in sections:
        for sub in sec.subsections:
            intro_count = sum(1 for c in sub.concepts if c.get("marker") == "вводится")
            if intro_count > STRUCT_PARSIMONY_INTRODUCES_LIMIT:
                names = [c.get("name", "?") for c in sub.concepts if c.get("marker") == "вводится"]
                findings.append(Finding(
                    "warning", sub.file, sub.line_start,
                    f"{sub.subsection_id}: вводится {intro_count} понятий (предел STRUCT-PARSIMONY = "
                    f"{STRUCT_PARSIMONY_INTRODUCES_LIMIT}). Список: {names}. Раздели на несколько подразделов "
                    f"или пометь часть как `используется`.",
                ))


def check_evidence_graph(sections: list[Section], findings: list[Finding]) -> None:
    """STRUCT-EVIDENCE (legacy code A.10): каждое «вводится» должно иметь источник Pack (PD.FORM/METHOD/CAT.NNN).

    NB: CHECKLIST-subsection A.10 — другое правило (шифры Pack в frontmatter `introduces`). Не путать.

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
                        f"(ожидается `(PD.FORM.NNN)` или `(PD.METHOD.NNN)` в строке) — STRUCT-EVIDENCE.",
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
    """Этап 8: проверка frontmatter подразделов.

    Поддерживает два режима:
      1. Structure-mode: путь — директория или файл `*structure-guide-*.md`.
         Парсятся все подразделы внутри structure-guide → cross-check prereq.
      2. Single-SS-mode: путь — одиночный SS-файл (например, content в aisystant/docs).
         Файл начинается с frontmatter `---`. Cross-check prereq не делается
         (нет реестра known_ids в одном файле).
    """
    targets = [Path(p) for p in args.paths]

    structure_targets: list[Path] = []
    single_ss_files: list[Path] = []
    findings: list[Finding] = []

    for t in targets:
        if not t.exists():
            findings.append(Finding("error", t, None, f"путь не существует: {t}"))
            continue
        if t.is_dir():
            structure_targets.append(t)
        elif t.is_file():
            if re.search(r"0?\d?-?structure-guide-", t.name):
                structure_targets.append(t)
            else:
                single_ss_files.append(t)

    known_ids: set[str] = set()
    all_subs: list[Subsection] = []

    if structure_targets:
        files, collect_findings = collect_structure_files(structure_targets)
        findings.extend(collect_findings)
        for f in files:
            sections, parse_findings = parse_structure_file(f)
            findings.extend(parse_findings)
            for sec in sections:
                for sub in sec.subsections:
                    if sub.subsection_id:
                        known_ids.add(sub.subsection_id)
                    all_subs.append(sub)

    for ss_path in single_ss_files:
        sub, parse_findings = parse_single_subsection(ss_path)
        findings.extend(parse_findings)
        if sub is not None:
            if sub.subsection_id:
                known_ids.add(sub.subsection_id)
            all_subs.append(sub)

    if not all_subs and not findings:
        findings.append(Finding("error", Path("."), None, "не найдено ни одного файла для проверки"))
        return report(findings, label="porter")

    for sub in all_subs:
        check_porter_frontmatter(sub, known_ids, findings)

    return report(findings, label="porter")


def check_porter_frontmatter(sub: Subsection, known_ids: set[str], findings: list[Finding]) -> None:
    fm = sub.frontmatter

    # Auxiliary detection (нужно знать ДО PORTER_REQUIRED_FIELDS check — у aux другие требования).
    # Защищаемся от хрупкого endswith: точный regex по концу subsection_id.
    fmt_ver = fm.get("format_version")
    if isinstance(fmt_ver, str):
        fmt_ver_str = fmt_ver.strip().lower()
        # null/false как явное «нет значения» → трактуем как отсутствие.
        if fmt_ver_str in ("", "null", "none", "false"):
            fmt_ver = None
        else:
            fmt_ver = fmt_ver.strip()
    aux_id_re = re.compile(r"\.SS(0?8|0?9|10|11)$")
    is_aux = fmt_ver == "4.1-aux" or (sub.subsection_id and aux_id_re.search(sub.subsection_id) is not None)

    # PORTER_REQUIRED_FIELDS — обязательны для main-подразделов. Auxiliary освобождены от cp_check/bh_check.
    for field_name in PORTER_REQUIRED_FIELDS:
        if field_name in ("cp_check", "bh_check") and is_aux:
            continue
        if field_name not in fm or fm[field_name] in (None, "", []):
            findings.append(Finding(
                "error", sub.file, sub.line_start,
                f"{sub.subsection_id or '<no-id>'}: отсутствует обязательное поле `{field_name}`",
            ))

    # B.9 — отсутствие format_version.
    # CHECKLIST v1.1 §B.9: «FAIL если отсутствует в main; WARN в auxiliary».
    # Архитектурное различение: B.9 как FAIL применяется ТОЛЬКО к одиночным SS-файлам (content в aisystant/docs).
    # В structure-guide-N.md frontmatter подразделов — упрощённый онтологический контракт без content-полей;
    # отсутствие format_version там — WARN (миграция корпуса = отдельный РП Ф0.9).
    b9_severity_missing = "error" if (sub.from_single_ss and not is_aux) else "warning"
    if not fmt_ver:
        findings.append(Finding(
            b9_severity_missing,
            sub.file, sub.line_start,
            f"{sub.subsection_id or '<no-id>'}: отсутствует `format_version` (B.9). "
            f"Добавь `format_version: 4.1` (main) или `4.1-aux` (auxiliary).",
        ))
    elif fmt_ver not in ("4.1", "4.1-aux"):
        findings.append(Finding(
            "warning", sub.file, sub.line_start,
            f"{sub.subsection_id or '<no-id>'}: неизвестный `format_version`: «{fmt_ver}». "
            f"Ожидается 4.1 или 4.1-aux.",
        ))

    # B.9 — остальные 5 mandatory meta-полей (только для single-SS-mode, main подразделы).
    # В structure-guide-N.md этих полей нет по дизайну (skeleton без content-метаданных).
    if sub.from_single_ss and not is_aux:
        for meta_field in ("time_reading", "time_practice", "word_count_target", "status", "wp"):
            value = fm.get(meta_field)
            if value is None or value == "" or value == []:
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id or '<no-id>'}: отсутствует обязательное meta-поле `{meta_field}` (B.9).",
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

    if not is_aux:
        can_do = fm.get("can_do")
        if can_do:
            items = can_do if isinstance(can_do, list) else [can_do]
            for item in items:
                if isinstance(item, str) and not item.lstrip().lower().startswith("могу"):
                    findings.append(Finding(
                        "warning", sub.file, sub.line_start,
                        f"{sub.subsection_id}: can_do элемент не начинается с «Могу»: «{item[:60]}»",
                    ))

        introduces_raw = fm.get("introduces", [])
        # Нормализация bare-scalar → list: автор мог написать `introduces: PD.FORM.089`
        # вместо `introduces: [PD.FORM.089]`. Без нормализации обе ветки A.10 пропускаются (false-green).
        introduces = introduces_raw if isinstance(introduces_raw, list) else (
            [introduces_raw] if introduces_raw not in (None, "") else []
        )
        for name in introduces:
            if not isinstance(name, str):
                continue
            if name.startswith("U."):
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: в `introduces` указан U.*-тип «{name}» — должно быть каноническое имя",
                ))
            # A.10 (CHECKLIST-side): шифры Pack в frontmatter `introduces` запрещены.
            # introduces должен содержать только канонические имена понятий, не Pack-источники.
            # IGNORECASE покрывает typos: `pd.form.089`, `Pd.Method.001`.
            if re.search(r"\bPD\.(?:FORM|METHOD|CAT)\.\d+", name, re.IGNORECASE):
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: в `introduces` запрещены шифры Pack «{name}» "
                    f"(PD.FORM/METHOD/CAT.NNN) — это источник, не имя понятия (A.10).",
                ))
            # RCS-индексы (cp.* / bh.*) — широкий regex: латинские буквы (любой кейс),
            # цифры, подчёркивание после `cp.` / `bh.`.
            if re.search(r"\b(?:cp|bh)\.[A-Za-z][A-Za-z0-9_]*", name, re.IGNORECASE):
                findings.append(Finding(
                    "error", sub.file, sub.line_start,
                    f"{sub.subsection_id}: в `introduces` запрещены RCS-индексы «{name}» "
                    f"(cp.* / bh.*) — это слот, не имя понятия (A.10).",
                ))

    # A.11 (CHECKLIST-side): формат `prerequisites` — только PD.GUIDE.N.SX.SSY, не §X.YY.
    # Нормализация bare-scalar → list (защита от false-green как в A.10).
    prereqs_raw = fm.get("prerequisites", [])
    prereqs = prereqs_raw if isinstance(prereqs_raw, list) else (
        [prereqs_raw] if prereqs_raw not in (None, "") else []
    )
    for ref in prereqs:
        if not isinstance(ref, str):
            continue
        # `§` в любом месте строки — индикатор legacy-формата (включая `см. §1.05`).
        if "§" in ref:
            findings.append(Finding(
                "error", sub.file, sub.line_start,
                f"{sub.subsection_id}: prerequisite «{ref}» содержит legacy-маркер `§` — "
                f"требуется чистый ID `PD.GUIDE.N.SX.SSY` (A.11).",
            ))
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

    scope = getattr(args, "scope", None)
    scope_id = getattr(args, "id", None)

    introduces_map: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    all_known_ids: set[str] = set()
    uses_list: list[tuple[str, Path, str]] = []  # (name, file, subsection_id)

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        sections, scope_err = apply_scope_to_sections(sections, scope, scope_id)
        if scope_err:
            findings.append(scope_err)
            return report(findings, label="cross-guide")
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

    scope = getattr(args, "scope", None)
    scope_id = getattr(args, "id", None)

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        sections, scope_err = apply_scope_to_sections(sections, scope, scope_id)
        if scope_err:
            findings.append(scope_err)
            return report(findings, label="pack-drift")
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

    scope = getattr(args, "scope", None)
    scope_id = getattr(args, "id", None)

    nodes: dict[str, dict] = {}  # name → {parent, pack_source, guide, subsection_id, mastery_node, stage_relevant}
    edges: list[dict] = []        # {source: subsection_id, target: concept_name, type: uses/contrast/see-also}

    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        sections, scope_err = apply_scope_to_sections(sections, scope, scope_id)
        if scope_err:
            findings.append(scope_err)
            return report(findings, label="graph build", findings_to_stderr=True)
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
# Subcommand: section / guide / prerequisites-graph (WP-322 Ф3.8, 17 мая)
# ============================================================================
#
# Эталоны: specs/v4-reference/CHECKLIST-section-v1.md §🔴 (A-C),
#          specs/v4-reference/CHECKLIST-guide-v1.md §🔴 (A-D).
#
# Принцип: section/guide читают тот же structure-guide-N.md, что и cross-guide,
# но проверяют разные инварианты. section фильтрует один S; guide агрегирует
# проверки по всем S одного руководства.

SECTION_ID_RE = re.compile(r"^PD\.GUIDE\.(\d+)\.S(\d+)$")
GUIDE_ID_RE = re.compile(r"^PD\.GUIDE\.(\d+)$")
SUBSECTION_FULL_ID_RE = re.compile(r"^PD\.GUIDE\.(\d+)\.S(\d+)\.SS(\d+)$")


def parse_section_id(section_id: str) -> tuple[int, int] | None:
    """`PD.GUIDE.<N>.S<X>` → (guide, section). None если формат неверный."""
    if not section_id:
        return None
    m = SECTION_ID_RE.match(section_id.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_guide_id_arg(guide_id: str) -> int | None:
    """`PD.GUIDE.<N>` или голое `N` (1-4) → N. None если формат неверный или N вне 1-4.

    Subagent-review FIX (H1): валидируем диапазон 1-4 единообразно для обоих форматов,
    чтобы избежать inconsistency «5 → None, PD.GUIDE.5 → 5».
    """
    if not guide_id:
        return None
    g = guide_id.strip()
    m = GUIDE_ID_RE.match(g)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 4 else None
    if g.isdigit():
        n = int(g)
        return n if 1 <= n <= 4 else None
    return None


def apply_scope_to_sections(
    sections: list[Section],
    scope: str | None,
    scope_id: str | None,
) -> tuple[list[Section], Finding | None]:
    """Помощник для cmd_cross_guide / cmd_pack_drift / cmd_graph_build (WP-322 Ф3.8).

    Возвращает (filtered, error_finding|None).
    scope=None → возврат без изменений, без ошибки.
    Если scope валиден, но id нет/невалиден → пустой список + Finding(error).
    """
    if scope is None:
        return sections, None

    if scope == "guide":
        g = parse_guide_id_arg(scope_id) if scope_id else None
        if g is None:
            return [], Finding(
                "error", Path("."), None,
                f"--scope guide требует --id PD.GUIDE.<N> или N (1-4), получено: «{scope_id}»",
            )
        return [s for s in sections if s.guide == g], None

    if scope == "section":
        parsed = parse_section_id(scope_id) if scope_id else None
        if parsed is None:
            return [], Finding(
                "error", Path("."), None,
                f"--scope section требует --id PD.GUIDE.<N>.S<X>, получено: «{scope_id}»",
            )
        g, sn = parsed
        return [s for s in sections if s.guide == g and s.section == sn], None

    return [], Finding(
        "error", Path("."), None,
        f"неизвестный --scope: «{scope}» (допустимо: guide, section)",
    )


def filter_sections_by_scope(
    sections_per_file: list[tuple[Path, list[Section]]],
    scope: str | None,
    scope_id: str | None,
) -> tuple[list[tuple[Path, list[Section]]], list[Finding]]:
    """Фильтровать разделы по `--scope` + `--id`.

    scope=None → без изменений.
    scope='guide' + id='PD.GUIDE.<N>' или 'N' → только разделы guide N.
    scope='section' + id='PD.GUIDE.<N>.S<X>' → только S X из guide N.

    Возвращает: (отфильтрованные данные, findings об ошибках формата id).
    """
    if scope is None:
        return sections_per_file, []

    findings: list[Finding] = []
    if scope == "guide":
        g = parse_guide_id_arg(scope_id) if scope_id else None
        if g is None:
            findings.append(Finding(
                "error", Path("."), None,
                f"--scope guide требует --id PD.GUIDE.<N> или N (1-4), получено: `{scope_id}`",
            ))
            return [], findings
        filtered = [(p, [s for s in secs if s.guide == g]) for p, secs in sections_per_file]
        return filtered, findings

    if scope == "section":
        parsed = parse_section_id(scope_id) if scope_id else None
        if parsed is None:
            findings.append(Finding(
                "error", Path("."), None,
                f"--scope section требует --id PD.GUIDE.<N>.S<X>, получено: `{scope_id}`",
            ))
            return [], findings
        g, s = parsed
        filtered = [(p, [sec for sec in secs if sec.guide == g and sec.section == s])
                    for p, secs in sections_per_file]
        return filtered, findings

    findings.append(Finding(
        "error", Path("."), None,
        f"неизвестный --scope: `{scope}` (допустимо: guide, section)",
    ))
    return [], findings


# ----------------------------------------------------------------------------
# Section checks (CHECKLIST-section-v1.md §🔴 A-C)
# ----------------------------------------------------------------------------

REQUIRED_SECTION_FRONTMATTER = ("section_id", "title", "parent_guide_id", "stage_focus", "mastery_node")


def check_section_ss_completeness(file: Path, section: Section, findings: list[Finding]) -> None:
    """A.1 — SS-номера непрерывны в разделе (нет пропусков)."""
    if not section.subsections:
        findings.append(Finding("error", file, None,
                                f"S{section.section}: нет подразделов (по structure-guide)"))
        return
    nums = sorted(sub.order for sub in section.subsections)
    expected = list(range(1, max(nums) + 1))
    missing = sorted(set(expected) - set(nums))
    if missing:
        findings.append(Finding(
            "error", file, None,
            f"S{section.section}: пропущены SS: {missing} (присутствуют SS{nums})",
        ))


def check_section_frontmatter(file: Path, section: Section, findings: list[Finding]) -> None:
    """A.2 — Frontmatter раздела содержит обязательные поля."""
    fm = section.frontmatter or {}
    for field_name in REQUIRED_SECTION_FRONTMATTER:
        if field_name not in fm:
            findings.append(Finding(
                "error", file, None,
                f"S{section.section}: frontmatter раздела не содержит `{field_name}` (A.2)",
            ))


def check_section_ss_parent_alignment(file: Path, section: Section, findings: list[Finding]) -> None:
    """A.3 — Каждый SS имеет parent_section_id, совпадающий с этим S.

    Subagent-review FIX (Б3): отсутствие parent_section_id — это нарушение A.3 (FAIL),
    а не silent pass. Чек-лист требует наличия поля.

    Subagent-review FIX (H2): не используем fallback от section.guide/section если
    section_id отсутствует в frontmatter раздела — A.2 уже отрапортовал это.
    """
    section_id_canonical = (section.frontmatter or {}).get("section_id")
    if not section_id_canonical:
        # A.2 уже репортит отсутствие section_id; не делаем A.3 на fallback-форме
        # чтобы не маскировать root-cause typo в section_id раздела.
        return

    for sub in section.subsections:
        parent = (sub.frontmatter or {}).get("parent_section_id")
        if not parent:
            findings.append(Finding(
                "error", file, sub.line_start,
                f"{sub.subsection_id}: parent_section_id отсутствует во frontmatter (A.3)",
            ))
        elif parent != section_id_canonical:
            findings.append(Finding(
                "error", file, sub.line_start,
                f"{sub.subsection_id}: parent_section_id «{parent}» ≠ «{section_id_canonical}» (A.3)",
            ))


def _detect_prereq_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Итеративный DFS cycle detection. Возвращает список циклов.

    Subagent-review FIX (L1): переписано на стек вместо рекурсии для защиты от
    RecursionError при глубоких графах (>1000 SS). Для типичного гайда (≤70 SS)
    результат идентичен рекурсивной версии.

    Алгоритм: стандартный 3-цветный DFS, но цикл detection реализован через
    явный стек (node, child_iter). При обнаружении GRAY-вершины — извлекается
    цикл из path. Path хранится синхронно со стеком.
    """
    cycles: list[list[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in graph}

    for start in list(graph.keys()):
        if color.get(start, WHITE) != WHITE:
            continue
        # Стек содержит кортежи (node, iterator-of-neighbors).
        # path — текущий DFS-путь (для извлечения цикла).
        # Subagent-review FIX (N1): type-annotation использует Iterator[str], не any.
        stack: list[tuple[str, "Iterator[str]"]] = [(start, iter(graph.get(start, [])))]
        path: list[str] = [start]
        color[start] = GRAY

        while stack:
            node, nb_iter = stack[-1]
            advanced = False
            for nb in nb_iter:
                nb_color = color.get(nb, WHITE)
                if nb_color == GRAY:
                    # Цикл обнаружен — извлекаем из path.
                    if nb in path:
                        idx = path.index(nb)
                        cycles.append(path[idx:] + [nb])
                elif nb_color == WHITE:
                    color[nb] = GRAY
                    path.append(nb)
                    stack.append((nb, iter(graph.get(nb, []))))
                    advanced = True
                    break
            if not advanced:
                # Все соседи обработаны — backtrack.
                color[node] = BLACK
                stack.pop()
                path.pop()

    return cycles


def check_section_prerequisites_graph(
    file: Path, section: Section, findings: list[Finding],
    known_ids_all: set[str] | None = None,
) -> None:
    """B.1 B.2 B.3 — prerequisites внутри раздела разрешаются, без циклов, cross-section помечен.

    Subagent-review FIX (H5): если передан known_ids_all (набор subsection_id со ВСЕХ
    файлов структуры), cross-section prereq дополнительно валидируется: ссылка на
    несуществующий S99.SS1 ловится как FAIL. Без known_ids_all cross-section prereq
    только проверяется на корректный формат (B.3).
    """
    own_ids = {sub.subsection_id for sub in section.subsections if sub.subsection_id}
    order_map = {sub.subsection_id: sub.order for sub in section.subsections if sub.subsection_id}
    graph: dict[str, list[str]] = {sid: [] for sid in own_ids}

    same_section_pattern = re.compile(
        rf"^PD\.GUIDE\.{section.guide}\.S{section.section}\.SS(\d+)$"
    )

    for sub in section.subsections:
        # Subagent-review FIX (Б1): SS без subsection_id отрапортовать отдельно — иначе KeyError в graph.append.
        # NB: prereqs такого SS пропускаются намеренно (B.1/B.2/B.3 не запускаются для него) —
        # до устранения FAIL «нет subsection_id» проверки prereq ненадёжны, поскольку нечего привязывать.
        if not sub.subsection_id:
            findings.append(Finding(
                "error", file, sub.line_start,
                f"S{section.section} SS#{sub.order}: subsection_id отсутствует во frontmatter (B.1 предусловие)",
            ))
            continue
        prereqs = (sub.frontmatter or {}).get("prerequisites", [])
        if not isinstance(prereqs, list):
            prereqs = [prereqs]
        for p in prereqs:
            if not isinstance(p, str):
                continue
            p_clean = p.strip()
            if not p_clean:
                continue

            # B.3: формат должен быть PD.GUIDE.N.SX.SSY (любая секция).
            if not SUBSECTION_FULL_ID_RE.match(p_clean):
                findings.append(Finding(
                    "error", file, sub.line_start,
                    f"{sub.subsection_id}: prereq «{p_clean}» нерезолвится — "
                    f"должен быть PD.GUIDE.N.SX.SSY (B.3)",
                ))
                continue

            if same_section_pattern.match(p_clean):
                # Внутрисекционный prereq — B.1 (существование) + B.2 (порядок).
                if p_clean not in own_ids:
                    findings.append(Finding(
                        "error", file, sub.line_start,
                        f"{sub.subsection_id}: prereq «{p_clean}» не существует в S{section.section} (B.1)",
                    ))
                else:
                    if order_map.get(p_clean, 10_000) >= sub.order:
                        findings.append(Finding(
                            "error", file, sub.line_start,
                            f"{sub.subsection_id}: prereq «{p_clean}» идёт ПОСЛЕ "
                            f"(order {order_map[p_clean]} ≥ {sub.order}, B.1)",
                        ))
                    graph[sub.subsection_id].append(p_clean)
            else:
                # Cross-section prereq — формат PD.GUIDE.N.SX.SSY уже соблюдён.
                # Subagent-review FIX (H5): если есть known_ids_all — проверить разрешимость.
                if known_ids_all is not None and p_clean not in known_ids_all:
                    findings.append(Finding(
                        "error", file, sub.line_start,
                        f"{sub.subsection_id}: cross-section prereq «{p_clean}» "
                        f"не разрешается ни в одном structure-guide-N.md (B.3)",
                    ))

    # B.2 — циклы в локальном графе.
    cycles = _detect_prereq_cycles(graph)
    for cycle in cycles:
        findings.append(Finding(
            "error", file, None,
            f"S{section.section}: цикл prerequisites: {' → '.join(cycle)} (B.2)",
        ))


def check_section_introduce_before_use(file: Path, section: Section, findings: list[Finding]) -> None:
    """C.1 — внутри раздела introduces идёт ДО uses (порядок чтения)."""
    first_introduction: dict[str, int] = {}
    for sub in section.subsections:
        for concept in sub.concepts:
            name = (concept.get("name") or "").strip()
            if concept.get("marker") == "вводится" and name and name not in first_introduction:
                first_introduction[name] = sub.order

    for sub in section.subsections:
        for concept in sub.concepts:
            name = (concept.get("name") or "").strip()
            if concept.get("marker") == "используется" and name in first_introduction:
                if first_introduction[name] > sub.order:
                    findings.append(Finding(
                        "error", file, sub.line_start,
                        f"{sub.subsection_id}: «{name}» используется ДО введения "
                        f"(вводится в SS{first_introduction[name]}, C.1)",
                    ))


def check_section_mastery_node_consistency(file: Path, section: Section, findings: list[Finding]) -> None:
    """C.2 — узел мастерства консистентен между разделом и его SS."""
    section_node = (section.frontmatter or {}).get("mastery_node")
    if not section_node:
        return  # A.2 уже отрапортовал
    section_set = set(section_node) if isinstance(section_node, list) else {section_node}

    for sub in section.subsections:
        sub_node = (sub.frontmatter or {}).get("mastery_node")
        if not sub_node:
            continue
        sub_set = set(sub_node) if isinstance(sub_node, list) else {sub_node}
        if not (sub_set & section_set):
            findings.append(Finding(
                "error", file, sub.line_start,
                f"{sub.subsection_id}: mastery_node {sorted(sub_set)} не пересекается "
                f"с S{section.section} mastery_node {sorted(section_set)} (C.2)",
            ))


def cmd_section(args: argparse.Namespace) -> int:
    """Этап section: проверки CHECKLIST-section-v1.md §🔴 A-C."""
    parsed = parse_section_id(args.id)
    if parsed is None:
        return report(
            [Finding("error", Path("."), None,
                     f"--id должен быть формата PD.GUIDE.<N>.S<X>, получено: «{args.id}»")],
            label="section",
        )
    target_guide, target_section = parsed

    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="section")

    matched_section: Section | None = None
    structure_file: Path | None = None
    # Subagent-review FIX (H5): собрать known_ids_all со ВСЕХ файлов для
    # валидации cross-section prereq.
    known_ids_all: set[str] = set()
    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        for sec in sections:
            for sub in sec.subsections:
                if sub.subsection_id:
                    known_ids_all.add(sub.subsection_id)
            if sec.guide == target_guide and sec.section == target_section:
                matched_section = sec
                structure_file = f

    if matched_section is None or structure_file is None:
        findings.append(Finding(
            "error", Path("."), None,
            f"раздел PD.GUIDE.{target_guide}.S{target_section} не найден в "
            f"{[f.name for f in files]}",
        ))
        return report(findings, label="section")

    check_section_ss_completeness(structure_file, matched_section, findings)
    check_section_frontmatter(structure_file, matched_section, findings)
    check_section_ss_parent_alignment(structure_file, matched_section, findings)
    check_section_prerequisites_graph(structure_file, matched_section, findings, known_ids_all)
    check_section_introduce_before_use(structure_file, matched_section, findings)
    check_section_mastery_node_consistency(structure_file, matched_section, findings)

    return report(findings, label=f"section PD.GUIDE.{target_guide}.S{target_section}")


# ----------------------------------------------------------------------------
# Guide checks (CHECKLIST-guide-v1.md §🔴 A-D)
# ----------------------------------------------------------------------------

REQUIRED_GUIDE_FRONTMATTER = ("guide_id", "title", "object", "axis", "stages")


def check_guide_section_completeness(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """A.1 — все S присутствуют (S1..SN без пропусков)."""
    if not guide_sections:
        findings.append(Finding("error", file, None,
                                f"PD.GUIDE.{guide_num}: нет разделов в structure"))
        return
    nums = sorted(s.section for s in guide_sections)
    expected = list(range(1, max(nums) + 1))
    missing = sorted(set(expected) - set(nums))
    if missing:
        findings.append(Finding(
            "error", file, None,
            f"PD.GUIDE.{guide_num}: пропущены S: {missing} (присутствуют S{nums}) (A.1)",
        ))


def check_guide_bounded_context(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """B.2 — Bounded Context: руководства 1-2 не должны содержать SS с mastery_node=iwe."""
    if guide_num not in GUIDES_FORBID_IWE:
        return
    for sec in guide_sections:
        for sub in sec.subsections:
            sub_node = (sub.frontmatter or {}).get("mastery_node")
            if not sub_node:
                continue
            sub_set = set(sub_node) if isinstance(sub_node, list) else {sub_node}
            if "iwe" in sub_set:
                findings.append(Finding(
                    "error", file, sub.line_start,
                    f"{sub.subsection_id}: mastery_node содержит «iwe», "
                    f"но Guide {guide_num} не должен вводить iwe-узел (B.2, A.1.1)",
                ))


def check_guide_cross_consistency(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """B.1 — понятия не дублируются внутри руководства (один источник `вводится`)."""
    introduces_map: dict[str, list[str]] = defaultdict(list)
    for sec in guide_sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                name = (concept.get("name") or "").strip()
                marker = concept.get("marker")
                if marker == "вводится" and name:
                    introduces_map[name].append(sub.subsection_id)

    for name, locations in introduces_map.items():
        if len(locations) > 1:
            findings.append(Finding(
                "error", file, None,
                f"Guide {guide_num}: понятие «{name}» вводится {len(locations)}× в "
                f"[{', '.join(locations)}] — должно быть одно определение (B.1)",
            ))


def check_guide_orphan_uses(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """B.3 — каждое `используется` ссылается на `вводится` (в этом или другом гайде).
    Здесь проверяем только внутри гайда; cross-guide ссылки проверяет cmd_cross_guide.
    """
    introduces_local: set[str] = set()
    uses_list: list[tuple[str, str]] = []  # (name, subsection_id)
    for sec in guide_sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                name = (concept.get("name") or "").strip()
                marker = concept.get("marker")
                if marker == "вводится" and name:
                    introduces_local.add(name)
                elif marker == "используется" and name:
                    uses_list.append((name, sub.subsection_id))

    for name, sub_id in uses_list:
        if name not in introduces_local:
            # WARN: может быть введено в другом гайде. cross-guide подтвердит.
            findings.append(Finding(
                "warning", file, None,
                f"Guide {guide_num}: {sub_id}: «{name}» помечено `используется`, "
                f"но в этом гайде не вводится (B.3 — проверь cross-guide)",
            ))


def check_guide_pack_mapping(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """B.4 — каждое `вводится` имеет ссылку на Pack (PD.FORM/METHOD/CAT.NNN).

    Subagent-review FIX (Б2): использовать concept["pack_source"], а не concept["ref"].
    `ref` — это cross-subsection ссылка (X.SY.SSZ), `pack_source` — это PD.FORM/METHOD/CAT.NNN
    (см. parse_concepts_block:189-191).
    """
    for sec in guide_sections:
        for sub in sec.subsections:
            for concept in sub.concepts:
                name = (concept.get("name") or "").strip()
                marker = concept.get("marker")
                if marker != "вводится" or not name:
                    continue
                pack_source = concept.get("pack_source")
                if not pack_source:
                    findings.append(Finding(
                        "warning", file, sub.line_start,
                        f"Guide {guide_num}: {sub.subsection_id}: «{name}» вводится "
                        f"без ссылки на Pack (PD.FORM/METHOD/CAT.NNN) (B.4)",
                    ))


def check_guide_prereq_acyclic_and_order(
    file: Path, guide_num: int, guide_sections: list[Section], findings: list[Finding],
) -> None:
    """C.1 + C.3 — ациклический граф prerequisites + порядок чтения."""
    sub_order_global: dict[str, tuple[int, int]] = {}  # subsection_id → (section, order)
    for sec in guide_sections:
        for sub in sec.subsections:
            if sub.subsection_id:
                sub_order_global[sub.subsection_id] = (sec.section, sub.order)

    graph: dict[str, list[str]] = {sid: [] for sid in sub_order_global}
    for sec in guide_sections:
        for sub in sec.subsections:
            prereqs = (sub.frontmatter or {}).get("prerequisites", [])
            if not isinstance(prereqs, list):
                prereqs = [prereqs]
            for p in prereqs:
                if not isinstance(p, str):
                    continue
                p_clean = p.strip()
                if not SUBSECTION_FULL_ID_RE.match(p_clean):
                    continue  # B.3 формат — отрапортован в check_section_*
                # C.3 — prereq должен быть ДО (по (section, order))
                if p_clean in sub_order_global:
                    pre_loc = sub_order_global[p_clean]
                    cur_loc = (sec.section, sub.order)
                    if pre_loc >= cur_loc:
                        findings.append(Finding(
                            "error", file, sub.line_start,
                            f"Guide {guide_num}: {sub.subsection_id}: prereq «{p_clean}» "
                            f"идёт ПОСЛЕ в порядке чтения (S{pre_loc[0]}.SS{pre_loc[1]} ≥ "
                            f"S{cur_loc[0]}.SS{cur_loc[1]}, C.3)",
                        ))
                    if sub.subsection_id:
                        graph[sub.subsection_id].append(p_clean)

    # C.1 — циклы
    cycles = _detect_prereq_cycles(graph)
    for cycle in cycles:
        findings.append(Finding(
            "error", file, None,
            f"Guide {guide_num}: цикл prerequisites: {' → '.join(cycle)} (C.1)",
        ))


def check_guide_readme_and_version(
    file: Path, guide_num: int, paths_arg: list[str], findings: list[Finding],
) -> None:
    """A.4 + A.5 — Subagent-review FIX (H3): filesystem-checks README.md + version.json.

    A.4 (README руководства): ищем `README-guide-<N>.md` или `README.md` в той же
    директории что и structure-guide-<N>.md. WARN если не найден (не блокирует).

    A.5 (version.json): ищем `version.json` или `version-guide-<N>.json` в той же
    директории. Проверяем что значение `version` соответствует semver v4.X.Y.
    WARN если не найден или формат неверен.

    Оба check'а — WARN, не блокирующие, потому что:
    - В v1.0 эти артефакты могут отсутствовать (Ф0 ещё не создал README на гайд)
    - Структура файловой иерархии не финализирована в чек-листе
    """
    import json as _json

    # Директория structure-guide файла
    parent_dir = file.parent

    # A.4 README — две конвенции имени
    readme_candidates = [
        parent_dir / f"README-guide-{guide_num}.md",
        parent_dir / "README.md",
    ]
    if not any(p.exists() for p in readme_candidates):
        findings.append(Finding(
            "warning", file, None,
            f"Guide {guide_num}: README не найден среди {[p.name for p in readme_candidates]} (A.4)",
        ))

    # A.5 version.json
    version_candidates = [
        parent_dir / f"version-guide-{guide_num}.json",
        parent_dir / "version.json",
    ]
    version_file = next((p for p in version_candidates if p.exists()), None)
    if version_file is None:
        findings.append(Finding(
            "warning", file, None,
            f"Guide {guide_num}: version.json не найден среди {[p.name for p in version_candidates]} (A.5)",
        ))
    else:
        try:
            version_data = _json.loads(version_file.read_text(encoding="utf-8"))
            version_str = version_data.get("version", "")
            if not re.match(r"^v?4\.\d+\.\d+$", version_str):
                findings.append(Finding(
                    "warning", version_file, None,
                    f"Guide {guide_num}: version={version_str!r} не соответствует semver v4.X.Y (A.5)",
                ))
        except (OSError, _json.JSONDecodeError) as e:
            findings.append(Finding(
                "warning", version_file, None,
                f"Guide {guide_num}: не удалось распарсить version.json: {e} (A.5)",
            ))


def cmd_guide(args: argparse.Namespace) -> int:
    """Этап guide: проверки CHECKLIST-guide-v1.md §🔴 A-D."""
    g = parse_guide_id_arg(args.id)
    if g is None:
        return report(
            [Finding("error", Path("."), None,
                     f"--id должен быть PD.GUIDE.<N> или N (1-4), получено: «{args.id}»")],
            label="guide",
        )

    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="guide")

    # Subagent-review FIX (H4): мульти-файловый shard — собираем разделы guide N
    # из ВСЕХ файлов, а не только первого. structure-guide может быть разбит на
    # patch-файлы (например, при peer-merge); первый match не должен быть единственным.
    structure_files_for_guide: list[Path] = []
    guide_sections: list[Section] = []
    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        secs_in_guide = [s for s in sections if s.guide == g]
        if secs_in_guide:
            structure_files_for_guide.append(f)
            guide_sections.extend(secs_in_guide)

    if not guide_sections:
        findings.append(Finding(
            "error", Path("."), None,
            f"PD.GUIDE.{g}: structure-guide-{g}.md не найден среди {[f.name for f in files]}",
        ))
        return report(findings, label="guide")

    # Используем первый файл как «representative» для error reporting,
    # но проверки оперируют объединённой коллекцией sections.
    structure_file = structure_files_for_guide[0]

    # A.1 — полнота разделов
    check_guide_section_completeness(structure_file, g, guide_sections, findings)
    # A.2 (delegated) — полнота SS в каждом разделе
    for sec in guide_sections:
        check_section_ss_completeness(structure_file, sec, findings)
    # A.4 / A.5 — Subagent-review FIX (H3): filesystem-checks README + version.json
    check_guide_readme_and_version(structure_file, g, args.paths, findings)
    # B.1 — кросс-руководная согласованность (внутри гайда)
    check_guide_cross_consistency(structure_file, g, guide_sections, findings)
    # B.2 — Bounded Context
    check_guide_bounded_context(structure_file, g, guide_sections, findings)
    # B.3 — orphan uses (warn)
    check_guide_orphan_uses(structure_file, g, guide_sections, findings)
    # B.4 — Pack-маппинг (warn)
    check_guide_pack_mapping(structure_file, g, guide_sections, findings)
    # C.1 + C.3 — ацикличность + порядок
    check_guide_prereq_acyclic_and_order(structure_file, g, guide_sections, findings)

    # D.1-D.3 — pack-drift (опционально, если передан --pack)
    if getattr(args, "pack", None):
        pack_path = Path(args.pack)
        if not pack_path.exists():
            findings.append(Finding("error", pack_path, None, f"Pack-файл не найден: {pack_path}"))
        else:
            pack_data = parse_pack_form089(pack_path)
            known_cp = pack_data["cp"]
            known_bh = pack_data["bh"]
            for sec in guide_sections:
                for sub in sec.subsections:
                    check_pack_drift_in_frontmatter(sub, known_cp, known_bh, findings)
                    check_pack_drift_in_text(sub, known_cp, known_bh, findings)

    return report(findings, label=f"guide PD.GUIDE.{g}")


# ----------------------------------------------------------------------------
# Prerequisites-graph (CHECKLIST-section-v1.md §🔴 B.1-B.3; standalone)
# ----------------------------------------------------------------------------

def cmd_prerequisites_graph(args: argparse.Namespace) -> int:
    """Отдельная проверка графа prerequisites. --scope section | guide + --id <id>.

    Делегирует логику в check_section_prerequisites_graph (section)
    или check_guide_prereq_acyclic_and_order (guide). Возвращает FAIL если есть error-finding.
    """
    if args.scope not in ("section", "guide"):
        return report(
            [Finding("error", Path("."), None,
                     f"--scope должен быть section или guide, получено: «{args.scope}»")],
            label="prerequisites-graph",
        )

    if args.scope == "section":
        # Делегируем cmd_section в режиме «только prereq-проверки».
        parsed = parse_section_id(args.id)
        if parsed is None:
            return report(
                [Finding("error", Path("."), None,
                         f"--scope section --id должен быть PD.GUIDE.<N>.S<X>, получено: «{args.id}»")],
                label="prerequisites-graph",
            )
        target_guide, target_section = parsed

        targets = [Path(p) for p in args.paths]
        files, findings = collect_structure_files(targets)
        if not files:
            return report(findings, label="prerequisites-graph")

        # Subagent-review FIX (H5): собрать known_ids_all для cross-section validation.
        known_ids_all: set[str] = set()
        target_section_obj: Section | None = None
        target_file: Path | None = None
        for f in files:
            sections, parse_findings = parse_structure_file(f)
            findings.extend(parse_findings)
            for sec in sections:
                for sub in sec.subsections:
                    if sub.subsection_id:
                        known_ids_all.add(sub.subsection_id)
                if sec.guide == target_guide and sec.section == target_section:
                    target_section_obj = sec
                    target_file = f
        if target_section_obj is not None and target_file is not None:
            check_section_prerequisites_graph(target_file, target_section_obj, findings, known_ids_all)
            return report(findings, label=f"prereq-graph section PD.GUIDE.{target_guide}.S{target_section}")

        findings.append(Finding("error", Path("."), None,
                                f"раздел PD.GUIDE.{target_guide}.S{target_section} не найден"))
        return report(findings, label="prerequisites-graph")

    # scope == "guide"
    g = parse_guide_id_arg(args.id)
    if g is None:
        return report(
            [Finding("error", Path("."), None,
                     f"--scope guide --id должен быть PD.GUIDE.<N> или N, получено: «{args.id}»")],
            label="prerequisites-graph",
        )
    targets = [Path(p) for p in args.paths]
    files, findings = collect_structure_files(targets)
    if not files:
        return report(findings, label="prerequisites-graph")
    for f in files:
        sections, parse_findings = parse_structure_file(f)
        findings.extend(parse_findings)
        secs = [s for s in sections if s.guide == g]
        if secs:
            check_guide_prereq_acyclic_and_order(f, g, secs, findings)
            return report(findings, label=f"prereq-graph guide PD.GUIDE.{g}")

    findings.append(Finding("error", Path("."), None, f"PD.GUIDE.{g} не найден"))
    return report(findings, label="prerequisites-graph")


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
    p_cross.add_argument("--scope", choices=["section", "guide"],
                         help="Ограничить scope проверки (WP-322 Ф3.8)")
    p_cross.add_argument("--id", help="ID scope: PD.GUIDE.<N> или PD.GUIDE.<N>.S<X>")
    p_cross.set_defaults(func=cmd_cross_guide)

    p_drift = sub.add_parser("pack-drift", help="Этап 14: cp/bh упоминания vs Pack FORM.089")
    p_drift.add_argument("paths", nargs="+")
    p_drift.add_argument("--pack", help="Путь к PD.FORM.089-learner-rcs.md")
    p_drift.add_argument("--scope", choices=["section", "guide"],
                         help="Ограничить scope проверки (WP-322 Ф3.8)")
    p_drift.add_argument("--id", help="ID scope: PD.GUIDE.<N> или PD.GUIDE.<N>.S<X>")
    p_drift.set_defaults(func=cmd_pack_drift)

    p_graph = sub.add_parser("graph", help="Концепт-граф из specs/v4-reference/ (build/diff)")
    graph_sub = p_graph.add_subparsers(dest="graph_cmd", required=True)

    p_graph_build = graph_sub.add_parser("build", help="Собрать граф (узлы + рёбра)")
    p_graph_build.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_graph_build.add_argument("--out-json", help="Записать JSON-снимок графа (иначе — stdout)")
    p_graph_build.add_argument("--out-dot", help="Записать Graphviz DOT для визуализации")
    p_graph_build.add_argument("--scope", choices=["section", "guide"],
                               help="Ограничить scope графа (WP-322 Ф3.8)")
    p_graph_build.add_argument("--id", help="ID scope: PD.GUIDE.<N> или PD.GUIDE.<N>.S<X>")
    p_graph_build.set_defaults(func=cmd_graph, graph_func=cmd_graph_build)

    p_graph_diff = graph_sub.add_parser("diff", help="Сравнить два JSON-снимка графа")
    p_graph_diff.add_argument("before", help="Старый JSON-снимок")
    p_graph_diff.add_argument("after", help="Новый JSON-снимок")
    p_graph_diff.set_defaults(func=cmd_graph, graph_func=cmd_graph_diff)

    # WP-322 Ф3.8: section / guide / prerequisites-graph
    p_section = sub.add_parser("section", help="CHECKLIST-section-v1 §🔴 (A-C): полнота, frontmatter, prereq-граф")
    p_section.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_section.add_argument("--id", required=True, help="ID раздела: PD.GUIDE.<N>.S<X>")
    p_section.set_defaults(func=cmd_section)

    p_guide = sub.add_parser("guide", help="CHECKLIST-guide-v1 §🔴 (A-D): полнота руководства, согласованность")
    p_guide.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_guide.add_argument("--id", required=True, help="ID руководства: PD.GUIDE.<N> или N (1-4)")
    p_guide.add_argument("--pack", help="Путь к PD.FORM.089-learner-rcs.md (для D.1-D.3 pack-drift)")
    p_guide.set_defaults(func=cmd_guide)

    p_pgraph = sub.add_parser("prerequisites-graph",
                              help="CHECKLIST-section-v1 §🔴 (B.1-B.3): автономная проверка графа prereq")
    p_pgraph.add_argument("paths", nargs="+", help="Файлы или директория v4-reference/")
    p_pgraph.add_argument("--scope", required=True, choices=["section", "guide"])
    p_pgraph.add_argument("--id", required=True, help="ID scope: PD.GUIDE.<N>.S<X> или PD.GUIDE.<N>")
    p_pgraph.set_defaults(func=cmd_prerequisites_graph)

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
