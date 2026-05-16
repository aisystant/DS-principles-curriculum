# tools/ — Валидаторы конвейера v4

> **Контракт инструмента:** [`~/IWE/DS-my-strategy/inbox/WP-321-v4-lint-validators.md`](../../../DS-my-strategy/inbox/WP-321-v4-lint-validators.md)
> **Этапы из WRITING-PIPELINE.md:** 2 (structure), 7 (FPF автоматизируемая часть), 8 (porter), 10 (cross-guide), 14 (pack-drift)

## v4-lint.py — единый CLI с 5 подкомандами

Python 3.11+, только stdlib (без внешних зависимостей).

### Подкоманды

| Команда | Этап | Что проверяет |
|---------|------|---------------|
| `structure` | 2, 7 | Синтаксис structure-guide-N.md: численная сортировка S1-S10, пропуски SS, омонимы, валидный формат «Понятия:». FPF: A.7 (кейсы не в `вводится`), A.10 (Pack source — WARN), A.11 (≤3 «вводится» — WARN), тройка идентификации (имя + parent U.* + Pack source). Маркеры из словаря и формат строк обязательны (FAIL) |
| `porter` | 8 | Frontmatter подразделов готов для алгоритма Портного: `subsection_id`, `cp_check`, `bh_check`, `mastery_node` ∈ {мыслительное/саморазвитие/iwe}, `stage_relevant` ⊆ [1-5], `can_do` начинается с «Могу», `introduces` без `U.*` префикса. A.1.1 Bounded Context: `mastery_node: [iwe]` запрещён в руководствах 1-2 |
| `cross-guide` | 10 | Одно понятие = одно определение во всех 4 руководствах. Понятие в `используется` имеет соответствующее `вводится` |
| `pack-drift` | 14 | Упоминания `cp.*` / `bh.*` в текстах и frontmatter соответствуют актуальной `PD.FORM.089-learner-rcs.md` |
| `graph build` | 5.3 (06-concept-graph) | Собирает концепт-граф из подразделов: узлы = `вводится`, рёбра = `используется`/`противопоставлен`/`сослан`. Выводит JSON + Graphviz DOT. Заменяет упомянутый, но не реализованный `tools/build-structure-overview.py` |
| `graph diff` | maintenance | Сравнивает два JSON-снимка графа: добавленные/удалённые узлы, изменённые `parent`/`pack_source`/`subsection_id`. Exit 1 если есть изменения (полезно для CI «нет дрейфа?») |

### Использование

```bash
# Все подразделы v4-reference/
python3 tools/v4-lint.py structure   specs/v4-reference/
python3 tools/v4-lint.py porter      specs/v4-reference/
python3 tools/v4-lint.py cross-guide specs/v4-reference/

# pack-drift требует путь к актуальной FORM.089
python3 tools/v4-lint.py pack-drift specs/v4-reference/ \
  --pack ../PACK-personal/pack/personal-development/02-domain-entities/formalizations/PD.FORM.089-learner-rcs.md

# Сборка концепт-графа
python3 tools/v4-lint.py graph build specs/v4-reference/ \
  --out-json /tmp/graph.json --out-dot /tmp/graph.dot

# Диагностика дрейфа графа
python3 tools/v4-lint.py graph diff /tmp/graph-before.json /tmp/graph-after.json

# Один файл
python3 tools/v4-lint.py porter specs/v4-reference/01-structure-guide-1.md
```

### Exit codes

| Код | Значение |
|-----|----------|
| 0 | PASS — ошибок нет (могут быть warnings) |
| 1 | FAIL — найдены errors |
| 2 | INTERNAL_ERROR — баг валидатора, traceback в stderr |

Warning ≠ FAIL. Warning означает «подозрительное место, проверь вручную», но коммит не блокируется.

## smoke-test.sh

```bash
bash tools/smoke-test.sh
```

Запускает 5 подкоманд на `fixtures/valid/` (ожидание exit=0) и `fixtures/broken/` (ожидание exit=1 + ожидаемые сообщения). Должно выводить `43 pass, 0 fail`.

Для pack-drift нужен реальный Pack-файл (по умолчанию ищется в `~/IWE/PACK-personal/...`). Переопределить путь:

```bash
PACK_FORM089=/path/to/PD.FORM.089-learner-rcs.md bash tools/smoke-test.sh
```

## pre-commit hook

`pre-commit-v4-lint.sh` устанавливается в `.git/hooks/pre-commit` (или вызывается из существующего hook). На каждый коммит проверяет staged файлы `specs/v4-reference/*.md` через `structure` + `porter`. Падающий FAIL блокирует коммит.

Установка:

```bash
ln -s ../../tools/pre-commit-v4-lint.sh .git/hooks/pre-commit
chmod +x tools/pre-commit-v4-lint.sh
```

## CI workflow

`.github/workflows/v4-lint.yml` запускает все 4 подкоманды на PR, затрагивающих `specs/v4-reference/`. На FAIL в любом из 4 — PR помечается красным.

## Архитектура

Один файл `v4-lint.py` (~470 строк). Общие функции:
- `parse_structure_file(path)` → `list[Section]` с подразделами и концептами
- `parse_yaml_block(text)` → `dict` (минимальный YAML-парсер для inline-блоков)
- `parse_pack_form089(path)` → `dict[cp|bh, set[str]]`
- `report(findings, label)` → exit code

Каждая подкоманда — функция `cmd_<name>(args)`, использующая общий парсер. Добавление нового валидатора = ~50 строк + новый subparser.

## Расширение

Новая подкоманда:

```python
def cmd_<name>(args):
    findings = []
    # ...проверки...
    return report(findings, label="<name>")

# В build_parser():
p_new = sub.add_parser("<name>", help="...")
p_new.add_argument("paths", nargs="+")
p_new.set_defaults(func=cmd_<name>)
```

Новый словарь констант (валидные значения, шаблоны) — добавить в начало файла.

## Известные ограничения

- YAML-парсер минимальный: понимает `key: value`, `key: [item, item]`, multi-line `key:` + `  - item`. Не поддерживает вложенные объекты, anchors, tags.
- Парсер «Понятия:» работает на строках вида `- маркер: имя → U.Type` или `- маркер: имя — см. X.SY.SSZ`. Имя до первого `→` / `—` / `(` / `см.`.
- `cross-guide` сравнивает понятия по точному совпадению имени. Регистр и пробелы важны — «Созидатель» ≠ «созидатель».
- `pack-drift` требует явный `--pack <путь>`. Семенной словарь как fallback убран намеренно (избегаем silent stale-data при rotate Pack).

## История изменений

| Версия | Дата | Что |
|--------|------|-----|
| v1 | 2026-05-16 | Первая версия (WP-321 commit `f3ff233`): 4 подкоманды, smoke 17/17, pre-commit + CI |
| v1.1 | 2026-05-16 | Ф9 follow-up по independent review: silent pass на несуществующих путях, multi-line YAML, парсер `сослан`, обязательный `--pack`, smoke 28/28 |
| v2 | 2026-05-16 | Ф10: FPF-проверки (A.7/A.10/A.11/A.1.1 + тройка идентификации), strict markers (unknown/malformed → FAIL), новая подкоманда `graph` (build/diff). smoke 43/43 |
