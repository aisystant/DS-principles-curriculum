#!/usr/bin/env bash
# Smoke-test для v4-lint.py.
# Проверяет: на valid-фикстурах exit=0, на broken — exit=1 + ожидаемые findings.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LINT="$SCRIPT_DIR/v4-lint.py"
VALID="$SCRIPT_DIR/fixtures/valid"
BROKEN="$SCRIPT_DIR/fixtures/broken"
PACK_FORM089="${PACK_FORM089:-$HOME/IWE/PACK-personal/pack/personal-development/02-domain-entities/formalizations/PD.FORM.089-learner-rcs.md}"

PASS=0
FAIL=0

assert_exit() {
  local expected="$1"; shift
  local label="$1"; shift
  local actual
  "$@" >/tmp/v4lint-smoke.out 2>&1
  actual=$?
  if [[ "$actual" == "$expected" ]]; then
    echo "  ✅ $label  (exit=$actual)"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label  (exit=$actual, ожидалось $expected)"
    cat /tmp/v4lint-smoke.out
    FAIL=$((FAIL + 1))
  fi
}

assert_grep() {
  local pattern="$1"; shift
  local label="$1"; shift
  if grep -q -- "$pattern" /tmp/v4lint-smoke.out; then
    echo "  ✅ $label"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label  (не найдено в выводе: $pattern)"
    cat /tmp/v4lint-smoke.out
    FAIL=$((FAIL + 1))
  fi
}

echo "=== structure: valid → exit 0 ==="
assert_exit 0 "structure(valid)" python3 "$LINT" structure "$VALID"

echo "=== structure: broken → exit 1 + ожидаемые finding'и ==="
assert_exit 1 "structure(broken)" python3 "$LINT" structure "$BROKEN"
assert_grep "пропущены SS-номера" "пропуск SS обнаружен"
assert_grep "омоним" "омоним обнаружен"
assert_grep "начинается с" "имя в скобках обнаружено"

echo "=== porter: valid → exit 0 ==="
assert_exit 0 "porter(valid)" python3 "$LINT" porter "$VALID"

echo "=== porter: broken → exit 1 + ожидаемые finding'и ==="
assert_exit 1 "porter(broken)" python3 "$LINT" porter "$BROKEN"
assert_grep "mastery_node «несуществующий-узел»" "невалидный mastery_node"
assert_grep "stage_relevant" "невалидный stage"
assert_grep "U.\*-тип" "introduces содержит U.* префикс"

echo "=== cross-guide: valid → exit 0 ==="
assert_exit 0 "cross-guide(valid)" python3 "$LINT" cross-guide "$VALID"

echo "=== cross-guide: broken → exit 1 (двойное «вводится») ==="
assert_exit 1 "cross-guide(broken)" python3 "$LINT" cross-guide "$BROKEN"
assert_grep "Понятие-Х" "двойное введение Понятия-Х"

echo "=== pack-drift: valid → exit 0 ==="
if [[ -f "$PACK_FORM089" ]]; then
  assert_exit 0 "pack-drift(valid)" python3 "$LINT" pack-drift "$VALID" --pack "$PACK_FORM089"
else
  echo "  ⏭  pack-drift: $PACK_FORM089 не найден — пропускаю"
fi

echo "=== pack-drift: broken → exit 1 (cp.unknownslot / bh.fakemetric) ==="
if [[ -f "$PACK_FORM089" ]]; then
  assert_exit 1 "pack-drift(broken)" python3 "$LINT" pack-drift "$BROKEN" --pack "$PACK_FORM089"
  assert_grep "cp.unknownslot" "неизвестный cp обнаружен"
  assert_grep "bh.fakemetric" "неизвестный bh обнаружен"
fi

echo ""
echo "=== Итог: $PASS pass, $FAIL fail ==="
exit "$FAIL"
