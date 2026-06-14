"""Тесты pack-drift G2 + JSON-контракт (WP-362 Ф7, peer-session 2026-06-14-44).

Тестируем CLI-контракт через subprocess — именно его зовёт pack-drift-watcher.yml.
Контракт:
  --json  : exit 0 при отработке (дрейф в JSON), exit 2 при сбое инструмента;
            drift_count = только error-level; warning_count отдельно.
  default : exit 1 при error-findings (PR-gate v4-lint.yml).
G2: concept.pack_source (PD.FORM/METHOD.NNN) должен существовать как файл в pack-root.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "v4-lint.py"


def _write_structure_guide(path: Path, pack_source: str) -> None:
    """Минимальный валидный structure-guide-N.md с одним подразделом и одним pack_source."""
    path.write_text(
        "---\n"
        "id: PD.GUIDE.1.STRUCTURE\n"
        'title: "Fixture"\n'
        "---\n\n"
        "# Fixture structure guide\n\n"
        "## Раздел 1. Fixture section\n\n"
        "### 1.1 Fixture subsection\n\n"
        "```yaml\n"
        "subsection_id: PD.GUIDE.1.S1.SS1\n"
        "parent_section_id: PD.GUIDE.1.S1\n"
        'title: "Fixture"\n'
        "cp_check: [cp.rhy]\n"
        "bh_check: [bh.sys]\n"
        "```\n\n"
        "**Понятия:**\n"
        f"- вводится: Понятие А → `U.Method` ({pack_source})\n\n"
        "**Содержание:** fixture.\n\n"
        "---\n",
        encoding="utf-8",
    )


def _make_fixtures(tmp_path: Path, pack_source: str, available_id: str = "PD.FORM.100"):
    """Возвращает (guide_file, pack_file, pack_root) для запуска pack-drift."""
    guide = tmp_path / "01-structure-guide-1.md"
    _write_structure_guide(guide, pack_source)

    pack_file = tmp_path / "PD.FORM.089-learner-rcs.md"
    pack_file.write_text("cp.rhy cp.wld bh.sys bh.awr\n", encoding="utf-8")

    pack_root = tmp_path / "pack-root"
    pack_root.mkdir()
    (pack_root / f"{available_id}-fixture.md").write_text("fixture\n", encoding="utf-8")
    return guide, pack_file, pack_root


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "pack-drift", *args],
        capture_output=True, text=True,
    )


def test_json_valid_ref_no_drift(tmp_path):
    """Валидный pack_source (есть файл в pack-root) → drift_count=0, exit 0."""
    guide, pack, root = _make_fixtures(tmp_path, "PD.FORM.100")
    r = _run([str(guide), "--pack", str(pack), "--pack-root", str(root), "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["drift_count"] == 0
    assert data["warning_count"] == 0


def test_json_broken_ref_is_drift(tmp_path):
    """Битый pack_source (PD.FORM.999 нет в pack-root) → drift_count>=1, error-item, exit 0."""
    guide, pack, root = _make_fixtures(tmp_path, "PD.FORM.999")
    r = _run([str(guide), "--pack", str(pack), "--pack-root", str(root), "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["drift_count"] >= 1
    errors = [i for i in data["items"] if i["severity"] == "error"]
    assert any("PD.FORM.999" in i["message"] for i in errors)


def test_json_missing_pack_root_downgrades_to_warning(tmp_path):
    """Недоступный pack-root → G2 пропущен (warning, не error), exit 0."""
    guide, pack, _ = _make_fixtures(tmp_path, "PD.FORM.999")
    r = _run([str(guide), "--pack", str(pack),
              "--pack-root", str(tmp_path / "nonexistent"), "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["drift_count"] == 0          # битый ref НЕ стал error без pack-root
    assert data["warning_count"] >= 1        # downgrade зафиксирован как warning


def test_json_missing_pack_arg_is_tool_failure(tmp_path):
    """Нет --pack → сбой инструмента → exit 2 (watcher не должен молча зеленеть)."""
    guide = tmp_path / "01-structure-guide-1.md"
    _write_structure_guide(guide, "PD.FORM.100")
    r = _run([str(guide), "--json"])
    assert r.returncode == 2, r.stderr


def test_json_schema_keys_present(tmp_path):
    """JSON-вывод содержит ключи контракта watcher'а."""
    guide, pack, root = _make_fixtures(tmp_path, "PD.FORM.100")
    r = _run([str(guide), "--pack", str(pack), "--pack-root", str(root), "--json"])
    data = json.loads(r.stdout)
    for key in ("tool", "version", "drift_count", "warning_count", "items"):
        assert key in data, f"missing key {key}"


def test_default_mode_broken_ref_fails_pr_gate(tmp_path):
    """default-режим (без --json): битый ref → exit 1 (валит PR в v4-lint.yml)."""
    guide, pack, root = _make_fixtures(tmp_path, "PD.FORM.999")
    r = _run([str(guide), "--pack", str(pack), "--pack-root", str(root)])
    assert r.returncode == 1, r.stdout


def test_default_mode_valid_ref_passes(tmp_path):
    """default-режим: валидный ref → exit 0."""
    guide, pack, root = _make_fixtures(tmp_path, "PD.FORM.100")
    r = _run([str(guide), "--pack", str(pack), "--pack-root", str(root)])
    assert r.returncode == 0, r.stdout
