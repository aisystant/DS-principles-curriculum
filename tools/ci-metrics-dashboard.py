#!/usr/bin/env python3
"""
ci-metrics-dashboard.py — WP-322 Ф7-MVP.

Собирает метрики CI из GitHub Actions через `gh run list` и генерирует markdown dashboard.
Запускается из `.github/workflows/ci-metrics.yml` (по расписанию или вручную).

Метрики:
- pass rate за последние N дней
- avg build time по workflow
- total runs
- последний drift count (из pack-drift-watcher логов, если доступно)

Usage:
  python3 tools/ci-metrics-dashboard.py --days 7 --out dashboard.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKFLOWS = [
    ("v4-lint.yml", "v4-lint", "🔴 Lint gates"),
    ("content-validation.yaml", "content-validation", "🔴 Pack-sufficiency"),
    ("pack-drift-watcher.yml", "Pack Drift Watcher", "🟡 Pack drift"),
    ("build-skeleton.yml", "build-skeleton", "🟢 Skeleton build"),
    ("release.yml", "release", "🟢 Release"),
]


def gh_json(cmd: list[str]) -> list[dict]:
    """Run gh command and return JSON output."""
    result = subprocess.run(
        cmd + ["--json", "name,status,conclusion,createdAt,updatedAt,databaseId,headBranch"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        print(f"[WARN] gh failed: {result.stderr}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[WARN] JSON parse error: {e}", file=sys.stderr)
        return []


def parse_iso(s: str) -> datetime:
    # GitHub format: 2026-05-19T16:03:15Z
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def duration_sec(start: str, end: str) -> int:
    d = parse_iso(end) - parse_iso(start)
    return max(0, int(d.total_seconds()))


def get_drift_count(run_id: int) -> int | None:
    """Try to extract drift_count from pack-drift-watcher run logs."""
    # gh run view --log prints job logs; we grep for drift_count
    result = subprocess.run(
        ["gh", "run", "view", str(run_id), "--log"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        # Pattern 1: drift_count=1 (from echo or GITHUB_OUTPUT)
        if "drift_count=" in line:
            parts = line.split("drift_count=")
            if len(parts) >= 2:
                val = parts[1].split()[0].split(",")[0].strip()
                try:
                    return int(val)
                except ValueError:
                    continue
        # Pattern 2: Drift count: 1 (from echo in stub-pack-drift step)
        if "Drift count:" in line:
            parts = line.split("Drift count:")
            if len(parts) >= 2:
                val = parts[1].split(",")[0].strip()
                try:
                    return int(val)
                except ValueError:
                    continue
        # Pattern 3: DRIFT_COUNT: 1 (from env var in issue creation step)
        if "DRIFT_COUNT:" in line:
            parts = line.split("DRIFT_COUNT:")
            if len(parts) >= 2:
                val = parts[1].strip()
                try:
                    return int(val)
                except ValueError:
                    continue
    return None


def analyze_workflow(filename: str, display_name: str, days: int) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    runs = gh_json(["gh", "run", "list", "--workflow", filename, "--limit", "100", "--created", f">={since[:10]}"])

    total = len(runs)
    successes = sum(1 for r in runs if r.get("conclusion") == "success")
    failures = sum(1 for r in runs if r.get("conclusion") == "failure")
    durations = [duration_sec(r["createdAt"], r["updatedAt"]) for r in runs]
    avg_duration = sum(durations) // len(durations) if durations else 0

    latest = runs[0] if runs else None
    latest_drift = None
    if latest and display_name == "Pack Drift Watcher":
        latest_drift = get_drift_count(latest["databaseId"])

    return {
        "name": display_name,
        "filename": filename,
        "total": total,
        "successes": successes,
        "failures": failures,
        "pass_rate": (successes / total * 100) if total else 0,
        "avg_duration_sec": avg_duration,
        "latest_conclusion": latest["conclusion"] if latest else "N/A",
        "latest_run_url": f"https://github.com/{get_repo()}/actions/runs/{latest['databaseId']}" if latest else "N/A",
        "latest_drift": latest_drift,
    }


def get_repo() -> str:
    # Try GITHUB_REPOSITORY env var
    repo = Path(".git").parent.resolve()
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True, check=False, cwd=str(repo),
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "aisystant/DS-principles-curriculum"


def generate_dashboard(results: list[dict], days: int) -> str:
    lines = [
        "# CI Metrics Dashboard",
        "",
        f"> Автоматически сгенерировано WP-322 Ф7. Период: последние **{days} дней**.",
        f"> Время генерации: `{datetime.now(timezone.utc).isoformat()}` UTC",
        "",
        "## Сводка по workflow",
        "",
        "| Workflow | Runs | ✅ Pass | ❌ Fail | Pass rate | Avg duration | Last status |",
        "|----------|------|---------|---------|-----------|--------------|-------------|",
    ]

    for r in results:
        status_icon = "✅" if r["latest_conclusion"] == "success" else "❌" if r["latest_conclusion"] == "failure" else "⏳"
        avg_min = r["avg_duration_sec"] // 60
        avg_sec = r["avg_duration_sec"] % 60
        duration_str = f"{avg_min}m {avg_sec}s" if r["avg_duration_sec"] else "—"
        pass_rate_str = f"{r['pass_rate']:.1f}%" if r["total"] else "—"
        lines.append(
            f"| [{r['name']}]({r['latest_run_url']}) | {r['total']} | {r['successes']} | {r['failures']} | {pass_rate_str} | {duration_str} | {status_icon} {r['latest_conclusion']} |"
        )

    lines.extend([
        "",
        "## Pack drift (последний run)",
        "",
    ])

    drift_result = next((r for r in results if r["name"] == "Pack Drift Watcher"), None)
    if drift_result and drift_result["latest_drift"] is not None:
        lines.append(f"- **drift_count** = `{drift_result['latest_drift']}`")
        if drift_result["latest_drift"] == 0:
            lines.append("- ✅ Curriculum синхронизирован с Pack.")
        else:
            lines.append("- ⚠️ Требуется ревизия подразделов. См. [pack-drift issues](../../labels/pack-drift).")
    else:
        lines.append("- _Нет данных (workflow не запускался или логи недоступны)._")

    lines.extend([
        "",
        "## Определения",
        "",
        "- **Pass rate** = успешные run'ы / общее количество run'ов за период.",
        "- **Avg duration** = среднее время от start до completion (включая queued time, приблизительно).",
        "- **Last status** = conclusion последнего run'а (success / failure / cancelled / etc).",
    ])

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Период в днях (default: 7)")
    parser.add_argument("--out", type=str, default="CI-DASHBOARD.md", help="Выходной markdown файл")
    args = parser.parse_args()

    print(f"Collecting CI metrics for last {args.days} days...")

    results = []
    for filename, display_name, _label in WORKFLOWS:
        print(f"  → {display_name} ...", end=" ", flush=True)
        data = analyze_workflow(filename, display_name, args.days)
        results.append(data)
        print(f"{data['total']} runs, {data['pass_rate']:.0f}% pass")

    markdown = generate_dashboard(results, args.days)

    out_path = Path(args.out)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"\nDashboard written to {out_path}")

    # Also write to GITHUB_STEP_SUMMARY if available
    summary_file = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    if summary_file.name != "/dev/null":
        summary_file.write_text(markdown, encoding="utf-8")
        print("Step summary updated.")

    return 0


if __name__ == "__main__":
    import os
    sys.exit(main())
