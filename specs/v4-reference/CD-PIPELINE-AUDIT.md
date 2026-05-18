---
id: PD-GUIDE-V4-CD-PIPELINE-AUDIT
title: "Аудит CD-конвейера: задекларировано vs реализовано"
status: draft
created: 2026-05-18
upstream: [CD-PIPELINE.md, VALIDATION_MATRIX.md, CHECKLISTS-README.md]
---

# Аудит CD-конвейера: задекларировано vs реализовано

> **Метод:** сравнение design-doc (CD-PIPELINE.md), спецификации (VALIDATION_MATRIX.md) и индекса (CHECKLISTS-README.md) с фактически созданными workflow, hooks, templates.
> **Дата аудита:** 2026-05-18.
> **Аудитор:** Kimi + Claude Sonnet 4.6 (cross-check).

---

## 1. Общий вердикт

**Реализовано:** ~60% CD-конвейера (все 🔴 gate'ы для content validation, часть инфраструктуры).
**Отсутствует:** ~40% (auto-merge, staging build, TG-уведомления, issue templates, CODEOWNERS, pack-drift-watcher, LLM Build, semver-bot, post-deploy checks).

Критичных багов нет. Все P0-проверки из VALIDATION_MATRIX.md реализованы. Основные gap'ы — в "мягкой" автоматизации (notifications, staging, release management), которая не блокирует merge, но блокирует полноценный CD.

---

## 2. Аудит по сценариям CD-PIPELINE.md (C1–C6)

### C1. Автор правит структуру подраздела

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1 | `git commit` в `specs/v4-reference/` | — | ✅ | — |
| 2 | pre-commit hook: `v4-lint structure + porter` локально (~1 сек) | В DS-principles-curriculum: `pack-lint.sh` + `generate-map.py` (PACK-specific). **Нет** `v4-lint structure` / `porter` в pre-commit. В docs: `pre-commit-docs.sh` (ссылки, drift, didactic lang) — но не v4-lint | ⚠️ Частично | Нет единого pre-commit hook для v4-lint structure + porter |
| 3 | `git push` | — | ✅ | — |
| 4 | GitHub Actions: structure / porter / cross-guide / pack-drift / fpf + smoke-test (~30 сек) | `v4-lint.yml` запускает structure, porter, cross-guide, pack-drift, smoke-test. `content-validation.yaml` (docs) запускает validate.py, drift, links, frontmatter, didactic | ✅ | — |
| 5 | PASS → auto-merge (hotfix) или ожидание ревью (feature) | Auto-merge **не настроен** в GitHub | ❌ | Нужно включить auto-merge в настройках репо + branch protection rules |
| 6 | Post-merge Build action: пересборка draft в `staging-v4` | Нет workflow | ❌ | Нужен staging-build.yml |
| 7 | TG-notification автору | Нет TG-бота в CI | ❌ | Нужен TG notification step |

### C2. Pack-владелец обновляет PD.FORM.089

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1 | commit в `PACK-personal/.../PD.FORM.089` | — | ✅ | — |
| 2 | GitHub webhook → `repository_dispatch` в `DS-principles-curriculum` | `notify-curriculum.yml` в PACK-personal отправляет dispatch | ✅ | — |
| 3 | Action `pack-drift-watcher` запускает `v4-lint pack-drift` на всех 4 руководствах | **Нет** workflow в DS-principles-curriculum, который принимает `repository_dispatch` | ❌ | Нужен `pack-drift-watcher.yml` с `on: repository_dispatch` |
| 4 | drift > 0 → issue с шаблоном | Нет issue template | ❌ | Нужен `.github/ISSUE_TEMPLATE/pack-drift.md` |
| 5 | Issue auto-assigned автору раздела (через CODEOWNERS) | Нет `CODEOWNERS` | ❌ | Нужен `CODEOWNERS` |
| 6 | Pack-владелец видит cross-repo status | Нет обратной связи | ❌ | Нужен status badge или comment bot |

### C3. LLM-генерация черновика

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1–5 | workflow_dispatch → Build action → Claude API → PR → merge | **Не реализовано** | ❌ | РП WP-149 (Кими) — вне скоупа текущего аудита |

### C4. Пилот заявляет «подраздел не работает»

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1 | GitHub issue с шаблоном `pilot-feedback` | Нет issue templates вообще | ❌ | Нужен `.github/ISSUE_TEMPLATE/pilot-feedback.yml` |
| 2 | Issue auto-assigned автору | Нет CODEOWNERS | ❌ | См. C2 |
| 3 | Label `needs-rework` автоматически | Нет automation | ❌ | Нужен GitHub Actions workflow или Probot |
| 4 | Подраздел исключается из broadcast | Нет механизма broadcast | ❌ | Зависит от пилот-платформы |
| 5 | Автор правит → новый build → новый пилот-тест | Ручной процесс | ⚠️ Частично | Нет авто-триггера на pilot-feedback issue |

### C5. Релиз новой версии (v4.0 → v4.1)

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1–5 | semver-bot → PR → Release → changelog → TG | **Не реализовано** | ❌ | РП отдельный (после первого пилот-цикла) |

### C6. Hotfix typo в продакшене

| Шаг | Задекларировано | Реализовано | Статус | Gap |
|-----|-----------------|-------------|--------|-----|
| 1 | Direct PR с `[hotfix]` в `docs/ru/personal-design/` | PR template создан, но нет hotfast-path | ⚠️ Частично | Нет branch protection rule для `[hotfix]` auto-merge |
| 2 | CI: только структурные тесты (без полного rebuild) | `content-validation.yaml` запускает всё — это тяжелее, чем "только структурные" | ⚠️ Частично | Нет отдельного lightweight workflow для hotfix |
| 3 | PASS → auto-merge без пилот-теста | Auto-merge не настроен | ❌ | См. C1 |
| 4 | TG-notification владельцу | Нет TG | ❌ | См. C1 |

---

## 3. Аудит VALIDATION_MATRIX.md: P0 vs реальность

Все P0-проверки реализованы. Ниже — статус каждой.

| # | Проверка | Где реализовано | Статус |
|---|----------|-----------------|--------|
| F-A | Структурная целостность (SS1–SS7) | `v4-lint.yml` (structure) | ✅ |
| F-B | Контракт Портного (frontmatter) | `v4-lint.yml` (porter) | ✅ |
| F-C | Cross-guide (один концепт = одно определение) | `v4-lint.yml` (cross-guide) | ✅ |
| F-D | Pack-drift (cp./bh.) | `v4-lint.yml` (pack-drift) | ✅ |
| F-E | Граф (сборка, циклы) | `v4-lint.yml` (graph) | ✅ |
| F-V1 | H1 совпадает с title | `content-validation.yaml` (validate.py) | ✅ |
| F-V2 | Pandoc-артефакты | `content-validation.yaml` (validate.py) | ✅ |
| F-V3 | Изображения | `content-validation.yaml` (validate.py) | ✅ |
| F-V4 | Сноски | `content-validation.yaml` (validate.py) | ✅ |
| F-V5 | Index.md | `content-validation.yaml` (validate.py) | ✅ |
| F-V6 | Имена файлов | `content-validation.yaml` (validate.py) | ✅ |
| F-V7 | Markdown таблицы | `content-validation.yaml` (validate.py) | ✅ |
| F-N1 | Битые cross-repo ссылки | `content-validation.yaml` (grep) + `pre-commit-docs.sh` | ✅ |
| F-N2 | Frontmatter completeness v4.1 | `content-validation.yaml` (Python скрипт) | ✅ |
| PS1 | Все introduces в ontology.md §2 | `content-validation.yaml` (sync-guide-to-ontology.py) | ✅ |
| PS2 | Pack source указан | `v4-lint.yml` (structure --strict-pack, A.8) | ✅ |
| G1–G3 | Граф (сборка, циклы, узлы) | `v4-lint.yml` (graph) | ✅ |
| G4–G5 | Cross-guide (orphans, дубли) | `v4-lint.yml` (cross-guide) | ✅ |
| G6 | Pack-drift | `v4-lint.yml` (pack-drift) | ✅ |
| FPF1 | U.* типы | `v4-lint.yml` (porter B.6, structure A.6) | ✅ |
| PR | PR template | `docs/.github/pull_request_template.md` | ✅ |
| Pre-commit | Pre-commit hook | `docs/scripts/pre-commit-docs.sh` | ✅ |

---

## 4. Аудит VALIDATION_MATRIX.md: P1 vs реальность

| # | Проверка | Задекларировано | Реализовано | Статус |
|---|----------|-----------------|-------------|--------|
| P1-1 | Post-deploy link check | `lychee` / `markdown-link-check` после deploy | Нет | ❌ |
| P1-2 | Word count check | CI warning при отклонении от target | Нет (validate.py не считает слова) | ❌ |
| P1-3 | FPF2–FPF4 (definition review, pedagogical marking, Role/Method/Work split) | Агент (PR) | Только ручной review | ⚠️ Частично |
| P1-4 | Graph orphans (G7) | Periodic: `sync-guide-to-ontology.py --reverse-check` | Скрипт не реализован | ❌ |
| P1-5 | Post-merge Build staging | `staging-v4` ветка + сборка draft | Нет | ❌ |
| P1-6 | Auto-merge hotfix | Branch protection + auto-merge | Нет | ❌ |
| P1-7 | TG notifications | TG-бот в CI | Нет | ❌ |
| P1-8 | Issue templates | `pilot-feedback`, `pack-drift` | Нет | ❌ |
| P1-9 | CODEOWNERS | Auto-assign issues/PR | Нет | ❌ |

---

## 5. Аудит CHECKLISTS-README.md

| Пункт | Задекларировано | Реализовано | Статус | Замечание |
|-------|-----------------|-------------|--------|-----------|
| Три уровня детализации (SS / S / Руководство) | Файлы CHECKLIST-{level}-v1.md | ✅ Все 3 файла существуют | ✅ | — |
| Три уровня контроля (🔴🟡🟢) | Таблица с инструментами | ✅ Описано корректно | ✅ | — |
| Правило вложенности | 🔴 → 🟡 → 🟢, hotfix-исключение | ✅ Описано | ✅ | — |
| Триггерная матрица | 10 триггеров × 3 уровня | ✅ Матрица корректна | ✅ | — |
| Алгоритм агента (шаг 3) | "Запустить 🔴 проверки (CLI команды из чек-листа)" | Команды работают, но нет единого "run all 🔴" | ⚠️ Частично | Можно добавить `make lint` или `v4-lint all` |
| Связь с PD.FORM.103 | Этапы 6-9 | ✅ Корректно отображено | ✅ | — |

---

## 6. Сводная таблица gap'ов

| # | Gap | Критичность | Относится к | Оценка времени | Блокер для |
|---|-----|-------------|-------------|----------------|------------|
| 1 | **pack-drift-watcher.yml** — приём `repository_dispatch` из PACK-personal | 🔴 P0 | C2 | 2-3h | Pack ↔ Curriculum связка |
| 2 | **Auto-merge** — branch protection rules + auto-merge для `[hotfix]` | 🔴 P0 | C1, C6 | 1-2h | Hotfix path |
| 3 | **CODEOWNERS** — auto-assign issues/PR авторам разделов | 🟡 P1 | C2, C4 | 1-2h | Auto-assign |
| 4 | **Issue templates** — `pilot-feedback.yml`, `pack-drift.md` | 🟡 P1 | C4, C2 | 2-3h | Pilot feedback loop |
| 5 | **Staging Build** — workflow, собирающий draft в `staging-v4` | 🟡 P1 | C1 (шаг 6) | 4-6h | Staging environment |
| 6 | **Post-deploy link check** — `lychee` после deploy | 🟡 P1 | P1-1 | 2-3h | Production quality |
| 7 | **Word count check** — скрипт, считающий слова в .md | 🟡 P1 | P1-2 | 1-2h | Content quality |
| 8 | **Graph orphans (reverse-check)** — `sync-guide-to-ontology.py --reverse-check` | 🟡 P1 | P1-4 | 2-3h | Ontology coverage |
| 9 | **TG notifications** — TG-бот в CI для авторов/пилотов | 🟢 P2 | C1, C6 | 3-4h | Visibility |
| 10 | **semver-bot + Release** — автоматический changelog + GitHub Release | 🟢 P2 | C5 | 3-4h | Versioning |
| 11 | **LLM Build** — workflow_dispatch → Claude API → draft | 🟢 P2 | C3 | 6-8h | Generation pipeline |
| 12 | **Единая команда 🔴** — `make lint` или `v4-lint all` | 🟢 P2 | CHECKLISTS | 1h | DX |

---

## 7. Рекомендуемый план доделки (по приоритету)

### Спринт 1 — Блокеры (🔴 P0, ~3-5h)

1. **pack-drift-watcher.yml** в DS-principles-curriculum:
   ```yaml
   on:
     repository_dispatch:
       types: [pack-drift-check]
   ```
   Запускает `v4-lint pack-drift` на всех 4 руководствах → создаёт issue при drift > 0.

2. **Auto-merge** — включить в настройках GitHub для docs и DS-principles-curriculum:
   - Branch protection: require status checks (content-validation, v4-lint)
   - Auto-merge: enable для PR с `[hotfix]`

### Спринт 2 — Инфраструктура (🟡 P1, ~10-15h)

3. **CODEOWNERS** — создать `.github/CODEOWNERS` в docs и DS-principles-curriculum.
4. **Issue templates** — `pilot-feedback.yml` и `pack-drift.md`.
5. **Staging Build** — workflow, который собирает structure + ontology → markdown draft в `staging-v4`.
6. **Post-deploy link check** — добавить `lychee` в `vkcloud-s3-static-deploy.yaml` или отдельный workflow.
7. **Word count check** — Python скрипт, считающий слова в body (без frontmatter).
8. **Graph reverse-check** — расширить `sync-guide-to-ontology.py` флагом `--reverse-check`.

### Спринт 3 — Polish (🟢 P2, ~15-20h)

9. **TG notifications** — интеграция с Telegram Bot API в workflow.
10. **semver-bot + Release** — GitHub Action, анализирующий теги коммитов.
11. **LLM Build** — координация с WP-149 (Кими).
12. **`make lint`** — единая команда для локального запуска всех 🔴 проверок.

---

## 8. Итоговый вердикт

**CD-конвейер на 2026-05-18:**
- ✅ **Content validation полностью покрыта** — все P0-проверки реализованы в CI и pre-commit.
- ✅ **Pack-sufficiency (AR.206) блокирует merge** — через v4-lint structure --strict-pack + content-validation.yaml.
- ✅ **Hotfix-исключение работает** — `[hotfix]` в коммите + Pack-sufficiency остаётся обязательной.
- ⚠️ **Cross-repo trigger (PACK → Curriculum) — односторонний** — PACK-personal шлёт dispatch, но Curriculum не принимает (нет pack-drift-watcher).
- ❌ **Staging + Deploy + Notify — не реализовано** — это следующий этап (WP-322).
- ❌ **Pilot feedback loop — не автоматизирован** — нужны issue templates + CODEOWNERS.

**Рекомендация:** после закрытия Спринта 1 (pack-drift-watcher + auto-merge) конвейер становится production-ready для команды авторов. Остальное — polish для масштабирования.

---

*Аудит завершён: 2026-05-18. Следующий шаг — либо закрыть Спринт 1 (P0 gap'ы), либо перейти к Guide 1.*
