#!/usr/bin/env bash
# Smoke-test для v4-lint.py.
# Покрывает: 4 подкоманды × {valid, broken} + edge-кейсы (пустой путь, missing Pack, broken-order).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LINT="$SCRIPT_DIR/v4-lint.py"
VALID="$SCRIPT_DIR/fixtures/valid"
BROKEN="$SCRIPT_DIR/fixtures/broken"
BROKEN_ORDER="$SCRIPT_DIR/fixtures/broken-order"
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
    echo "  ❌ $label  (не найдено: $pattern)"
    cat /tmp/v4lint-smoke.out
    FAIL=$((FAIL + 1))
  fi
}

# ============================================================================
# structure
# ============================================================================
echo "=== structure: valid → exit 0 ==="
assert_exit 0 "structure(valid)" python3 "$LINT" structure "$VALID"

echo "=== structure: broken → exit 1 + ожидаемые finding'и ==="
assert_exit 1 "structure(broken)" python3 "$LINT" structure "$BROKEN"
assert_grep "пропущены SS-номера" "пропуск SS обнаружен"
assert_grep "омоним" "омоним обнаружен"
assert_grep "начинается с" "имя в скобках обнаружено"

echo "=== structure: broken-order → exit 1 (S1, S10, S2 не отсортирован) ==="
assert_exit 1 "structure(broken-order)" python3 "$LINT" structure "$BROKEN_ORDER"
assert_grep "не отсортированы численно" "нарушение S1/S10/S2 обнаружено"

# ============================================================================
# porter
# ============================================================================
echo "=== porter: valid → exit 0 ==="
assert_exit 0 "porter(valid)" python3 "$LINT" porter "$VALID"

echo "=== porter: broken → exit 1 + ожидаемые finding'и ==="
assert_exit 1 "porter(broken)" python3 "$LINT" porter "$BROKEN"
assert_grep "mastery_node «несуществующий-узел»" "невалидный mastery_node"
assert_grep "stage_relevant" "невалидный stage"
assert_grep "U.\*-тип" "introduces содержит U.* префикс"
assert_grep "can_do элемент не начинается с «Могу»" "can_do без «Могу» (multi-line YAML работает)"
assert_grep "prerequisite.*не найден" "prereq на несуществующий ID"

# ============================================================================
# cross-guide
# ============================================================================
echo "=== cross-guide: valid → exit 0 ==="
assert_exit 0 "cross-guide(valid)" python3 "$LINT" cross-guide "$VALID"

echo "=== cross-guide: broken → exit 1 ==="
assert_exit 1 "cross-guide(broken)" python3 "$LINT" cross-guide "$BROKEN"
assert_grep "Понятие-Х" "двойное введение Понятия-Х"
assert_grep "Сирота-без-определения" "orphan-reference обнаружен"

# ============================================================================
# pack-drift
# ============================================================================
if [[ -f "$PACK_FORM089" ]]; then
  echo "=== pack-drift: valid → exit 0 ==="
  assert_exit 0 "pack-drift(valid)" python3 "$LINT" pack-drift "$VALID" --pack "$PACK_FORM089"

  echo "=== pack-drift: broken → exit 1 (cp.unknownslot / bh.fakemetric) ==="
  assert_exit 1 "pack-drift(broken)" python3 "$LINT" pack-drift "$BROKEN" --pack "$PACK_FORM089"
  assert_grep "cp.unknownslot" "неизвестный cp обнаружен"
  assert_grep "bh.fakemetric" "неизвестный bh обнаружен"
else
  echo "  ⏭  pack-drift: $PACK_FORM089 не найден — пропускаю"
fi

# ============================================================================
# Edge-кейсы
# ============================================================================
echo "=== edge: несуществующий путь → exit 1 (НЕ silent pass) ==="
assert_exit 1 "edge(nonexistent path)" python3 "$LINT" structure "/tmp/v4lint-does-not-exist-$$"
assert_grep "путь не существует" "несуществующий путь явно отловлен"

echo "=== edge: pack-drift без --pack → exit 1 ==="
assert_exit 1 "edge(no --pack)" python3 "$LINT" pack-drift "$VALID"
assert_grep "требует --pack" "отсутствие --pack явно отловлено"

echo "=== edge: pack-drift с несуществующим --pack → exit 1 ==="
assert_exit 1 "edge(missing pack)" python3 "$LINT" pack-drift "$VALID" --pack "/tmp/no-such-pack-$$"
assert_grep "Pack-файл не найден" "missing --pack явно отловлен"

echo ""
echo "=== Итог: $PASS pass, $FAIL fail ==="
exit "$FAIL"
