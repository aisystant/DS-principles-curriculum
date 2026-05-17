---
id: PD-GUIDE-V4-CD-PIPELINE
title: "Continuous Delivery pipeline для универсальных руководств v4 (design)"
status: design
created: 2026-05-16
upstream: [WP-321, WP-300]
---

# CD pipeline для универсальных руководств v4 — design doc

> **Цель документа:** зафиксировать обещание + сценарии + декомпозицию CD-конвейера от структуры подраздела до прода. Не реализация — будущий source для РП (предположительно WP-322).
>
> **Связь с WP-321:** WP-321 реализовал слой «быстрые тесты» (v4-lint, этапы 2/8/10/14 WRITING-PIPELINE.md). CD-pipeline — расширение наверх: build, staging, deploy, monitor, hotfix.

---

## DP.SC.curriculum-cd — обещание сервиса

| Поле | Значение |
|------|----------|
| **Триггер** | Коммит в `specs/v4-reference/`, или коммит в `PACK-personal/ontology.md` / `PD.FORM.089`, или pilot-feedback issue, или ручной `workflow_dispatch` |
| **Входы** | `structure-guide-N.md` (структура) + `PACK-personal/ontology.md` (понятия) + `role-prefixes.md` (дуга нарратива) + `PD.FORM.089` (метрики) + опционально draft текста подраздела |
| **Выходы** | (1) Build: собранный markdown подраздела в staging; (2) Validation: PASS/FAIL по 4 этапам v4-lint; (3) Pack-drift: список расхождений после смены Pack; (4) Promote: merge staging → prod после 3/3 пилот-теста |
| **Время отклика** | ≤2 мин от коммита до finish CI; ≤15 мин до build draft в staging; ≤30 мин до уведомления пилота; ≤7 дней до prod (зависит от пилот-теста) |
| **Инвариант** | Ни один подраздел не попадает в `docs/ru/personal-new/` без: (а) **Pack-sufficiency** (все понятия `introduces` есть в `PACK-personal/ontology.md` §2 + имеют Pack-источник `PD.FORM/METHOD/CAT.NNN` — `v4-lint structure --strict-pack`, см. PD.FORM.103 Этап 3.5 + WRITING-PIPELINE §1.5); (б) PASS всех 4 v4-lint валидаторов (structure, porter, cross-guide, pack-drift) + FPF (Ф10); (в) PASS субагент-ревью (Этап 9 WRITING-PIPELINE); (г) 6/6 от ≥3 пилотов (Этап 11). Hotfix-исключение: typo-only с тегом `[hotfix]` — только pre-commit + auto-merge, но Pack-sufficiency (а) обязательна и для hotfix |
| **Режим отказа** | FAIL build/lint → GitHub issue автору с диагностикой; FAIL pilot → откат в staging с тегом `needs-rework`; Pack-drift → issue с местами, требующими обновления, без блокировки текущей работы |

---

## Сценарии использования

### С1. Автор правит структуру подраздела (typo, новое понятие)

**Потребитель:** автор v4 (Артём, Кими, пилот).

1. `git commit` в `specs/v4-reference/01-structure-guide-1.md`
2. pre-commit hook запускает `v4-lint structure + porter` локально — за ~1 сек
3. `git push`
4. GitHub Actions запускает: structure / porter / cross-guide / pack-drift / fpf (Ф10) + smoke-test → ~30 сек
5. PASS → auto-merge (hotfix-тег) или ожидание ревью (feature)
6. Post-merge Build action: пересборка draft в ветке `staging-v4` репо `aisystant/docs`
7. Автор получает TG: «draft 1.04 обновлён в staging, ссылка X»

### С2. Pack-владелец обновляет PD.FORM.089 (новый `cp.something`)

**Потребитель:** Knowledge Extractor (DP.AISYS.013), пилот-владелец Pack.

1. commit в `PACK-personal/.../PD.FORM.089-learner-rcs.md`
2. GitHub webhook → `repository_dispatch` в `DS-principles-curriculum`
3. Action `pack-drift-watcher` запускает `v4-lint pack-drift` на всех 4 руководствах
4. drift > 0 → создание issue с шаблоном «Pack обновлён, требуется проверка X подразделов»
5. Issue auto-assigned автору раздела (через CODEOWNERS)
6. Pack-владелец видит в Pack-репо: «curriculum обновлён» (cross-repo status)

### С3. LLM-генерация черновика подраздела

**Потребитель:** автор v4, не хочет писать с нуля.

1. `workflow_dispatch` с параметром `subsection_id=PD.GUIDE.1.S2.SS3`
2. Build action собирает контекст: structure-guide + понятия + role-prefixes + промпт из WRITING-PIPELINE Этап 4
3. Вызов Claude API → markdown draft
4. PR в `aisystant/docs` с draft в `docs/ru/personal-new-staging/1-2/02-03.md`
5. Автор-ревьюер правит → merge в staging

**Пересечение:** WP-149 «Система генерации руководств» (Кими) делает ровно это. Перед началом — выяснить, что у него готово.

### С4. Пилот заявляет «подраздел не работает»

**Потребитель:** пилот (Паша / Дима / Ильшат).

1. GitHub issue с шаблоном `pilot-feedback`:
   - Какой подраздел (`PD.GUIDE.X.SX.SSX`)
   - Что не сработало (мем не снят / метод не применим / время ≠ норме)
2. Issue auto-assigned автору раздела
3. Label `needs-rework` ставится автоматически
4. Подраздел в staging переоткрывается, исключается из broadcast'а к новым пилотам
5. Автор правит → новый build → новый пилот-тест

### С5. Релиз новой версии руководства (v4.0 → v4.1)

**Потребитель:** пилоты, маркетинг (если будет публичный анонс).

1. На `main` собралось ≥5 merge'ей с `new-concept` тегом → semver-bot предлагает v4.1.0
2. PR с обновлённым `version.json`
3. После merge: GitHub Release auto + changelog из git log
4. TG-notification всем активным пилотам: «вышел v4.1, что нового: ...»
5. Старые версии остаются доступны через git tag (воспроизводимость)

### С6. Hotfix typo в продакшене

**Потребитель:** автор, заметивший опечатку.

1. Direct PR с тегом `[hotfix]` в `docs/ru/personal-new/`
2. CI: только структурные тесты (без полного rebuild)
3. PASS → auto-merge без пилот-теста (typo не требует пилота)
4. TG-notification владельцу: «hotfix залит»

---

## Скорость изменений (целевая)

| Изменение | Сейчас (ручной) | С полным CD | Ускорение |
|-----------|----------------|------------|-----------|
| Опечатка | 5 мин | 1 мин (auto-merge hotfix) | 5× |
| Новое понятие в Pack + синхронизация 4 руководств | 1-2 часа (ручной grep + правки) | 15 мин (commit Pack + auto-pack-drift + auto-issue) | 8× |
| Новый подраздел с нуля | 1-3 дня | 4-8 часов (LLM draft + ревью + пилот в параллель) | 3-5× |
| Изменение нарративной дуги | 1-2 недели | 2-3 дня (auto-detection всех затронутых подразделов) | 5× |

**Видимость на каждом уровне:**

- **Автор:** CI logs в GitHub (≤2 мин), pre-commit локально (≤1 сек)
- **Pack-владелец:** issue в DS-principles-curriculum при drift'е (в день обновления Pack)
- **Пилот:** TG-уведомление при обновлении его подраздела
- **Маркетинг/публичные пилоты:** GitHub Releases + changelog
- **Метрики на сайте** (если будет): время на чтение, % завершения, conversion

---

## Декомпозиция в спринты

| # | Спринт | Бюджет | Приоритет | Что даёт |
|---|--------|--------|-----------|----------|
| 1 | **Pack-watcher** (cross-repo trigger PACK-personal → DS-principles-curriculum) | 4-6h | 🔴 высокий | Pack ↔ Curriculum связка хрупкая, drift накапливается невидимо. Самая дешёвая и ценная автоматика |
| 2 | **Staging environment** (ветка `staging-v4` + папка `personal-new-staging/`) | 6-8h | 🔴 высокий | Фундамент для всего CD — без staging нет deploy gate |
| 3 | **Deterministic Build** (структура + Pack → markdown draft через шаблонизацию, без LLM) | 4-6h | 🟡 средний | Дешёвая версия сборщика — Скелет подраздела без AI |
| 4 | **LLM Build** (Claude API + промпт из WRITING-PIPELINE Этап 4) | 6-8h | 🔴 высокий | Главный rebenefit. Пересекается с WP-149 (Кими) — координировать |
| 5 | **Pilot feedback loop** (issue templates + label automation) | 3-4h | 🟡 средний | Без него пилот-фидбек теряется в TG |
| 6 | **Versioning + Release** (semver-bot + auto-changelog + TG notify) | 3h | 🟢 средний | После первого пилот-цикла |
| 7 | **Metrics/Monitor** (analytics на site, completion rate) | 6-10h | 🟡 средний | Зависит от того, есть ли публичный сайт с tracking |
| 8 | **Cross-repo CI mono-pipeline** (конвергенция всех trigger'ов в один view) | 4-6h | 🟢 средний | Polish — не блокер |

**ИТОГО:** ~36-51h на полный CD.

---

## Связки с другими РП

| РП | Связь |
|----|-------|
| **WP-321** v4-lint валидаторы | 🔴 Фундамент. Все 4 валидатора + Ф10 (FPF + Graph) — это слой «быстрые тесты» CI. Без него CD не имеет gate'ов |
| **WP-300** Универсальные руководства | 🔴 Parent. CD pipeline = инфраструктура доставки контента WP-300 |
| **WP-149** Система генерации руководств | 🔴 Прямое пересечение со Спринт 4 (LLM Build). Координировать с Кими |
| **WP-245** Программа личного развития | 🟡 Содержательный source (дуга нарратива, ступени, рубрики) |
| **PD.SC.036** Routing of knowledge | 🟢 Куда коммитить (структура vs финальный текст). Уже описан |

---

## Что НЕ автоматизируется (остаётся ручным или за субагентом)

| Проверка | Почему |
|----------|--------|
| **A.6 Boundary Discipline** (чёткие границы между понятиями) | Семантика, не структура. Этап 9 (субагент Claude) |
| **Нарратив мем → метод → мировоззрение** | Нужно прочитать текст и понять, есть ли цепочка. Этап 9 |
| **Дуга по ступени** (тональность ст. 1-2 = конкретика; 3-5 = горизонт) | NLP-проверка тональности. Этап 9 |
| **Thinking Through Writing** (каждый абзац несёт мысль) | Семантика. Этап 9 |
| **Эмерджентность аналогии** (метафора работает или нет) | Требует пилот-теста с живым человеком. Этап 11 |
| **Сдвиг мировоззрения** | Требует наблюдения за пилотом. Не метрика — наблюдение |

Это финальный ограничитель: софтверный CD доставляет код за минуты, контентный CD доставляет _черновик_ за минуты, но _проверенный текст_ — за дни (нужен пилот-тест).

---

## Открытые вопросы

1. **Куда коммитить финальный текст?** Сейчас: `aisystant/docs/docs/ru/personal-new/`. Structure: `DS-principles-curriculum/specs/v4-reference/`. Разделение source vs build artifact — стандарт. WRITING-PIPELINE Этап 13 этого явно не подчёркивает (был замечен в первичной проверке Кими).
2. **Куда писать build-логи / staging-метаданные?** Github Actions logs vs отдельный лог в репо?
3. **Кто owner субагент-ревью (Этап 9)?** Сейчас вызывается автором вручную. Можно автоматизировать через `claude-code` в CI, но это требует API budget.
4. **Pilot-pool dynamic.** Сейчас 3 фиксированных пилота. При >10 руководств одновременно — нужна ротация. Кто пишет алгоритм?
5. **A/B тесты подраздела.** Описано в концепции, не описано как реализовать в Git-based pipeline.

---

*Создан: 2026-05-16 (WP-321 close). Следующий шаг: после Ф10 WP-321 — открыть WP-322 «CD pipeline для curriculum» по этому design doc.*
