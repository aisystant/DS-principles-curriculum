"""
Скрипт извлечения детских ячеек из репо kids-learning-pack (Д. Асфандияров).

Источник (Pack):  github.com/asf-denis-system/kids-learning-pack
Результат (DS):   data/curriculum/kids_cells.json

Запуск: python scripts/extract_kids_cells.py
Требования: gh CLI с доступом к репо asf-denis-system/kids-learning-pack

Архитектура:
  kids-learning-pack (Denis, Pack)  →  DS-principles-curriculum (DS-instrument)  →  Bot Child Training
  Денис обновляет карточки → запускаем этот скрипт → kids_cells.json обновляется → бот видит новый контент
"""

import base64
import json
import re
import subprocess
from pathlib import Path

REPO = "asf-denis-system/kids-learning-pack"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "curriculum"

# Z-принципы: id → meta (из 01-domain-contract/01B-distinctions.md Дениса)
Z_PRINCIPLES = {
    "Z0": {
        "name": "Инварианты",
        "zp_ref": "ZP.2",
        "key_question": "Что здесь осталось тем же, хотя выглядит иначе?",
        "domains": ["быт", "природа", "игра", "математика"],
    },
    "Z1": {
        "name": "Симметрии операций",
        "zp_ref": "ZP.2",
        "key_question": "Если поменять шаги местами — будет то же самое?",
        "domains": ["быт", "приготовление еды", "игра"],
    },
    "Z2": {
        "name": "Композиция / системность",
        "zp_ref": ["ZP.2", "ZP.3"],
        "key_question": "Из чего состоит? Что изменится, если убрать эту часть?",
        "domains": ["быт", "природа", "конструирование", "язык"],
    },
    "Z3": {
        "name": "Оптимизация",
        "zp_ref": "ZP.4",
        "key_question": "Что здесь значит лучше? По какому правилу? Какие ограничения?",
        "domains": ["быт", "игра", "планирование"],
    },
    "Z4": {
        "name": "Неопределённость / вероятность",
        "zp_ref": "ZP.5",
        "key_question": "Это точно? Или скорее всего? Или ты не знаешь?",
        "domains": ["природа", "игра", "прогнозы"],
    },
    "Z5": {
        "name": "Многомасштабность",
        "zp_ref": "ZP.3",
        "key_question": "На каком уровне мы сейчас смотрим? Что видно здесь и не видно там?",
        "domains": ["природа", "город", "тело"],
    },
    "Z6": {
        "name": "Ресурсные ограничения",
        "zp_ref": "ZP.6",
        "key_question": "Сколько у нас времени/попыток/сил? Хватит? Что упростим?",
        "domains": ["быт", "планирование", "игра"],
    },
    "Z7": {
        "name": "Интервенция / причинность",
        "zp_ref": None,  # нет аналога в ZP.1–ZP.6 — потенциальный ZP.7
        "key_question": "Что мы поменяли? Что оставили одинаковым? Что изменилось?",
        "domains": ["природа", "эксперименты", "быт"],
    },
}

# Файлы preschool (3–6 лет)
PRESCHOOL_FILES = {
    "Z0": "Z0-invariants.md",
    "Z1": "Z1-symmetry.md",
    "Z2": "Z2-composition.md",
    "Z3": "Z3-optimization.md",
    "Z4": "Z4-probability.md",
    "Z5": "Z5-multiscale.md",
    "Z6": "Z6-resources.md",
    "Z7": "Z7-intervention.md",
}

# Файлы school (7–10 лет)
SCHOOL_FILES = {
    "Z0": "Z0-invariants.md",
    "Z1": "Z1-symmetry.md",
    "Z2": "Z2-composition.md",
    "Z3": "Z3-optimization.md",
    "Z4": "Z4-probability.md",
    "Z5": "Z5-multiscale.md",
    "Z6": "Z6-resources.md",
    "Z7": "Z7-intervention.md",
}


# ─────────────────────────────────────────────
# GitHub fetch
# ─────────────────────────────────────────────

def fetch_file(path: str) -> str:
    """Fetch file content from GitHub via gh CLI. Returns decoded text or ''."""
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{path}", "--jq", ".content"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  WARNING: not found — {path}")
        return ""
    try:
        return base64.b64decode(result.stdout.strip()).decode("utf-8")
    except Exception as e:
        print(f"  WARNING: decode error {path}: {e}")
        return ""


# ─────────────────────────────────────────────
# Markdown parsers
# ─────────────────────────────────────────────

def clean_md(text: str) -> str:
    """Strip basic markdown formatting."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # bold
    text = re.sub(r'__(.+?)__', r'\1', text)        # bold alt
    text = re.sub(r'\*(.+?)\*', r'\1', text)        # italic
    text = re.sub(r'`(.+?)`', r'\1', text)          # inline code
    text = re.sub(r'^> ', '', text, flags=re.MULTILINE)  # blockquote
    return text.strip()


def extract_section(content: str, *headings: str) -> str:
    """Extract first matching markdown section (## or ###)."""
    for heading in headings:
        pattern = rf'##+ {re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def extract_bullets(block: str) -> list[str]:
    """Extract bullet list items, cleaned of markdown."""
    bullets = re.findall(r'^[-*]\s+(.+)', block, re.MULTILINE)
    return [clean_md(b) for b in bullets if b.strip()]


def extract_can_do(content: str) -> list[str]:
    """Extract success indicators from preschool or school card."""
    # School: "### Признаки успеха" subsection inside "## Что развивает"
    m = re.search(
        r'###\s+Признаки успеха\s*\n(.*?)(?=\n###|\n##|\Z)',
        content, re.DOTALL
    )
    if m:
        # Combine both depth sub-lists
        all_bullets = extract_bullets(m.group(1))
        if all_bullets:
            return all_bullets

    # Preschool: "## Чему учит этот эпизод" — bullet list after intro
    m = re.search(
        r'##\s+Чему учит этот эпизод\s*\n(.*?)(?=\n##|\Z)',
        content, re.DOTALL
    )
    if m:
        bullets = extract_bullets(m.group(1))
        if bullets:
            return bullets

    return []


def extract_transfer_test(content: str) -> str:
    """Extract transfer test line."""
    patterns = [
        r'\*\*Тест переноса[^*]*\*\*[:\s]+(.+?)(?=\n\n|\n---|\n##|\Z)',
        r'Тест переноса[:\s]+(.+?)(?=\n\n|\n---|\n##|\Z)',
    ]
    for p in patterns:
        m = re.search(p, content, re.DOTALL)
        if m:
            return clean_md(m.group(1).strip().split('\n')[0])
    return ""


def extract_criteria(content: str) -> str:
    """Extract success criteria from 'Что наблюдать' — ✅ rows."""
    m = re.search(r'##+ Что наблюдать\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if not m:
        return ""
    block = m.group(1)
    rows = re.findall(r'\|([^|\n]+)\|[^|\n]*✅[^|\n]*\|', block)
    if rows:
        cleaned = [clean_md(r.strip()) for r in rows if r.strip() and '---' not in r]
        return '; '.join(cleaned)
    return ""


def extract_common_errors(content: str) -> list[dict]:
    """Extract adult errors from 'Типичные ошибки взрослого' table."""
    m = re.search(r'##+ Типичные ошибки взрослого\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    errors = []
    # Table: | Ошибка | Как выглядит | Как исправить |
    for row in re.findall(r'\|([^|\n]+)\|([^|\n]+)\|([^|\n]+)\|', block):
        error = clean_md(row[0].strip())
        fix = clean_md(row[2].strip())
        if error and '---' not in error and error.lower() not in ('ошибка', 'error', 'mistake'):
            errors.append({"error": error, "why": fix})
    return errors


def extract_scenario_preschool(content: str, max_chars: int = 1200) -> str:
    """Extract preschool scenario text (condensed)."""
    m = re.search(r'##+ Сценарий эпизода\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if not m:
        return ""
    text = clean_md(m.group(1))
    # Remove table formatting
    text = re.sub(r'\|[^\n]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()[:max_chars]


def extract_scenario_school_depth(content: str, depth: int, max_chars: int = 1200) -> str:
    """Extract school scenario for specific depth."""
    if depth == 1:
        patterns = [
            r'###\s+Часть 1[^\n]*\n(.*?)(?=###\s+Часть 2|##\s+Что наблюдать|\Z)',
            r'##\s+Сценарий эпизода\s*\n(.*?)(?=###\s+Часть 2|##\s+Что наблюдать|\Z)',
        ]
    else:  # depth 2
        patterns = [
            r'###\s+Часть 2[^\n]*\n(.*?)(?=###\s+Часть 3|##\s+Что наблюдать|\Z)',
        ]
    for p in patterns:
        m = re.search(p, content, re.DOTALL)
        if m:
            text = clean_md(m.group(1))
            text = re.sub(r'\|[^\n]+', '', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()[:max_chars]
    return ""


def extract_depth2_can_do(content: str) -> list[str]:
    """Extract Depth 2 can_do from school card (Глубина 2 subsection)."""
    m = re.search(
        r'Глубина 2[^\n]*объясняет[^\n]*\n(.*?)(?=\n###|\n##|\Z)',
        content, re.DOTALL
    )
    if m:
        return extract_bullets(m.group(1))
    return []


# ─────────────────────────────────────────────
# Main processing
# ─────────────────────────────────────────────

def process_principle(principle_id: str) -> dict:
    """Process one principle: fetch both tracks, build cell structure."""
    print(f"\nProcessing {principle_id}...")
    meta = Z_PRINCIPLES[principle_id]

    # Fetch cards
    preschool_content = fetch_file(f"03-methods/preschool/{PRESCHOOL_FILES[principle_id]}")
    if preschool_content:
        print(f"  ✅ preschool/{PRESCHOOL_FILES[principle_id]}")

    school_content = fetch_file(f"03-methods/school/{SCHOOL_FILES[principle_id]}")
    if school_content:
        print(f"  ✅ school/{SCHOOL_FILES[principle_id]}")

    # Common fields (prefer preschool as base, fallback to school)
    base = preschool_content or school_content
    can_do_d1 = extract_can_do(preschool_content) or extract_can_do(school_content)
    transfer_test = extract_transfer_test(preschool_content) or extract_transfer_test(school_content)
    criteria = extract_criteria(preschool_content) or extract_criteria(school_content)
    common_errors = extract_common_errors(preschool_content) or extract_common_errors(school_content)
    domains = meta["domains"]

    # Depth 1 — preschool (preoperational) + school d1 (concrete_operational)
    preschool_scenario = extract_scenario_preschool(preschool_content)
    school_scenario_d1 = extract_scenario_school_depth(school_content, depth=1)

    depth_1 = {
        "bloom_level": "Remember",
        "can_do": can_do_d1,
        "transfer_test": transfer_test,
        "criteria": criteria,
        "common_errors": common_errors,
        "domains": domains,
        "forms": {
            "preoperational": preschool_scenario,
            "concrete_operational": school_scenario_d1,
            "formal_operational": "Не применимо на данной глубине",
            "postformal": "Не применимо на данной глубине",
        },
    }

    depths = {"1": depth_1}

    # Depth 2 — school only (concrete_operational углублённый)
    school_scenario_d2 = extract_scenario_school_depth(school_content, depth=2)
    if school_scenario_d2:
        can_do_d2 = extract_depth2_can_do(school_content)
        depth_2 = {
            "bloom_level": "Understand",
            "can_do": can_do_d2 or can_do_d1,
            "transfer_test": transfer_test,
            "criteria": criteria,
            "common_errors": common_errors,
            "domains": domains,
            "forms": {
                "preoperational": "Не применимо — слишком абстрактно для 3-6 лет",
                "concrete_operational": school_scenario_d2,
                "formal_operational": "Не применимо на данной глубине",
                "postformal": "Не применимо на данной глубине",
            },
        }
        depths["2"] = depth_2

    return {
        "name": meta["name"],
        "key_question": meta["key_question"],
        "zp_ref": meta["zp_ref"],
        "depths": depths,
    }


def validate(result: dict) -> bool:
    """Проверить качество извлечённых ячеек. Возвращает True если всё OK.

    Критические ошибки (exit 1):
    - Принцип пропущен полностью
    - forms.preoperational или forms.concrete_operational пустые у depth 1

    Предупреждения (продолжаем, но сообщаем):
    - transfer_test пустой
    - can_do пустой
    - criteria пустой
    """
    MIN_SCENARIO_CHARS = 50
    errors = []
    warnings = []

    expected = set(Z_PRINCIPLES.keys())
    extracted = set(result.keys())
    missing = expected - extracted
    if missing:
        errors.append(f"Пропущены принципы: {missing}")

    for pid, principle in result.items():
        depths = principle.get("depths", {})

        if "1" not in depths:
            errors.append(f"{pid}: нет depth 1")
            continue

        d1 = depths["1"]
        forms = d1.get("forms", {})

        preop = forms.get("preoperational", "")
        if len(preop) < MIN_SCENARIO_CHARS:
            errors.append(f"{pid} depth 1: forms.preoperational пуст или слишком короткий ({len(preop)} chars) — возможно, секция «Сценарий эпизода» переименована в preschool-карточке")

        conop = forms.get("concrete_operational", "")
        if len(conop) < MIN_SCENARIO_CHARS:
            errors.append(f"{pid} depth 1: forms.concrete_operational пуст ({len(conop)} chars) — возможно, секция «Часть 1» переименована в school-карточке")

        if not d1.get("can_do"):
            warnings.append(f"{pid} depth 1: can_do пуст — секция «Признаки успеха» / «Чему учит» не найдена")

        if not d1.get("transfer_test"):
            warnings.append(f"{pid} depth 1: transfer_test пуст — строка «Тест переноса» не найдена")

        if not d1.get("criteria"):
            warnings.append(f"{pid} depth 1: criteria пуст — ✅ строки в «Что наблюдать» не найдены")

    print("\n── Валидация ──────────────────────────────")
    if warnings:
        for w in warnings:
            print(f"  ⚠️  {w}")
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        print(f"\nВалидация: FAILED ({len(errors)} ошибок, {len(warnings)} предупреждений)")
        print("Совет: проверьте что Denis не переименовал секции в карточках.")
        return False
    else:
        print(f"  ✅ Все {len(result)} принципов прошли валидацию ({len(warnings)} предупреждений)")
        return True


def main():
    print(f"Extracting kids cells from {REPO}...")
    result = {}

    for principle_id in Z_PRINCIPLES:
        try:
            result[principle_id] = process_principle(principle_id)
        except Exception as e:
            print(f"  ERROR {principle_id}: {e}")
            import traceback
            traceback.print_exc()

    # Валидация перед записью
    ok = validate(result)
    if not ok:
        print("\nФайл НЕ записан из-за критических ошибок. Исправьте extract-скрипт и запустите снова.")
        import sys
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "kids_cells.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total_depths = sum(len(p.get("depths", {})) for p in result.values())
    size_kb = output_path.stat().st_size / 1024
    print(f"\nDone: {len(result)} principles, {total_depths} depth cells")
    print(f"Output: {output_path} ({size_kb:.1f} KB)")
    print("\nСледующий шаг: скопируй в бот и задеплой:")
    print(f"  cp {output_path} <aist_bot>/data/curriculum/kids_cells.json")


if __name__ == "__main__":
    main()
