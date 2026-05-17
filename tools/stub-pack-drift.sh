#!/usr/bin/env bash
# stub-pack-drift.sh — placeholder для будущего v4-lint pack-drift
#
# Usage: bash tools/stub-pack-drift.sh --pack <path-to-pack-form-file> [--curriculum <path>]
#
# Назначение: Pack-watcher (Ф1 WP-322) — детектор drift между PACK-personal/PD.FORM.089
# и подразделами руководств в DS-principles-curriculum.
#
# Текущая реализация: stub. Всегда возвращает exit 0 и пишет diagnostic в stdout.
# Будущая замена: `python3 tools/v4-lint.py pack-drift --pack <...> --scope <...>` (WP-321).
#
# Output (для GitHub Actions): JSON в stdout с полями {drift_count, items[]}.
# - drift_count = 0 → no issue
# - drift_count > 0 → создать issue по шаблону .github/ISSUE_TEMPLATE/pack-drift.yml

set -euo pipefail

PACK_PATH=""
CURRICULUM_PATH="."
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pack) PACK_PATH="$2"; shift 2 ;;
        --curriculum) CURRICULUM_PATH="$2"; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$PACK_PATH" ]]; then
    echo "ERROR: --pack required" >&2
    echo "Usage: bash tools/stub-pack-drift.sh --pack <path-to-PD.FORM.089>" >&2
    exit 2
fi

if [[ ! -f "$PACK_PATH" ]]; then
    echo "ERROR: pack file not found: $PACK_PATH" >&2
    exit 2
fi

# STUB LOGIC
# Реальный v4-lint pack-drift будет:
#   1. Парсить PACK_PATH (PD.FORM.089) — извлекать все cp.* / bh.* / методы
#   2. Сканировать CURRICULUM_PATH/specs/v4-reference/*.md — собирать все cp.* / bh.* ссылки
#   3. Находить mismatch (cp в curriculum, которых нет в Pack; cp в Pack, не используемые в curriculum)
#   4. Возвращать структурированный JSON drift_count + items
#
# Stub возвращает фиксированный отчёт с drift_count=1 для smoke-test workflow.

PACK_HASH=$(sha256sum "$PACK_PATH" 2>/dev/null | cut -c1-8 || shasum -a 256 "$PACK_PATH" | cut -c1-8)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ $VERBOSE -eq 1 ]]; then
    echo "[stub-pack-drift] pack=$PACK_PATH hash=$PACK_HASH curriculum=$CURRICULUM_PATH ts=$TIMESTAMP" >&2
fi

# Output: JSON для CI parsing
cat <<EOF
{
  "tool": "stub-pack-drift",
  "version": "0.1.0-stub",
  "timestamp": "$TIMESTAMP",
  "pack_file": "$PACK_PATH",
  "pack_hash": "$PACK_HASH",
  "curriculum_path": "$CURRICULUM_PATH",
  "drift_count": 1,
  "items": [
    {
      "type": "stub",
      "severity": "info",
      "location": "$PACK_PATH",
      "message": "Stub реализация — настоящий детектор появится в WP-321 (v4-lint pack-drift). Этот placeholder подтверждает, что Pack-watcher pipeline работает end-to-end."
    }
  ]
}
EOF

exit 0
