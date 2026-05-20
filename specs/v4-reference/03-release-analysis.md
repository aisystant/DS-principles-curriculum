---
id: PD.GUIDE.3.RELEASE-ANALYSIS
title: "Анализ релизов FMT vs структура Guide 3"
status: draft
created: 2026-05-20
updated: 2026-05-20
related: [WP-322, WP-300, FMT-exocortex-template]
---

# Анализ релизов FMT vs структура Guide 3

## Цель

Проверить, отражены ли ключевые функции релизов FMT-exocortex-template (0.28.x–0.33.x) в структуре Руководства 3 «IWE: работа и развитие». Выявить пропуски и предложить корректировки структуры + pipeline (WP-322).

## Метод

1. Скан CHANGELOG FMT (релизы 0.28.0–0.33.0+, ~50 значимых фич).
2. Классификация каждой фичи по релевантности к Guide 3 (ось = IWE как среда/инфраструктура/культура).
3. Проверка наличия соответствующего понятия/подраздела в 03-structure-guide-3.md (S1–S9).
4. Категоризация пропусков: 🔴 критический (должен быть в Guide 3), 🟡 желательный (можно в другом руководстве), 🟢 операционный (не для руководства).

---

## Сводка по пропускам

| # | Фича релиза (FMT) | Версия | Где должно быть | Статус | Приоритет |
|---|-------------------|--------|-----------------|--------|-----------|
| R1 | **Agent Inbox / Диспетчеризация** (headless claude -p, cron, WP-324) | 0.32.0 | S4 (Агенты) или S7 | ❌ Отсутствует | 🔴 |
| R2 | **Generated runtime architecture** (build-runtime.sh, .iwe-runtime/) | 0.29.0 | S2 (Онтология) или S3 | ❌ Отсутствует | 🔴 |
| R3 | **Extensions / load-extensions.sh** (wildcard suffix loader, 13 EP) | 0.29.9 | S7 (Развитие среды) | ❌ Отсутствует | 🔴 |
| R4 | **iwe-audit.sh / iwe-drift.sh** (аудит + дрейф-детектор) | 0.28.12, 0.29.12 | S2.06–S2.07 (Дрейф) | ⚠️ Упомянуто абстрактно, конкретные скрипты — нет | 🔴 |
| R5 | **Agent Fault Profile** (учёт косяков агента, скрипты) | 0.31.0, 0.33.0 | S5 (14 элементов) или S8 | ❌ Отсутствует | 🔴 |
| R6 | **changelog automation** (semver-bot, changelog-append.sh) | 0.31.0–0.32.0 | S3 (Семейства документов) или S5 | ❌ Отсутствует | 🟡 |
| R7 | **Post-release audit** (adversarial audit workflow, 5 уровней) | 0.29.18 | S5.07 (ТО) или S7 | ❌ Отсутствует | 🟡 |
| R8 | **Integration Contract Validator** (8 detectors, Spec↔State) | 0.29.0+ | S3 (ADR) или S7 | ❌ Отсутствует | 🟡 |
| R9 | **template-sync.sh** (синхронизация авторского → FMT) | 0.29.28 | S3 (Drift) или S7 | ❌ Отсутствует | 🟡 |
| R10 | **Memory Lifecycle Protocol** (memory-validate, memory-bleed) | 0.29.21 | S3 (Pack) или S7 | ❌ Отсутствует | 🟡 |
| R11 | **iwe-trace-recorder** (WP-295, трассировка действий агента) | 0.33.0 | S9.04 (Трассировка) | ⚠️ Понятие «Трассировка» есть, конкретный инструмент — нет | 🟡 |
| R12 | **Promote-скрипты** (script/hook/skill-promote.sh, L1-flow) | 0.31.0 | S7 (Развитие среды) | ❌ Отсутствует | 🟡 |
| R13 | **Secret Drift Detector** (iwe-grep-secret.sh) | 0.31.0 | S8 (Аварии/безопасность) | ❌ Отсутствует | 🟢 |
| R14 | **Telegram reminders** (TG-уведомления, rule 8) | 0.31.0–0.32.0 | Вне Guide 3 (интеграция) | ❌ Отсутствует | 🟢 |
| R15 | **calendar / day-open + week-close skills** (server-calendar.sh) | 0.33.0 | S5 (ОРЗ) | ⚠️ ОРЗ есть, calendar-интеграция — нет | 🟢 |
| R16 | **week-draft-init.sh / week-draft-append.sh** | 0.30.0 | Вне Guide 3 (контент) | ❌ Отсутствует | 🟢 |
| R17 | **WP Sync Gate** (wp-sync-bundle.sh, wp-sync-actualizer) | 0.29.30 | Вне Guide 3 (операционно) | ❌ Отсутствует | 🟢 |
| R18 | **personal-guide-start / personal-guide-render** | 0.29.23 | Guide 2 (личное развитие) | ❌ Отсутствует | 🟢 |

**Итого:** 5 🔴 критических пропусков + 7 🟡 желательных + 6 🟢 операционных (вне Guide 3).

---

## Детализация 🔴 критических пропусков

### R1 — Agent Inbox / Диспетчеризация

**Что это:** Диспетчер агентов (`extensions/agent-inbox/`, `iwe-agent-dispatcher.py`) — cron/systemd/launchd запускает headless `claude -p` по расписанию, передаёт задачи агентам, собирает результаты. Обходит RemoteTrigger v1→v2 issue.

**Почему в Guide 3:** Guide 3 учит работать с IWE как средой. Диспетчеризация — ключевой элемент мультиагентности (S5.05), но в структуре она описана только как «использование разных моделей». Диспетчер — это инфраструктурный слой, который делает мультиагентность масштабируемой.

**Где добавить:** S4 (Агенты) — новый подраздел **4.08 Диспетчеризация агентов** (после 4.07), или расширить S4.SS6 (Peer-review) / S5.SS5 (Множественные агенты). Рекомендация: S4.08.

**Понятия:** Диспетчер (Dispatcher), Agent Inbox, Headless-режим, Cron-задача.

---

### R2 — Generated runtime architecture

**Что это:** `build-runtime.sh` генерирует `.iwe-runtime/` из FMT + `.exocortex.env`. FMT = immutable upstream, runtime = derived state. Аналог Nix derivation.

**Почему в Guide 3:** Guide 3 учит понимать IWE как систему. Generated runtime — архитектурный паттерн, объясняющий, как шаблон отделён от рабочего состояния. Это защита от drift'а между source и runtime (корень многих аварий).

**Где добавить:** S2.03 (Среда: инструментарий работы) — дополнить про runtime-генерацию, или S3 (Архитектура знаний) — как семейство документов. Рекомендация: S2.03 дополнить абзацем + S3.06 (Семейства документов) пример.

**Понятия:** Generated runtime, build-runtime, Source-of-Truth upstream, Runtime drift.

---

### R3 — Extensions / load-extensions.sh

**Что это:** 13 extension points (before/after/checks) в протоколах, wildcard suffix loader (`load-extensions.sh`). Пользователь добавляет `extensions/<protocol>.<hook>.md` — платформа подхватывает.

**Почему в Guide 3:** Guide 3 учит создавать IWE (S7). Extensions — механизм кастомизации без форка шаблона. Это ключевой элемент «создания среды» (M5), но в S7 нет ни слова про extensions.

**Где добавить:** S7.02 (Создание протокола) — дополнить про extension points, или новый подраздел S7.08 Расширяемость (после 7.07). Рекомендация: S7.02 дополнить.

**Понятия:** Extension point, Suffix extension, load-extensions, Hook (before/after/checks).

---

### R4 — iwe-audit.sh / iwe-drift.sh

**Что это:** Скрипты аудита (6 компонентов) и дрейф-детектора (mtime-lag пары source→derived).

**Почему в Guide 3:** S2.06–S2.07 уже про дрейф и аудит, но абстрактно («скрипты проверяют ссылки»). Конкретные инструменты не названы. Пилот, прочитав Guide 3, не узнает про существование `iwe-audit.sh` и `iwe-drift.sh`.

**Где добавить:** S2.07 (Дрейф-контроль и аудит Машины) — добавить перечень скриптов: `iwe-audit.sh`, `iwe-drift.sh`, `check-references.sh`. Упомянуть `sync-manifest.yaml` как реестр пар.

---

### R5 — Agent Fault Profile

**Что это:** Система учёта косяков агента: `agent_fault_remind.py`, `sync_feedback_to_memory.py`, feedback loop. Правило 1 культуры IWE.

**Почему в Guide 3:** S5 (14 элементов культуры) и S8 (Аварии) не содержат концепции «учёт ошибок агента». Это важная культурная практика: агенты ошибаются, и система должна это отслеживать.

**Где добавить:** S5.07 (ТО и эволюция системы) — дополнить про Agent Fault Profile как элемент журнала паттернов, или S8.06 (Восстановление после аварии) — как фиксация опыта. Рекомендация: S5.07.

**Понятия:** Agent Fault Profile, Feedback loop, Косяк агента (Agent fault).

---

## Рекомендации по структуре Guide 3

### Минимальные правки (5 🔴)

| Подраздел | Что добавить | Объём |
|-----------|-------------|-------|
| S2.03 | Параграф про `.iwe-runtime/` и `build-runtime.sh` | +2–3 строки |
| S2.07 | Перечень скриптов: `iwe-audit.sh`, `iwe-drift.sh` | +1–2 строки |
| S4 | Новый S4.08 «Диспетчеризация агентов» или расширить S4.SS6/S5.SS5 | +1 подраздел |
| S5.07 | Параграф про Agent Fault Profile | +2–3 строки |
| S7.02 | Параграф про extension points и `load-extensions.sh` | +2–3 строки |

### Расширенные правки (+7 🟡)

| Подраздел | Что добавить |
|-----------|-------------|
| S3.06 | Пример: CHANGELOG как семейство документов |
| S5.07 | Параграф про post-release audit (5 уровней) |
| S7 | Параграф про promote-скрипты (L1-flow) |
| S3 / S7 | Параграф про integration-contract-validator |
| S3 | Параграф про template-sync и drift между авторским и FMT |
| S3 или S7 | Параграф про Memory Lifecycle Protocol |
| S9.04 | Упоминание `iwe-trace-recorder` как инструмента трассировки |

---

## Предложение по WP-322: Release-to-guide mapping gate

### Проблема

FMT-релизы содержат функции, которые должны отражаться в Guide 3 (и других руководствах). Сейчас это происходит вручную и хаотично. Результат: Guide 3 отстаёт от платформы на 3–6 месяцев.

### Решение: Ф19 — Release-watcher

**Триггер:** push в `FMT-exocortex-template:main` с изменением `CHANGELOG.md`.

**Pipeline:**
1. **Извлечение:** Парсить CHANGELOG → список `Added` bullet points за релиз.
2. **Классификация:** Для каждой фичи — relevance score к Guide 3 (heuristic: keywords из ontology + manual mapping table).
3. **Проверка:** Для фич с score ≥ threshold — проверить, есть ли соответствующее `introduces` в `03-structure-guide-3.md` (или другом guide).
4. **Issue:** При gap → auto-create issue в `DS-principles-curriculum` с label `release-gap`, `guide-3`, `needs-author-review`.
5. **Чеклист:** Issue содержит шаблон: «Фича X из FMT vN.M.K не отражена в Guide 3. Рекомендуемый раздел: Y».

**Реализация:**
- Новый workflow `.github/workflows/release-to-guide.yml` в `DS-principles-curriculum` (или в `FMT-exocortex-template` как sender).
- Парсер CHANGELOG: Python-скрипт `tools/parse-changelog-features.py` — извлекает `Added` секции, фильтрует `Fixed`/`Changed` (не всегда нужны).
- Mapping table: YAML-файл `tools/release-to-guide-mapping.yaml` — ручная таблица «фича → раздел руководства → приоритет».
- Проверка против structure-guide: `v4-lint.py` уже умеет читать `introduces` из structure-guide. Можно расширить.

**Бюджет:** ~3–4 часа (Sonnet, closed-loop).

**Зависимости:**
- Готовность structure-guide-3.md (уже готова).
- Доступ к CHANGELOG FMT (public repo — `github.token` достаточен).

### Альтернатива: ручной gate

Вместо автоматики — добавить пункт в **чеклист релиза FMT** (WP-5 / S-44):
- «Проверить mapping новых фич → Guide 3. Если gap > 0 — создать issue в DS-principles-curriculum».

Это дешевле, но требует дисциплины.

---

## Вывод

1. **Guide 3 отстаёт от FMT на 5+ критических функций.** Без корректировки пилот, прочитавший Guide 3, не узнает про диспетчеризацию агентов, generated runtime, extensions, конкретные скрипты аудита и Agent Fault Profile.
2. **Минимальные правки** — 5 небольших дополнений (~10 строк текста + 1 подраздел), которые можно внести уже на уровне структуры (Phase 2).
3. **WP-322 стоит дополнить Ф19** (Release-watcher) для предотвращения накопления gap в будущем. Это 3–4 часа работы Sonnet.
4. **Рекомендация:** сначала минимальные правки структуры (🔴), затем Ф19 в WP-322, затем расширенные правки (🟡) по мере написания подразделов.
