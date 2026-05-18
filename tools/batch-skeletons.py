#!/usr/bin/env python3
"""batch-skeletons.py — массовая генерация skeleton для руководств v4.

Usage:
  python3 batch-skeletons.py --guide 2 --structure specs/v4-reference/02-structure-guide-2.md --out-dir docs/ru/personal-design/1-2-self-development-methods/
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "v4_lint", str(Path(__file__).parent / "v4-lint.py")
)
v4_lint = importlib.util.module_from_spec(_spec)
sys.modules["v4_lint"] = v4_lint
_spec.loader.exec_module(v4_lint)

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
bottleneck_hint: "{bottleneck_hint}"
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

**Мем, который снимается.** <узнаваемый образ или установка читателя, которая ограничивает или искажает понимание. Опровергается одним аргументом, который вводит понятия из `introduces`>

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


def yaml_list(values) -> str:
    if not values:
        return "[]"
    if isinstance(values, list):
        items = ", ".join(repr(v) if isinstance(v, str) else str(v) for v in values)
        return f"[{items}]"
    return repr(values)


def extract_meta(structure_text: str) -> dict:
    """Извлекает time_reading и time_practice из заголовка руководства."""
    meta = {}
    m = re.search(r'Время на подраздел[:：]\s*([^\n]+)', structure_text)
    if m:
        time_line = m.group(1).strip()
        # Пытаемся распарсить "45 мин чтение + 25 мин практика = 70 мин"
        parts = re.findall(r'(\d+)\s*мин\s*(чтение|практика)?', time_line)
        if len(parts) >= 2:
            meta['time_reading'] = f"{parts[0][0]} мин чтение"
            meta['time_practice'] = f"{parts[1][0]} мин"
        elif len(parts) == 1:
            meta['time_reading'] = f"{parts[0][0]} мин чтение"
            meta['time_practice'] = "15 мин"
    if 'time_reading' not in meta:
        meta['time_reading'] = "45 мин чтение"
    if 'time_practice' not in meta:
        meta['time_practice'] = "25 мин"
    return meta


def render_skeleton(sub, defaults: dict) -> str:
    fm = sub.frontmatter or {}
    introduces = fm.get("introduces", [])
    uses = fm.get("uses", [])
    prerequisites = fm.get("prerequisites", [])
    mastery_node = fm.get("mastery_node", defaults.get("mastery_node", "саморазвитие"))
    stage_relevant = fm.get("stage_relevant", defaults.get("stage_relevant", [1, 2, 3, 4, 5]))
    cp_check = fm.get("cp_check", [])
    bh_check = fm.get("bh_check", [])
    title = fm.get("title", "<TITLE>")
    bottleneck_hint = fm.get("bottleneck_hint", "<подсказка для застрявшего: какой индикатор проверить>")

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
        bottleneck_hint=bottleneck_hint,
        time_reading=defaults.get("time_reading", "45 мин чтение"),
        time_practice=defaults.get("time_practice", "25 мин"),
        sig_signature=sig_signature,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Массовая генерация skeleton для руководства v4")
    p.add_argument("--guide", required=True, type=int, help="Номер руководства (2,3,4)")
    p.add_argument("--structure", required=True, help="Путь к structure-guide-N.md")
    p.add_argument("--out-dir", required=True, help="Базовая директория для сохранения")
    p.add_argument("--wp", default=300, type=int, help="WP идентификатор")
    args = p.parse_args()

    structure_path = Path(args.structure)
    if not structure_path.exists():
        print(f"ERROR: --structure не найден: {args.structure}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sections, _ = v4_lint.parse_structure_file(structure_path)
    structure_text = structure_path.read_text(encoding="utf-8")
    meta = extract_meta(structure_text)

    defaults = {
        "wp": args.wp,
        "time_reading": meta["time_reading"],
        "time_practice": meta["time_practice"],
    }

    created = 0
    skipped = 0
    for sec in sections:
        for sub in sec.subsections:
            file_name = f"{sub.section}.{sub.order:02d}.md"
            file_path = out_dir / file_name
            if file_path.exists():
                skipped += 1
                continue
            skeleton = render_skeleton(sub, defaults)
            file_path.write_text(skeleton, encoding="utf-8")
            created += 1

    print(f"Guide {args.guide}: создано {created}, пропущено (уже есть) {skipped}, всего {created + skipped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
