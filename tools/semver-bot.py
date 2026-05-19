#!/usr/bin/env python3
"""semver-bot.py — автоматическое версионирование руководств v4 (WP-322 Ф6).

Алгоритм:
  1. Читает version.json для текущей версии.
  2. Перебирает git log --merges с последнего тега/даты.
  3. По лейблам/ключевым словам в сообщениях определяет уровень bump:
       [hotfix]         → patch (0.0.X)
       new-concept      → minor (0.X.0)  ← 1+ подраздел с новыми понятиями
       new-section      → minor (0.X.0)  ← новый раздел
       new-guide        → major (X.0.0)  ← новое руководство
  4. Выводит новую версию и changelog-блок в stdout.
  5. Если --write: обновляет version.json + добавляет в CHANGELOG.md.

Триггер в release.yml: ≥5 merged PR с pilot-approved / new-concept / hotfix
с момента последнего тега.

Usage:
  python3 tools/semver-bot.py [--write] [--since <git-ref>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
VERSION_FILE = REPO_ROOT / "version.json"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

# Уровни bump: 3=major, 2=minor, 1=patch, 0=no change
BUMP_PATTERNS = [
    (3, re.compile(r"\bnew-guide\b|\bfeat\(guide\)")),
    (2, re.compile(r"\bnew-section\b|\bnew-concept\b|\bfeat\(section\)|\bfeat\(skeleton\)")),
    (1, re.compile(r"\[hotfix\]|\bfix\b")),
]

RELEASE_TRIGGERS = {"pilot-approved", "new-concept", "new-section", "hotfix"}


def run(cmd: list[str], **kwargs) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout.strip()


def get_last_tag() -> str | None:
    try:
        tag = run(["git", "describe", "--tags", "--abbrev=0"])
        return tag
    except SystemExit:
        return None


def get_commits_since(since_ref: str | None) -> list[dict]:
    """Return merged commits since ref (or all if None)."""
    range_arg = f"{since_ref}..HEAD" if since_ref else "HEAD"
    log = run([
        "git", "log", "--merges",
        "--pretty=format:%H\t%s\t%b",
        range_arg,
    ])
    if not log:
        # Also get non-merge commits with relevant keywords
        log = run([
            "git", "log",
            "--pretty=format:%H\t%s",
            range_arg,
        ])

    commits = []
    for line in log.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2:
            commits.append({"hash": parts[0], "subject": parts[1], "body": parts[2] if len(parts) > 2 else ""})
    return commits


def classify_bump(commits: list[dict]) -> tuple[int, list[dict]]:
    """Return (max_bump_level, list of relevant commits)."""
    max_bump = 0
    relevant = []
    for c in commits:
        text = c["subject"] + " " + c["body"]
        for level, pattern in BUMP_PATTERNS:
            if pattern.search(text):
                if level > max_bump:
                    max_bump = level
                relevant.append(c)
                break
    return max_bump, relevant


def bump_version(version: str, level: int) -> str:
    parts = [int(x) for x in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    if level == 3:
        parts = [parts[0] + 1, 0, 0]
    elif level == 2:
        parts = [parts[0], parts[1] + 1, 0]
    elif level == 1:
        parts = [parts[0], parts[1], parts[2] + 1]
    return ".".join(str(x) for x in parts)


def format_changelog_entry(new_version: str, commits: list[dict]) -> str:
    today = date.today().isoformat()
    lines = [f"## [{new_version}] — {today}\n"]

    # Hotfix: коммит начинается с fix(/ fix: или содержит [hotfix] в квадратных скобках
    hotfixes = [c for c in commits
                if re.search(r"^\s*fix[\(:]|\[hotfix\]", c["subject"], re.IGNORECASE)]
    features = [c for c in commits if c not in hotfixes]

    if features:
        lines.append("### Добавлено\n")
        for c in features:
            subj = c["subject"]
            lines.append(f"- {subj}")
        lines.append("")

    if hotfixes:
        lines.append("### Исправлено\n")
        for c in hotfixes:
            subj = c["subject"]
            lines.append(f"- {subj}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Semver bump для руководств v4")
    p.add_argument("--since", metavar="GIT_REF",
                   help="Git ref начала периода (default: последний тег)")
    p.add_argument("--write", action="store_true",
                   help="Записать новую версию в version.json и CHANGELOG.md")
    p.add_argument("--min-commits", type=int, default=1,
                   help="Минимальное число релевантных коммитов для выпуска (default: 1)")
    args = p.parse_args()

    if not VERSION_FILE.exists():
        print(f"ERROR: version.json не найден: {VERSION_FILE}", file=sys.stderr)
        return 2

    data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    current_version = data.get("version", "0.0.0")

    since_ref = args.since or get_last_tag()
    commits = get_commits_since(since_ref)

    bump_level, relevant = classify_bump(commits)

    if len(relevant) < args.min_commits:
        print(f"semver-bot: {len(relevant)} релевантных коммитов < {args.min_commits} min — релиз не нужен")
        print(f"current_version={current_version}")
        return 0

    if bump_level == 0:
        print(f"semver-bot: нет коммитов, требующих bump")
        print(f"current_version={current_version}")
        return 0

    new_version = bump_version(current_version, bump_level)
    bump_names = {3: "major", 2: "minor", 1: "patch"}
    print(f"semver-bot: {current_version} → {new_version} ({bump_names[bump_level]} bump, {len(relevant)} коммитов)")
    print(f"new_version={new_version}")

    changelog_entry = format_changelog_entry(new_version, relevant)
    print("\n--- CHANGELOG ---")
    print(changelog_entry)

    if args.write:
        data["version"] = new_version
        data["released_at"] = date.today().isoformat()
        VERSION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✅ version.json обновлён: {current_version} → {new_version}")

        if CHANGELOG_FILE.exists():
            existing = CHANGELOG_FILE.read_text(encoding="utf-8")
            # Insert after first line (# Changelog header)
            first_nl = existing.find("\n")
            if first_nl >= 0:
                new_content = existing[:first_nl + 1] + "\n" + changelog_entry + existing[first_nl + 1:]
            else:
                new_content = changelog_entry + existing
        else:
            new_content = "# Changelog\n\n" + changelog_entry

        CHANGELOG_FILE.write_text(new_content, encoding="utf-8")
        print(f"✅ CHANGELOG.md обновлён")

    return 0


if __name__ == "__main__":
    sys.exit(main())
