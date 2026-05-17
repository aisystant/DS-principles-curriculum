#!/usr/bin/env python3
"""build-skeleton.py — детерминированная сборка SS-skeleton (WP-322 Ф3).

Вход: subsection_id (PD.GUIDE.N.SX.SSY) + путь к structure-guide-N.md
Выход: markdown skeleton SS-файла по v4-структуре (13 блоков из PD.FORM.103).

Этап 8 WRITING-PIPELINE: автор/Портной получает skeleton с placeholder-ами,
заполняет содержанием, прогоняет /verify subsection.

Usage:
  python3 build-skeleton.py --id PD.GUIDE.1.S6.SS1 \\
    --structure specs/v4-reference/01-structure-guide-1.md \\
    --out docs/ru/personal-new-staging/.../6.01-five-stages.md

Если --out не указан — печать в stdout.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Делим ответственность: парсим structure через v4-lint.parse_structure_file
# NB: dataclass требует module в sys.modules до exec_module (Python 3.9 quirk)
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "v4_lint", str(Path(__file__).parent / "v4-lint.py")
)
v4_lint = importlib.util.module_from_spec(_spec)
sys.modules["v4_lint"] = v4_lint
_spec.loader.exec_module(v4_lint)


SUBSECTION_ID_RE = re.compile(r"^PD\.GUIDE\.(\d+)\.S(\d+)\.SS(\d+)$")


SKELETON_TEMPLATE = """---
wp: {wp}
guide: {guide}
section: {section}
subsection_id: {subsection_id}
parent_section_id: PD.GUIDE.{guide}.S{section}
title: {title}
order: {order}
introduces: {introduces}
uses: {uses}
prerequisites: {prerequisites}
mastery_node: {mastery_node}
stage_relevant: {stage_relevant}
can_do:
  - "Могу <НАБЛЮДАЕМОЕ действие, проверяемое за <5 мин>"
cp_check: {cp_check}
bh_check: {bh_check}
bottleneck_hint: "<подсказка для застрявшего: какой индикатор проверить>"
time_reading: {time_reading}
time_practice: {time_practice}
word_count_target: 500–1500
status: draft
format_version: '4.1'
---


#### §{section}.{order:02d} {title}

**Время:** {time_reading} + {time_practice} = <сумма>
**Что узнаешь:** <одно предложение о ключевом понимании>

**В одном предложении:** <короткий тезис подраздела — мем + объект + сдвиг>

**Сигнатура понятий:** {sig_signature}

**Мем, который снимается.** <узнаваемый образ или установка читателя, которая ограничивает или искажает понимание. Опровергается одним аргументом, который вводит понятия из `introduces`.>

**Определение из источника.** <ввод формальных понятий через ссылку на Pack (PD.FORM/METHOD/CAT.NNN). Каждый термин в `introduces` определяется один раз — здесь.>

**Развитие мысли.** <разворот: связи понятий между собой и с надсистемой. Thinking Through Writing — каждый абзац несёт одну новую мысль, не повтор.>

**Метод — минимальный шаг.** <конкретное действие, которое читатель может выполнить за заявленные `time_practice` минут. ≥3 шага с порядком/длительностью.>

**Пример из жизни.** <конкретный, желательно из доменов разных от прежних подразделов. На ст. 1-2 — личный опыт, близкое окружение. На ст. 3-5 — системные кейсы.>

**Типичная ошибка.** <2-3 распространённые когнитивные ловушки + почему возникают. Не «не делайте Y», а «люди склонны думать X потому что Z, на самом деле W».>

**Степени мастерства:**

| Степень | Что происходит | Критерий перехода |
|---------|----------------|-------------------|
| 1. Объясняю | Могу сформулировать суть понятий и метода | Один раз практически применил |
| 2. Умею | Применяю метод по чеклисту, получаю результат | Раз в неделю воспроизвожу без подсказки |
| 3. Навык | Применяю без напоминания, ловлю случаи где нужен | Замечаю в чужой ситуации, могу подсказать |
| 4. Мастерство | Помогаю другим освоить, передаю культуру | Веду группу, развиваю метод |

**Проверка себя.**
- Понимание: <вопрос, на который читатель должен ответить с пониманием, не пересказом>
- Поведение: <наблюдаемый индикатор: что я сейчас делаю/перестал делать>
- Застревание: <маркер, что застрял на текущей ступени — какой сигнал ловить>

**Что дальше.** <отсылка к следующему подразделу или к более широкой картине (программа «Рабочее развитие», старшие ступени, надсистема). Открывает горизонт за пределы подраздела.>
"""


def parse_id(subsection_id: str) -> tuple[int, int, int] | None:
    m = SUBSECTION_ID_RE.match(subsection_id.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def find_subsection(structure_path: Path, subsection_id: str):
    """Возвращает Subsection-объект из structure-guide или None."""
    sections, _ = v4_lint.parse_structure_file(structure_path)
    for sec in sections:
        for sub in sec.subsections:
            if sub.subsection_id == subsection_id:
                return sub
    return None


def yaml_list(values) -> str:
    """`['a', 'b']` → строка YAML."""
    if not values:
        return "[]"
    if isinstance(values, list):
        items = ", ".join(repr(v) if isinstance(v, str) else str(v) for v in values)
        return f"[{items}]"
    return repr(values)


def render_skeleton(sub, defaults: dict) -> str:
    """Заполнить SKELETON_TEMPLATE данными из parsed Subsection."""
    fm = sub.frontmatter or {}

    introduces = fm.get("introduces", [])
    uses = fm.get("uses", [])
    prerequisites = fm.get("prerequisites", [])
    mastery_node = fm.get("mastery_node", defaults.get("mastery_node", "саморазвитие"))
    stage_relevant = fm.get("stage_relevant", defaults.get("stage_relevant", [1, 2, 3, 4, 5]))
    cp_check = fm.get("cp_check", [])
    bh_check = fm.get("bh_check", [])
    title = fm.get("title", "<TITLE>")

    sig_concepts = []
    for c in (sub.concepts or [])[:3]:
        name = (c.get("name") or "").strip()
        if name:
            sig_concepts.append(name)
    sig_signature = "; ".join(f"{n} — <определение>" for n in sig_concepts) or "<3-5 ключевых понятий с короткими определениями>"

    return SKELETON_TEMPLATE.format(
        wp=defaults.get("wp", 300),
        guide=sub.guide,
        section=sub.section,
        order=sub.order,
        subsection_id=sub.subsection_id,
        title=title,
        introduces=yaml_list(introduces),
        uses=yaml_list(uses),
        prerequisites=yaml_list(prerequisites),
        mastery_node=yaml_list(mastery_node) if isinstance(mastery_node, list) else f"[{mastery_node}]",
        stage_relevant=yaml_list(stage_relevant),
        cp_check=yaml_list(cp_check),
        bh_check=yaml_list(bh_check),
        time_reading=defaults.get("time_reading", "15 мин чтение"),
        time_practice=defaults.get("time_practice", "15 мин"),
        sig_signature=sig_signature,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Сборка SS-skeleton по subsection_id")
    p.add_argument("--id", required=True, help="subsection_id (PD.GUIDE.N.SX.SSY)")
    p.add_argument("--structure", required=True, help="Путь к structure-guide-N.md")
    p.add_argument("--out", help="Файл для записи (иначе stdout)")
    p.add_argument("--wp", default=300, type=int, help="WP идентификатор (default: 300)")
    p.add_argument("--time-reading", default="15 мин чтение", help="time_reading")
    p.add_argument("--time-practice", default="15 мин", help="time_practice")
    args = p.parse_args()

    parsed = parse_id(args.id)
    if parsed is None:
        print(f"ERROR: --id «{args.id}» не соответствует PD.GUIDE.N.SX.SSY", file=sys.stderr)
        return 2

    structure_path = Path(args.structure)
    if not structure_path.exists():
        print(f"ERROR: --structure «{args.structure}» не найден", file=sys.stderr)
        return 2

    sub = find_subsection(structure_path, args.id)
    if sub is None:
        print(f"ERROR: подраздел «{args.id}» не найден в {structure_path.name}", file=sys.stderr)
        return 1

    defaults = {
        "wp": args.wp,
        "time_reading": args.time_reading,
        "time_practice": args.time_practice,
    }
    skeleton = render_skeleton(sub, defaults)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(skeleton, encoding="utf-8")
        print(f"OK: {args.id} → {out_path}", file=sys.stderr)
    else:
        sys.stdout.write(skeleton)

    return 0


if __name__ == "__main__":
    sys.exit(main())
