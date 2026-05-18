#!/usr/bin/env bash
# pre-commit hook: запускает v4-lint structure + porter на staged файлах.
# Установка: ln -s ../../tools/pre-commit-v4-lint.sh .git/hooks/pre-commit
#
# Проверяет:
#   1. Структурные гайды в specs/v4-reference/ — structure + porter

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LINT="$REPO_ROOT/tools/v4-lint.py"

if [[ ! -f "$LINT" ]]; then
  echo "v4-lint: $LINT не найден — пропускаю pre-commit"
  exit 0
fi

STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep -E '^specs/v4-reference/0[0-9]-structure-guide-[0-9]+\.md$' || true)

if [[ -z "$STAGED" ]]; then
  exit 0
fi

echo "v4-lint: проверяю staged файлы..."
echo "$STAGED" | sed 's/^/  /'

FAILED=0

echo ""
echo "=== structure ==="
if ! python3 "$LINT" structure $STAGED; then
  FAILED=1
fi

echo ""
echo "=== porter ==="
if ! python3 "$LINT" porter $STAGED; then
  FAILED=1
fi

if [[ "$FAILED" -ne 0 ]]; then
  echo ""
  echo "❌ v4-lint: pre-commit failed. Исправь ошибки или используй --no-verify (не рекомендуется)."
  exit 1
fi

echo ""
echo "✅ v4-lint: pre-commit passed."
exit 0
