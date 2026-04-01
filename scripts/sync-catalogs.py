"""
sync-catalogs.py — конвертация CAT.001, CAT.002, CAT.003 из MD → JSON.

Выходные файлы:
  DS-autonomous-agents/agents/tailor/memes.json      (CAT.001)
  DS-autonomous-agents/agents/tailor/practices.json  (CAT.002 + CAT.003)

Запуск:
  python3 scripts/sync-catalogs.py

Запускать после каждого обновления карточек в data/curriculum/.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_DIR = REPO_ROOT / "data" / "curriculum"
TAILOR_DIR = REPO_ROOT.parent / "DS-autonomous-agents" / "agents" / "tailor"


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADER_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+.+\n(.*?)(?=^##\s+|\Z)", re.DOTALL | re.MULTILINE)


def parse_frontmatter(text: str) -> dict:
    m = _FM_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def body_after_frontmatter(text: str) -> str:
    m = _FM_RE.match(text)
    return text[m.end():] if m else text


def extract_section(text: str, heading: str) -> str:
    """Извлечь содержимое секции по заголовку (без самого заголовка)."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\n(.*?)(?=^##\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_degree_block(text: str, degree_label: str) -> dict:
    """
    Из блока степени (Степень N — Название) извлечь can-do, задание, assessment.
    """
    pattern = re.compile(
        rf"^##\s+Степень\s+{degree_label}.*?\n(.*?)(?=^##\s+Степень|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return {}

    block = m.group(1)

    def _grab(label: str) -> str:
        p = re.compile(
            rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\*\*[А-ЯA-Z]|\Z)",
            re.DOTALL,
        )
        bm = p.search(block)
        return bm.group(1).strip() if bm else ""

    return {
        "degree": int(degree_label),
        "can_do": _grab("can-do"),
        "task": _grab("Задание"),
        "assessment": _grab("Assessment"),
    }


def extract_depth_block(text: str, depth_label: str) -> dict:
    """
    Из блока глубины (Глубина N — Название) извлечь can-do, задание, assessment.
    """
    pattern = re.compile(
        rf"^##\s+Глубина\s+{depth_label}.*?\n(.*?)(?=^##\s+Глубина|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return {}

    block = m.group(1)

    def _grab(label: str) -> str:
        p = re.compile(
            rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\*\*[А-ЯA-Z]|\Z)",
            re.DOTALL,
        )
        bm = p.search(block)
        return bm.group(1).strip() if bm else ""

    return {
        "depth": int(depth_label),
        "can_do": _grab("can-do"),
        "task": _grab("Задание"),
        "assessment": _grab("Assessment"),
    }


# ---------------------------------------------------------------------------
# CAT.001 → memes.json
# ---------------------------------------------------------------------------

def parse_meme_card(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm or fm.get("status") == "draft":
        return None

    body = body_after_frontmatter(text)

    # Извлечь diagnostics (первый абзац после заголовка)
    diag = extract_section(body, "Диагностика")

    # Антитезис — из первого абзаца body (строка **Продуктивный антитезис:**)
    antithesis_m = re.search(r"\*\*(?:Продуктивный антитезис|Антитезис):\*\*\s*(.+)", body)
    antithesis = antithesis_m.group(1).strip() if antithesis_m else ""

    # Различение
    dist_m = re.search(r"\*\*Ключевое различение:\*\*\s*(.+)", body)
    distinction = dist_m.group(1).strip() if dist_m else ""

    # Глубины 1–3
    depths = []
    for d in [1, 2, 3]:
        block = extract_depth_block(body, str(d))
        if block:
            depths.append(block)

    return {
        "id": fm.get("id", path.stem),
        "name": fm.get("name", ""),
        "area": int(fm.get("area", 1)),
        "entry_stage": int(fm.get("entry_stage", 0)),
        "blocks_transition": fm.get("blocks_transition", ""),
        "context": fm.get("context", ""),
        "distinction": distinction,
        "antithesis": antithesis,
        "diagnostics": diag,
        "depths": depths,
    }


def build_memes_json(cat001_dir: Path) -> dict:
    memes = []
    for f in sorted(cat001_dir.glob("M-*.md")):
        card = parse_meme_card(f)
        if card:
            memes.append(card)
    return {"version": "1.0", "source": "CAT.001", "count": len(memes), "memes": memes}


# ---------------------------------------------------------------------------
# CAT.002 + CAT.003 → practices.json
# ---------------------------------------------------------------------------

def parse_practice_card(path: Path, catalog: str) -> dict | None:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm or fm.get("status") == "draft":
        return None

    body = body_after_frontmatter(text)

    # Различение / принцип
    dist_m = re.search(r"\*\*Ключевое различение:\*\*\s*(.+)", body)
    distinction = dist_m.group(1).strip() if dist_m else ""

    # Принцип культуры
    principle_m = re.search(r"\*\*Принцип культуры:\*\*\s*(.+)", body)
    principle = principle_m.group(1).strip() if principle_m else ""

    # Ритуал (первый ##-блок с «Ритуал»)
    ritual = extract_section(body, "Ритуал учёта времени (единый для всех слотов)")
    if not ritual:
        ritual = extract_section(body, "Ритуал учёта времени (единый для рабочих слотов)")

    # Степени 1–4
    degrees = []
    for d in [1, 2, 3, 4]:
        block = extract_degree_block(body, str(d))
        if block:
            degrees.append(block)

    return {
        "id": fm.get("id", path.stem),
        "catalog": catalog,
        "name": fm.get("name", ""),
        "area": int(fm.get("area", 1)),
        "entry_stage": int(fm.get("entry_stage", 0)),
        "context": fm.get("context", fm.get("stream", "")),
        "distinction": distinction,
        "principle": principle,
        "ritual": ritual,
        "degrees": degrees,
    }


def build_practices_json(cat002_dir: Path, cat003_dir: Path) -> dict:
    practices = []

    for f in sorted(cat002_dir.glob("*.md")):
        if f.name == "README.md":
            continue
        card = parse_practice_card(f, "CAT.002")
        if card:
            practices.append(card)

    for f in sorted(cat003_dir.glob("METHOD*.md")):
        card = parse_practice_card(f, "CAT.003")
        if card:
            practices.append(card)

    return {
        "version": "1.0",
        "sources": ["CAT.002", "CAT.003"],
        "count": len(practices),
        "practices": practices,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cat001 = CURRICULUM_DIR / "CAT.001"
    cat002 = CURRICULUM_DIR / "CAT.002"
    cat003 = CURRICULUM_DIR / "CAT.003"

    if not TAILOR_DIR.exists():
        print(f"[ERROR] tailor dir not found: {TAILOR_DIR}", file=sys.stderr)
        sys.exit(1)

    # Мемы
    memes_data = build_memes_json(cat001)
    memes_out = TAILOR_DIR / "memes.json"
    memes_out.write_text(json.dumps(memes_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] memes.json: {memes_data['count']} мемов → {memes_out}")

    # Практики
    practices_data = build_practices_json(cat002, cat003)
    practices_out = TAILOR_DIR / "practices.json"
    practices_out.write_text(json.dumps(practices_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] practices.json: {practices_data['count']} практик → {practices_out}")


if __name__ == "__main__":
    main()
