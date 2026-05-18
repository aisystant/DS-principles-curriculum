---
type: process
status: draft
created: 2026-05-17
updated: 2026-05-17
upstream: [WP-322, CD-PIPELINE.md]
---

# Процессы CD-конвейера для руководств v4

> Система доставки контента от структуры подраздела до продакшена.
> Описана по правилу ВДВ (Вход → Действие → Выход) из DP.M.008 §5.
> Три аспекта: Процессы (как делать) + Данные (что хранить) + Видимость (что увидит участник).

---

## 1. Обещание сервиса (DP.SC.curriculum-cd)

**Кому:** Авторы руководств v4, Pack-владельцы, пилоты, платформа.

**Зачем:** Любое изменение в руководствах v4 проходит через предсказуемый конвейер: валидация → сборка → staging → пилот-тест → прод. Ни один подраздел не попадает в прод без gate'ов.

**Что получит:**
- Автор: мгновенная обратная связь по структуре и контенту (≤2 мин CI)
- Pack-владелец: автоматическое обнаружение drift'а при изменении Pack
- Пилот: уведомление о новых/изменённых подразделах + канал обратной связи
- Платформа: воспроизводимые релизы с semver и changelog

**Критерий приёмки:** Коммит в structure-guide → CI PASS/FAIL за ≤2 мин. Изменение Pack → issue за ≤5 мин. workflow_dispatch → draft в staging за ≤15 мин. Hotfix typo → в прод за ≤1 мин.

---

## 2. Система через ВДВ

### 2.1. Цель системы

Преобразовать изменения в структуре/контенте руководств v4 в опубликованный, проверенный текст с гарантией качества.

### 2.2. Границы системы

**Внутри конвейера:**
- GitHub Actions в `DS-principles-curriculum` и `aisystant/docs`
- Скрипты сборки/шаблонизации в `tools/`
- Staging-ветка `aisystant/docs:staging-v4`
- Issue-шаблоны и label-автоматика

**Снаружи (интерфейсы):**
- `PACK-personal` — источник онтологии и метрик (вход)
- `aisystant/docs:main` — продакшен (выход)
- Telegram-бот — канал уведомлений (выход)
- Neon `learning.guide_sections` — хранилище версий (данные)
- Claude API — LLM-сборка draft'ов (внешний сервис)

### 2.3. Процессы (ВДВ-цепочки)

#### С1. Автор правит структуру подраздела

**Вход:**
- Изменённый файл `specs/v4-reference/0N-structure-guide-N.md`
- Git-репо автора с настроенным pre-commit hook

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | Автор делает `git commit` | Автор | Git |
| 2 | Pre-commit hook: stub-валидатор structure + porter (~1 сек) | Локальный Git | `tools/pre-commit-stub.sh` |
| 3 | `git push` в `main` | Автор | Git |
| 4 | GitHub Actions: запуск CI pipeline | GitHub | `.github/workflows/ci-pipeline.yml` |
| 5 | CI: stub-валидаторы (structure / porter / cross-guide / pack-drift / fpf) + smoke-test (~30 сек) | CI-агент | `tools/stub-*.sh` → потом `v4-lint` |
| 6 | CI: PASS → auto-merge (если hotfix-тег) или ожидание ревью | GitHub | branch protection |
| 7 | Post-merge: trigger build в staging | GitHub | `repository_dispatch` → aisystant/docs |
| 8 | Build action: пересборка draft в `staging-v4` | CI-агент | `tools/build-skeleton.py` или LLM |
| 9 | TG-уведомление автору: «draft обновлён в staging» | Бот | Telegram API |

**Выход:**
- Обновлённый draft в `aisystant/docs:staging-v4`
- CI-лог с PASS/FAIL
- TG-уведомление автору

**Режим отказа:**
- FAIL lint → GitHub PR comment с диагностикой, merge blocked
- FAIL build → issue автору, staging не обновляется

---

#### С2. Pack-владелец обновляет PD.FORM.089

**Вход:**
- Коммит в `PACK-personal/.../PD.FORM.089-learner-rcs.md`

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | Коммит в `PACK-personal` | Pack-владелец | Git |
| 2 | Webhook: `repository_dispatch` в `DS-principles-curriculum` | GitHub | `.github/workflows/notify-curriculum.yml` |
| 3 | Action `pack-drift-watcher`: checkout PACK-personal + запуск stub-pack-drift | CI-агент | `tools/stub-pack-drift.sh` → потом `v4-lint pack-drift` |
| 4 | drift > 0 → создание issue «Pack обновлён» | CI-агент | `gh issue create` |
| 5 | Issue auto-assigned автору раздела (CODEOWNERS) | GitHub | CODEOWNERS |
| 6 | Cross-repo status: комментарий в Pack-PR «curriculum обновлён» | CI-агент | GitHub API |

**Выход:**
- GitHub issue в `DS-principles-curriculum` с таблицей drift'а
- Assigned автору
- Комментарий в Pack-репо

**Режим отказа:**
- Webhook не доставлен → лог в GitHub Actions, ручной retry через `workflow_dispatch`
- PACK-personal недоступен → CI FAIL с явной ошибкой, issue не создаётся

---

#### С3. LLM-генерация черновика подраздела

**Вход:**
- `subsection_id` (например, `PD.GUIDE.1.S2.SS3`)
- `structure-guide-N.md` — структура
- `role-prefixes.md` — дуга нарратива
- `PACK-personal/ontology.md` — понятия
- `PD.FORM.089` — метрики

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | `workflow_dispatch` с `subsection_id` | Автор / Автоматика | GitHub Actions UI / API |
| 2 | Build action собирает контекст: structure + Pack + role-prefixes | CI-агент | `tools/build-context.py` |
| 3 | Промпт из WRITING-PIPELINE Этап 4 + контекст → Claude API | CI-агент | Anthropic API |
| 4 | Claude API возвращает markdown draft | Claude | Opus/Sonnet |
| 5 | PR в `aisystant/docs:staging-v4` с draft | CI-агент | `gh pr create` |
| 6 | Автор-ревьюер правит → merge в staging | Автор | GitHub |

**Выход:**
- PR с markdown draft в `aisystant/docs:staging-v4`
- Контекст-файл (для аудита генерации)

**Режим отказа:**
- API timeout (>15 мин) → CI FAIL, retry через exponential backoff
- Невалидный `subsection_id` → FAIL до вызова API
- Недостаточно контекста → draft с placeholder'ами, автор дополняет

---

#### С4. Пилот заявляет «подраздел не работает"

**Вход:**
- Опыт пилота с подразделом (мем не снят / метод не применим / время ≠ норме)

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | Пилот открывает GitHub issue через шаблон `pilot-feedback` | Пилот | GitHub Issues |
| 2 | Issue auto-assigned автору раздела | GitHub | CODEOWNERS |
| 3 | Label `needs-rework` ставится автоматически | GitHub | Actions / labeler |
| 4 | Подраздел исключается из broadcast'а к новым пилотам | CI-агент | Фильтр в build-скрипте |
| 5 | Автор правит → новый commit → CI → build → staging | Автор | Полный pipeline С1 |
| 6 | Новый пилот-тест (≥3 пилота 6/6) | Пилоты | Платформа / TG |
| 7 | Label `pilot-approved` → подраздел возвращается в broadcast | GitHub | Actions |

**Выход:**
- GitHub issue с диагностикой
- Исправленный подраздел в staging
- Статус `needs-rework` / `pilot-approved`

**Режим отказа:**
- Автор не реагирует >7 дней → escalation к Platform Owner
- Пилот не проходит 6/6 после 3 итераций → субагент-ревью (Этап 9)

---

#### С5. Релиз новой версии (v4.X → v4.Y)

**Вход:**
- ≥5 merge'ей в `main` с тегом `new-concept`

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | `semver-bot.py` сканирует git log, предлагает bump | CI-агент | `tools/semver-bot.py` |
| 2 | PR с обновлённым `version.json` | CI-агент | `gh pr create` |
| 3 | Merge PR → GitHub Release auto | GitHub | `.github/workflows/release.yml` |
| 4 | Changelog из git log | CI-агент | `git log --pretty=format` |
| 5 | TG-notification активным пилотам | Бот | Telegram API |
| 6 | Git tag `v4.X.Y` для воспроизводимости | Git | `git tag` |

**Выход:**
- GitHub Release v4.X.Y
- Changelog
- TG-уведомление
- Git tag

**Режим отказа:**
- Нет `new-concept` merge'ей → no-op, релиз не предлагается
- TG-бот недоступен → лог в Actions, релиз создан без уведомления

---

#### С6. Hotfix typo в продакшене

**Вход:**
- Direct PR с `[hotfix]` в сообщении
- Изменение только в тексте (нет структурных изменений)

**Действие:**

| # | Шаг | Актор | Инструмент |
|---|-----|-------|------------|
| 1 | PR с тегом `[hotfix]` | Автор | GitHub |
| 2 | CI: только stub-structure-check (быстро, без rebuild) | CI-агент | `tools/stub-structure-check.sh` |
| 3 | PASS → auto-merge без пилот-теста | GitHub | branch protection + auto-merge |
| 4 | TG-notification: «hotfix залит» | Бот | Telegram API |

**Выход:**
- Смердженный hotfix в `main`
- TG-уведомление

**Режим отказа:**
- PR содержит не только typo → блокировка, требуется полный pipeline
- CI FAIL → merge blocked, автор получает диагностику

---

### 2.4. Данные (что хранить)

| Данные | Направление | Формат | Где хранится |
|--------|-------------|--------|--------------|
| Structure-файлы (source) | Вход → Конвейер | Markdown | `DS-principles-curriculum/specs/v4-reference/` |
| Pack (онтология + метрики) | Вход → Конвейер | Markdown | `PACK-personal/` |
| Role-prefixes (дуга) | Вход → Конвейер | Markdown | `DS-principles-curriculum/specs/v4-reference/role-prefixes.md` |
| Draft (staging) | Выход → Автор | Markdown | `aisystant/docs:staging-v4/docs/ru/personal-design-staging/` |
| Final text (prod) | Выход → Пилот | Markdown | `aisystant/docs:main/docs/ru/personal-design/` |
| CI-логи | Выход → Диагностика | Text / JSON | GitHub Actions logs (retention 90 дней) |
| GitHub issues (drift, feedback) | Выход → Автор | Markdown | `DS-principles-curriculum/issues` |
| version.json | Внутренний | JSON | `aisystant/docs/version.json` |
| Changelog | Выход → Пилот | Markdown | GitHub Release notes |
| TG-уведомления | Выход → Пилот | Text | Telegram (эфемерные) |
| Neon guide_sections | Данные → Платформа | SQL/JSON | Neon `learning.guide_sections` |
| Neon personal_guide_renders | Данные → Платформа | SQL/JSON | Neon `learning.personal_guide_renders` |

---

### 2.5. Видимость (что увидит участник)

| Участник | Что видит | Где | Когда |
|----------|-----------|-----|-------|
| **Автор** | CI PASS/FAIL + диагностика | GitHub PR / Actions | При каждом push |
| **Автор** | Pre-commit результат | Terminal (локально) | При каждом commit |
| **Автор** | TG: «draft обновлён, ссылка X» | Telegram | После merge |
| **Pack-владелец** | Issue «Pack обновлён, N подразделов» | GitHub Issues | В день коммита в Pack |
| **Пилот** | Новый/изменённый подраздел в staging | Сайт / TG | После build |
| **Пилот** | Issue-шаблон для feedback | GitHub Issues | По запросу |
| **Пилот** | TG: «вышел v4.X, что нового» | Telegram | При релизе |
| **Платформа** | CI health dashboard | Grafana / GitHub | Постоянно |
| **Platform Owner** | Pipeline metrics (pass rate, build time) | Grafana / Actions Summary | Еженедельно |

---

### 2.6. Режимы отказа

| Отказ | Детекция | Реакция | Восстановление |
|-------|----------|---------|----------------|
| CI FAIL (lint) | GitHub Actions | PR comment, merge blocked | Автор правит → push |
| CI FAIL (build) | GitHub Actions | Issue автору, staging не обновляется | Автор/агент чинит → retry |
| Pack-drift | `pack-drift-watcher` | Issue с таблицей drift'а | Автор обновляет подразделы |
| API timeout (Claude) | Actions timeout (>15 мин) | CI FAIL, exponential backoff retry | Повторный dispatch |
| TG-бот недоступен | HTTP error | Лог в Actions, релиз/уведомление без TG | Ручное уведомление |
| Невалидный subsection_id | Валидация ДО API call | FAIL с диагностикой | Автор исправляет ID |
| Пилот не проходит 6/6 | Label `needs-rework` | Исключение из broadcast, escalation | Автор правит → retest |
| Hotfix содержит не typo | Diff-анализ в CI | Блокировка, требуется полный pipeline | Автор делает полный PR |

---

## 3. Декомпозиция фаз (8 спринтов)

> Конвейер строится итеративно. Каждая фаза — работающий инкремент.
> Валидаторы (WP-321) интегрируются позже как gate'и в уже работающую трубу.

### Фаза 1. Pack-watcher — наблюдатель за Pack (~4-6ч)

**Цель:** Pack и Curriculum перестают дрейфовать невидимо.

**ВДВ:**
- **Вход:** Коммит в `PACK-personal/.../PD.FORM.089-learner-rcs.md`
- **Действие:** Webhook → `repository_dispatch` → stub-pack-drift → issue при drift > 0
- **Выход:** GitHub issue с assigned автором

**Чеклист:**
- [ ] `.github/workflows/notify-curriculum.yml` в `PACK-personal`
- [ ] `.github/workflows/pack-drift-watcher.yml` в `DS-principles-curriculum`
- [ ] `tools/stub-pack-drift.sh` (placeholder, exit 0 + лог)
- [ ] Issue шаблон «Pack обновлён»
- [ ] CODEOWNERS для авто-assignment
- [ ] Тест: локально обновить PD.FORM.089 → issue появляется

---

### Фаза 2. Staging-среда — песочница (~6-8ч)

**Цель:** Есть куда деплоить draft до продакшена.

**ВДВ:**
- **Вход:** Merge в `aisystant/docs:staging-v4` или trigger из `DS-principles-curriculum`
- **Действие:** Build + deploy в `personal-design-staging/`
- **Выход:** Доступный по URL staging-контент

**Чеклист:**
- [ ] Ветка `staging-v4` в `aisystant/docs`
- [ ] Папка `docs/ru/personal-design-staging/`
- [ ] `.github/workflows/staging-deploy.yml`
- [ ] Gate: merge staging → main только через label `pilot-approved` (ручной пока)
- [ ] Тест: push в staging → контент виден по URL

---

### Фаза 3. Детерминированная сборка — скелет без LLM (~4-6ч)

**Цель:** Структура → markdown draft без ИИ.

**ВДВ:**
- **Вход:** `subsection_id` + `structure-guide-N.md`
- **Действие:** `tools/build-skeleton.py` извлекает структуру, формирует скелет
- **Выход:** PR со скелетом в `staging-v4`

**Чеклист:**
- [ ] `tools/build-skeleton.py` (Jinja2 или string-formatting)
- [ ] `workflow_dispatch` с параметром `subsection_id`
- [ ] PR auto-create в `aisystant/docs:staging-v4`
- [ ] Тест: dispatch → PR со скелетом за ≤2 мин

---

### Фаза 4. LLM-сборка — черновик через Claude API (~6-8ч)

**Цель:** Полноценный draft за ≤15 мин от кнопки.

**ВДВ:**
- **Вход:** Контекст (structure + Pack + role-prefixes) + промпт Этап 4
- **Действие:** Claude API → markdown draft → PR
- **Выход:** PR с draft в `staging-v4`

**Чеклист:**
- [ ] `tools/build-context.py` — сборка контекста для API
- [ ] `ANTHROPIC_API_KEY` в secrets
- [ ] `.github/workflows/llm-build.yml`
- [ ] Промпт из WRITING-PIPELINE Этап 4 (вынесен в файл)
- [ ] Таймаут 15 мин, retry logic
- [ ] Тест: dispatch → draft PR за ≤15 мин

**⚠️ Координация:** Перед реализацией — проверить WP-149 (Кими), что уже готово.

---

### Фаза 5. Обратная связь пилота — замкнутый контур (~3-4ч)

**Цель:** Пилот не пишет в TG — пилот пишет в систему.

**ВДВ:**
- **Вход:** Опыт пилота с подразделом
- **Действие:** Issue-шаблон → label → assign → broadcast-фильтр
- **Выход:** Исправленный подраздел + статус approved/rework

**Чеклист:**
- [ ] `.github/ISSUE_TEMPLATE/pilot-feedback.yml`
- [ ] Auto-label `needs-rework`
- [ ] Auto-assign через CODEOWNERS
- [ ] Broadcast-фильтр: `needs-rework` → skip
- [ ] Тест: issue → label → assign → фильтр

---

### Фаза 6. Версионирование + релиз (~3ч)

**Цель:** Релизы без ручного труда.

**ВДВ:**
- **Вход:** ≥5 merge'ей с `new-concept`
- **Действие:** semver-bot → PR → Release → TG
- **Выход:** GitHub Release v4.X.Y + changelog + уведомление

**Чеклист:**
- [ ] `tools/semver-bot.py`
- [ ] `.github/workflows/release.yml`
- [ ] `version.json`
- [ ] Auto-changelog из git log
- [ ] TG-notification

---

### Фаза 7. Метрики и мониторинг (~6-10ч)

**Цель:** Видимость health pipeline.

**ВДВ:**
- **Вход:** CI-логи, build-метрики, пилот-данные
- **Действие:** Агрегация → Grafana dashboard
- **Выход:** Dashboard (pass rate, build time, drift count, completion rate)

**Чеклист:**
- [ ] CI-логи в формате для парсинга
- [ ] Метрики: pass rate, avg build time, drift count
- [ ] Grafana dashboard (или GitHub Actions summary)
- [ ] Тест: dashboard обновляется после CI run

---

### Фаза 8. Единый cross-repo pipeline (~4-6ч)

**Цель:** Один view на все trigger'ы.

**ВДВ:**
- **Вход:** Все trigger'ы (commit, Pack-change, pilot-feedback, dispatch)
- **Действие:** Конвергенция в единый workflow с `workflow_call`
- **Выход:** Единый status view (GitHub Actions summary / PR comment)

**Чеклист:**
- [ ] Рефакторинг в `cd-pipeline.yml` с `workflow_call`
- [ ] Единый PR comment со статусом всех gate'ов
- [ ] GitHub Actions summary page

---

## 4. Интеграция WP-321 (валидаторы) — после построения трубы

Когда WP-321 будет готов, stub'ы заменяются настоящими валидаторами:

| Stub | Замена | Где |
|------|--------|-----|
| `stub-structure-check.sh` | `python3 tools/v4-lint.py structure` | Pre-commit + CI |
| `stub-porter-check.sh` | `python3 tools/v4-lint.py porter` | Pre-commit + CI |
| `stub-cross-guide.sh` | `python3 tools/v4-lint.py cross-guide` | CI |
| `stub-pack-drift.sh` | `python3 tools/v4-lint.py pack-drift` | Pack-watcher |
| `stub-fpf-check.sh` | `python3 tools/v4-lint.py structure` (Ф10) | CI |

**Порядок интеграции:**
1. WP-322: Ф1-Ф8 с stub'ами (pipeline работает end-to-end)
2. WP-321: Реализация v4-lint (5 подкоманд)
3. WP-322 (продолжение): Замена stub → v4-lint, настройка gate'ов

---

## 5. Связь с другими системами

| Система | Интерфейс | Направление |
|---------|-----------|-------------|
| **PD.FORM.103** (методический upstream) | Pack | Источник модели жизненного цикла руководства (10 этапов ВДВ) |
| `PACK-personal` | GitHub webhook + `repository_dispatch` | Вход (онтология, метрики) |
| `aisystant/docs` | Git (push/PR) + GitHub Actions | Выход (staging, prod) |
| Telegram-бот | HTTP API | Выход (уведомления) |
| Neon (learning) | SQL / API | Данные (версии, рендеры) |
| Claude API | HTTP API | Внешний сервис (LLM Build) |
| WP-149 (Кими) | Координация ручная / shared design | Пересечение (LLM Build) |
| WP-321 (валидаторы) | CLI tools / GitHub Actions | Вход (gate'ы качества) |

### Карта чек-листов (содержательная проверка)

CD-конвейер использует трёхуровневые чек-листы (см. [CHECKLISTS-README.md](specs/v4-reference/CHECKLISTS-README.md)):

| Уровень | Файл | Применяется к |
|---------|------|---------------|
| Подраздел | [CHECKLIST-subsection-v1.md](specs/v4-reference/CHECKLIST-subsection-v1.md) | один SS |
| Раздел | [CHECKLIST-section-v1.md](specs/v4-reference/CHECKLIST-section-v1.md) | один S |
| Руководство | [CHECKLIST-guide-v1.md](specs/v4-reference/CHECKLIST-guide-v1.md) | целое руководство |

Чек-листы покрывают этапы 6-9 PD.FORM.103 (🔴 lint → 🟡 субагент → 🟢 пилот). Правило вложенности: подраздел → раздел → руководство; нижний уровень должен быть PASS перед верхним.
