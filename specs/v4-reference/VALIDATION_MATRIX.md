---
id: PD-GUIDE-V4-VALIDATION-MATRIX
title: "Матрица валидации контента v4 — согласование с конвейером"
status: draft
created: 2026-05-18
upstream: [CHECKLIST-subsection-v1, CHECKLIST-section-v1, CHECKLIST-guide-v1, CD-PIPELINE.md, v4-lint.py, PD.FORM.103, AR.206]
applies_to: все изменения в specs/v4-reference/ и aisystant/docs
---

# Матрица валидации контента v4

> **Назначение:** согласовать 7 измерений проверок с существующей системой 🔴🟡🟢 + v4-lint.py + CD-PIPELINE.md. Исправляет первую версию (docs/.github/VALIDATION_MATRIX.md), которая нарушила Routing Gate (не тот репо), устарела по структуре v4.1 и дублировала существующие инструменты.
>
> **Ключевое отличие от v1:** явный mapping на 🔴🟡🟢, dedup с v4-lint.py, Pack-sufficiency как P0-инвариант, hotfix-исключение, owner/trigger для Periodic.

---

## 1. Архитектура: 7 измерений × 3 уровня контроля

| Измерение | Вопрос | 🔴 Машина | 🟡 Агент | 🟢 Пилот |
|-----------|--------|:---------:|:--------:|:--------:|
| **Форма** | Правильно ли оформлено? | v4-lint structure + porter, validate.py | — | — |
| **Содержание** | Корректны ли определения, примеры, мемы? | word count, didactic-lang grep | expert review | восприятие, аналогия |
| **Pack-sufficiency (AR.206)** | Все понятия закрыты Pack? | v4-lint structure --strict-pack | — | — |
| **Граф знаний** | Связи построены, нет циклов? | v4-lint graph | анализ orphans | — |
| **Cross-guide** | Нет дублей и orphan-ссылок? | v4-lint cross-guide | — | — |
| **Pack-drift** | cp.*/bh.* актуальны? | v4-lint pack-drift | — | — |
| **FPF** | Не противоречит FPF? | U.* type check | definition review vs FPF-Spec | — |

**Правило вложенности (из CHECKLISTS-README.md):** 🔴 PASS обязателен перед 🟡. 🟡 PASS обязателен перед 🟢. Hotfix-исключение: `[hotfix]` в коммите = только 🔴 на затронутом уровне (Pack-sufficiency остаётся обязательной даже для hotfix).

---

## 2. Измерение: Форма

> **Вопрос:** Правильно ли оформлен подраздел? Нет ли технических артефактов, пропущенных блоков, битых ссылок?

### 2.1. Что уже покрыто v4-lint.py (🔴)

| # | Проверка | Команда | Статус |
|---|----------|---------|--------|
| F-A | Структурная целостность (SS1–SS7, сортировка, омонимы, unknown маркеры) | `v4-lint structure` | ✅ Реализовано |
| F-B | Контракт Портного (frontmatter: subsection_id, title, mastery_node, stage_relevant, introduces, uses, prerequisites, can_do, cp_check, bh_check, meta-поля) | `v4-lint porter` | ✅ Реализовано |
| F-C | Кросс-руководная согласованность (один концепт = одно определение, orphan references, дубли узлов) | `v4-lint cross-guide` | ✅ Реализовано |
| F-D | Pack-drift (cp.*/bh.* актуальны, Pack source указан) | `v4-lint pack-drift` | ✅ Реализовано |
| F-E | Граф понятий (сборка, циклы, все introduces в графе) | `v4-lint graph` | ✅ Реализовано |
| F-F | Git-целостность (status чистый, commit message с WP-XXX или [v4]) | ручной / pre-commit | ⚠️ Частично |

### 2.2. Что НЕ покрыто v4-lint.py — покрывает validate.py (docs/scripts/convert_word/) (🔴)

| # | Проверка | Критерий | Инструмент | Где внедрять |
|---|----------|----------|------------|--------------|
| F-V1 | H1 совпадает с title | Заголовок после `---` = `title:` в frontmatter | `validate.py` правило 2 | CI docs |
| F-V2 | Pandoc-артефакты | Нет `{.underline}`, `{.mark}`, `---`, grid-таблиц | `validate.py` правило 9 | CI docs |
| F-V3 | Изображения | В `assets/`, имена `fig-XX`, файлы существуют | `validate.py` правило 6 | CI docs |
| F-V4 | Сноски | Каждая `[^N]` имеет определение `[^N]:` | `validate.py` правило 7 | CI docs |
| F-V5 | Index.md | Каждая папка-секция имеет `index.md` | `validate.py` правило 8 | CI docs |
| F-V6 | Имена файлов | Только латиница, kebab-case, префикс `NN-` | `validate.py` правило 5, 10 | CI docs |
| F-V7 | Markdown таблицы | Только pipe-формат, нет simple/grid таблиц | `validate.py` правило 11, 12 | CI docs |

### 2.3. Что НЕ покрыто ни v4-lint, ни validate.py (🔴)

| # | Проверка | Критерий | Инструмент | Где внедрять |
|---|----------|----------|------------|--------------|
| F-N1 | Битые cross-repo ссылки | Нет `../../../PACK-personal/ontology.md#*` в тексте руководств | `grep` / `lychee` | pre-commit + CI |
| F-N2 | Frontmatter completeness v4.1 | `format_version`, `pack_refs`, `time_reading`, `time_practice`, `word_count_target`, `status` присутствуют | `sync-guide-to-ontology.py` + скрипт | pre-commit + CI |

### 2.4. Обязательные блоки v4.1 (актуализировано)

> **Исключение:** auxiliary-подразделы (.08–.11) освобождены от полного набора.

| Блок | Наличие | Проверяется |
|------|---------|-------------|
| **Понятия этого раздела** | Обязателен | 🔴 v4-lint structure (A.5, A.6) |
| **Мем, который снимается** | Обязателен | 🟡 агент (семантика) |
| **Из Pack** | Обязателен | 🔴 v4-lint structure (A.8 — Pack source) |
| **Объяснение** | Обязателен | 🟡 агент |
| **Минимальный шаг** | Обязателен | 🟡 агент (выполнимость) |
| **Пример из жизни** | Обязателен | 🟡 агент |
| **Типичная ошибка** | Обязателен | 🟡 агент |
| **Степени мастерства** | Обязателен | 🔴 v4-lint structure (F.4.1 таблица, F.4.2 проверка себя) |
| **Проверка себя** | Обязателен | 🔴 v4-lint structure (F.4.2) |
| **На практике** | Обязателен | 🟡 агент |
| **См. также** | Обязателен | 🟡 агент (корректность ссылок) |
| **Что дальше** | Обязателен для SS < last | 🟡 агент |
| ~~Что узнаешь~~ | ~~Удалено в c73fa3f~~ | — |
| ~~Время как отдельный блок~~ | ~~Удалено в c73fa3f~~ | — |

**Примечание:** `time_reading` и `time_practice` перенесены в frontmatter (проверяется `v4-lint porter` B.9). `word_count_target` — тоже в frontmatter.

---

## 3. Измерение: Содержание

> **Вопрос:** Корректны ли определения, объяснения, примеры? Понятно ли читателю?

| # | Проверка | Критерий | Уровень | Инструмент | Gate |
|---|----------|----------|---------|------------|------|
| C1 | Определения понятий | Короткое определение + «≠» + пример из жизни | 🟡 | Агент (context isolation) | PR |
| C2 | Педагогическая ясность | Понятно целевой аудитории; FPF-термины только если это Pack | 🟡 | Агент | PR |
| C3 | Примеры | Каждый абстрактный тезис иллюстрирован | 🟡 | Агент | PR |
| C4 | Мемы | Реальное заблуждение, опровергаемое одним аргументом | 🟡 | Агент | PR |
| C5 | Минимальный шаг | Выполнимо за указанное время, не требует подготовки | 🟡 | Агент | PR |
| C6 | Степени мастерства | 4 ступени, критерии перехода наблюдаемы | 🟡 | Агент | PR |
| C7 | Word count | Целевой объём 500–1500 слов; ±20% = warning, ±50% = error | 🔴 | `wc` / скрипт | CI (warning) |
| C8 | Didactic language | Нет «шаг», «урок», «внедрить», «за N дней» (UB-1) | 🔴 | `grep` / pack-lint | CI |

---

## 4. Измерение: Pack-sufficiency (AR.206) — P0-инвариант

> **Вопрос:** Все понятия, введённые в подразделе, закрыты в Pack? Есть ли у каждого Pack-источник?
>
> **Статус:** блокирующий gate. Не проходит = не merge. Действует даже для `[hotfix]`.

| # | Проверка | Критерий | Уровень | Инструмент | Gate |
|---|----------|----------|---------|------------|------|
| PS1 | Все introduces в ontology.md §2 | Каждое понятие из `introduces` есть в `PACK-personal/ontology.md` §2 | 🔴 | `v4-lint structure --strict-pack` (A.8) | pre-commit + CI |
| PS2 | Pack source указан | Каждое «вводится» имеет источник `PD.FORM/METHOD/CAT.NNN` | 🔴 | `v4-lint structure --strict-pack` (A.8) | pre-commit + CI |
| PS3 | Обратное покрытие | Каждый термин ontology.md §2 используется минимум в одном подразделе (или помечен `reserved`) | 🔴 | `sync-guide-to-ontology.py --reverse-check` *(не реализован)* | Periodic |

**Связь с CHECKLIST-subsection-v1:** A.8 Evidence Graph (STRUCT-EVIDENCE) — severity FAIL, см. PD.FORM.103 Этап 3.5 + WRITING-PIPELINE §1.5.

**Связь с CD-PIPELINE:** DP.SC.curriculum-cd инвариант: «Ни один подраздел не попадает в docs/ru/personal-design/ без Pack-sufficiency».

---

## 5. Измерение: Граф знаний + Cross-guide + Pack-drift

> **Вопрос:** Связи между понятиями построены и непротиворечивы? Prerequisites → introduces образуют ациклический граф?

| # | Проверка | Критерий | Уровень | Инструмент | Gate |
|---|----------|----------|---------|------------|------|
| G1 | Граф собирается без ошибок | `v4-lint graph build` → exit 0 | 🔴 | `v4-lint graph` | CI |
| G2 | Нет циклов | Ациклический граф (DFS) | 🔴 | `v4-lint graph` | CI |
| G3 | Все introduces в графе | Каждое понятие из `introduces` — узел графа | 🔴 | `v4-lint graph` | CI |
| G4 | Нет orphan-references | `uses` ссылается на существующее `introduces` | 🔴 | `v4-lint cross-guide` (C.2) | CI |
| G5 | Нет дублей узлов | Одно понятие = одно определение в 4 руководствах | 🔴 | `v4-lint cross-guide` (C.1) | CI |
| G6 | Prerequisites реализуемы | Каждый `prerequisites` покрыт предыдущими подразделами | 🟡 | Агент (графовый анализ) | PR |
| G7 | Нет orphans (глобально) | Понятие введено, но нигде не используется | 🟡 | Агент + `sync-guide-to-ontology.py` | Periodic |

---

## 6. Измерение: FPF

> **Вопрос:** Определения и структура не противоречат FPF? Педагогические адаптации явно помечены?

| # | Проверка | Критерий | Уровень | Инструмент | Gate |
|---|----------|----------|---------|------------|------|
| FPF1 | U.* типы | Корректный родительский U.* тип из SPF для каждого термина | 🔴 | `v4-lint structure` (A.6 — тройка идентификации) + ручной | PR |
| FPF2 | Strict distinction | Определения содержат «≠» — защита от концептуальной путаницы | 🟡 | Агент | PR |
| FPF3 | Pedagogical marking | Если определение упрощено относительно FPF — есть пометка «педагогическая интерпретация» | 🟡 | Агент | PR |
| FPF4 | Role/Method/Work split | Не смешиваются роль (кто), метод (как), работа (что получилось) | 🟡 | Агент | PR |

---

## 7. Hotfix-исключение

> **Правило (из CHECKLIST-subsection-v1 и CD-PIPELINE):**
> - `[hotfix]` в коммите = только 🔴 на затронутом уровне (типично подраздел).
> - 🟡 и 🟢 пропускаются — не для исправления typo.
> - **Pack-sufficiency (PS1, PS2) остаётся обязательной даже для hotfix** — изменение понятия в hotfix требует Pack-источника.
> - Hotfix не применяется к структурным изменениям (новый SS, изменение порядка, добавление понятия).

| Тип изменения | 🔴 | 🟡 | 🟢 | Pack-sufficiency |
|---------------|:--:|:--:|:--:|:----------------:|
| Typo, punctuation | ✅ | ⏭️ | ⏭️ | ✅ |
| Форматирование (markdown) | ✅ | ⏭️ | ⏭️ | ✅ |
| Ссылка (не понятие) | ✅ | ⏭️ | ⏭️ | ✅ |
| Новое понятие в introduces | ✅ | ✅ | ⏭️ | ✅ (блокер) |
| Изменение определения | ✅ | ✅ | ⏭️ | ✅ (блокер) |
| Новый подраздел | ✅ | ✅ | ✅ | ✅ (блокер) |

---

## 8. Сводная матрица: что × где × кто

| Измерение / Подпункт | 🔴 Машина | 🟡 Агент | 🟢 Пилот | Periodic |
|----------------------|:---------:|:--------:|:--------:|:--------:|
| **Форма** | v4-lint structure, porter, graph, cross-guide, pack-drift; validate.py; grep links | — | — | — |
| **Pack-sufficiency** | v4-lint --strict-pack (A.8); ontology reverse-check | — | — | reverse-check |
| **Содержание** | word count; didactic-lang grep | expert review (Claude) | — | — |
| **Граф знаний** | v4-lint graph, cross-guide | анализ orphans | — | глобальный orphan audit |
| **Cross-guide** | v4-lint cross-guide | — | — | — |
| **Pack-drift** | v4-lint pack-drift | — | — | — |
| **FPF** | U.* check (v4-lint A.6) | definition review | — | — |

---

## 9. Periodic: owner + trigger + инструмент

| Периодичность | Что проверяем | Триггер | Owner | Инструмент | Результат |
|---------------|---------------|---------|-------|------------|-----------|
| **Еженедельно** (пн 09:00 UTC) | Cross-guide consistency + Pack-drift + broken links | CI cron | CI (авто) | `v4-lint cross-guide` + `v4-lint pack-drift` + `grep` | Issue при FAIL |
| **Ежемесячно** (1-й пн месяца) | Глобальный orphan audit + coverage reverse-check | CI cron + агент | Агент (Claude) | `v4-lint graph` + `sync-guide-to-ontology.py --reverse-check` | Отчёт + issue |
| **Ежеквартально** | Полный CHECKLIST-guide-v1.md | Ручной (пилот) | Пилот (методолог) | CHECKLIST-guide-v1.md | GitHub issue с результатами |
| **При изменении Pack** | Pack-drift по всем 4 руководствам | webhook (PACK-personal → curriculum) | CI (авто) | `v4-lint pack-drift` + `notify-curriculum.yml` | Auto-issue |

**Важно:** без триггера Periodic = «никогда». CI cron задаётся в `.github/workflows/v4-lint.yml` (дополнить `schedule:`). Ежемесячный агентский аудит — через `workflow_dispatch` с reminder в календаре пилота.

---

## 10. Инвентарь инструментов: dedup

| Инструмент | Что покрывает | Что НЕ покрывает | Статус | Рекомендация |
|------------|---------------|------------------|--------|--------------|
| **v4-lint.py** | 🔴 A–F из CHECKLIST-subsection (structure, porter, cross-guide, pack-drift, graph, git) | Markdown lint (pandoc-артефакты, сноски, изображения), битые ссылки | ✅ Работает | Дополнить CI |
| **validate.py** (docs/scripts/convert_word/) | Markdown lint (12 правил: frontmatter, H1, pandoc, таблицы, сноски, изображения, index.md, kebab-case) | v4-специфика (Pack source, graph, cross-guide) | ✅ Работает (локально) | Внедрить в CI |
| **sync-guide-to-ontology.py** | Drift guide ↔ ontology, frontmatter sync, synonym map | Pack source validation, graph cycles | ✅ Работает (локально) | Внедрить в CI; добавить `--reverse-check` |
| **check-pack-collisions.sh** | R4 ID коллизии в Pack-репо | — | ✅ Работает (CI + pre-commit) | Оставить как есть |
| **pack-lint.sh** | Pack структура (WP-242) | — | ✅ Работает (pre-commit) | Оставить как есть |
| **lychee / grep** | Битые ссылки | — | ❌ Нет | Добавить pre-commit + CI |

---

## 11. Чеклист для согласования

- [ ] Место файла — корректно (`DS-principles-curriculum/specs/v4-reference/`)
- [ ] F2 актуализирован (убраны «Что узнаешь» и «Время как блок»)
- [ ] Pack-sufficiency (AR.206) выделен как P0-инвариант
- [ ] Mapping на 🔴🟡🟢 явный и непротиворечив с CHECKLIST-subsection-v1
- [ ] Hotfix-исключение описано, Pack-sufficiency не пропускается
- [ ] Dedup с v4-lint.py выполнен (§10)
- [ ] Periodic: owner + trigger зафиксированы (§9)
- [ ] Следующий шаг: создать/обновить `v4-lint.yml` workflow + PR template + pre-commit hook

---

*Draft v2. 2026-05-18. Исправляет v1: routing gate, F2 устаревание, Pack-sufficiency отсутствие, 🔴🟡🟢 mapping, hotfix, dedup, Periodic owner.*
