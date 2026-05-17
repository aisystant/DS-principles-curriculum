---
id: PACK-WATCHER-SETUP
title: "Инструкция: настройка Pack-watcher (WP-322 Ф1.3 e2e)"
created: 2026-05-17
upstream: [WP-322]
audience: владелец репо (Дмитрий)
---

# Настройка Pack-watcher: e2e тест

> **Цель:** проверить end-to-end что коммит в `PACK-personal/PD.FORM.089` создаёт issue в `DS-principles-curriculum`.
>
> Локальный stub (`tools/stub-pack-drift.sh`) уже протестирован в Ф1.1 — работает. Receiver workflow и sender workflow готовы, но требуют user action для активации.

## Что готово (закоммичено)

| Компонент | Где | Status |
|-----------|-----|--------|
| `notify-curriculum.yml` | `PACK-personal/.github/workflows/` | ✅ commited |
| `pack-drift-watcher.yml` | `DS-principles-curriculum/.github/workflows/` (ветка `review/pipeline-section-07`) | ✅ committed |
| `stub-pack-drift.sh` | `DS-principles-curriculum/tools/` | ✅ committed |
| `pack-drift.yml` issue-шаблон | `DS-principles-curriculum/.github/ISSUE_TEMPLATE/` | ✅ committed |
| `CODEOWNERS` | `DS-principles-curriculum/.github/` | ✅ committed |

## Шаги для e2e (требуют action пользователя)

### Шаг 1. Merge workflow в default branch

GitHub регистрирует workflow только из default branch. Текущая ветка — `review/pipeline-section-07`.

```bash
cd ~/IWE/DS-principles-curriculum
# Вариант A: merge ветки целиком (если все коммиты ветки готовы к main)
gh pr create --base main --head review/pipeline-section-07 \
  --title "feat(WP-322): Ф0 + Ф1.1-1.2 — методический фундамент + Pack-watcher" \
  --body "См. WP-322 контекст. После merge — workflow зарегистрируется и можно тестировать e2e."

# Вариант B: cherry-pick только WP-322 коммита в новую ветку от main
git checkout main && git pull
git checkout -b wp-322/pack-watcher
git cherry-pick b39a866   # SHA коммита WP-322 Ф0+Ф1.1+Ф1.2
git push origin wp-322/pack-watcher
gh pr create --base main --head wp-322/pack-watcher --title "..." --body "..."
```

### Шаг 2. Создать PAT для cross-repo dispatch

`notify-curriculum.yml` использует secret `CURRICULUM_DISPATCH_TOKEN`.

1. Зайти в [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) — Fine-grained PAT
2. Resource owner: `aisystant` (org owner DS-principles-curriculum)
3. Repositories: `DS-principles-curriculum` only
4. Permissions:
   - Contents: Read-only
   - Actions: Read and write (для `repository_dispatch`)
5. Скопировать токен.

### Шаг 3. Добавить secret в PACK-personal

```bash
cd ~/IWE/PACK-personal
gh secret set CURRICULUM_DISPATCH_TOKEN --body "<token-from-step-2>"
gh secret list   # проверить, что появился
```

### Шаг 4. Тестовый коммит в PD.FORM.089

```bash
cd ~/IWE/PACK-personal
echo "" >> pack/personal-development/02-domain-entities/formalizations/PD.FORM.089-learner-rcs.md
git add pack/personal-development/02-domain-entities/formalizations/PD.FORM.089-learner-rcs.md
git commit -m "test(WP-322 Ф1.3 e2e): trigger Pack-watcher"
git push origin main
```

### Шаг 5. Проверить срабатывание

```bash
# 1. PACK-personal: notify-curriculum.yml должен пройти
cd ~/IWE/PACK-personal
gh run list --workflow=notify-curriculum.yml --limit 1
gh run view <run-id>   # проверить, что dispatch отправлен

# 2. DS-principles-curriculum: pack-drift-watcher.yml должен запуститься
cd ~/IWE/DS-principles-curriculum
gh run list --workflow=pack-drift-watcher.yml --limit 1
gh run view <run-id>

# 3. Issue должен появиться
gh issue list --label pack-drift --limit 5
```

**Критерий PASS:** issue с label `pack-drift` создан в `DS-principles-curriculum` за ≤2 мин после коммита в PACK-personal.

## Альтернатива: ручной запуск через workflow_dispatch

Можно проверить только receiver pipeline (без cross-repo PAT) после merge workflow в main:

```bash
cd ~/IWE/DS-principles-curriculum
gh workflow run pack-drift-watcher.yml --ref main
gh run list --workflow=pack-drift-watcher.yml --limit 1
```

Это запустит receiver, который checkout PACK-personal (через `github.token`), запустит stub-pack-drift, создаст issue. Проверяет всё, кроме cross-repo notify.

## После успешного e2e

- Обновить WP-322 контекст: Ф1.3 → completed
- Перейти к Ф2 (staging-среда `aisystant/docs:staging-v4`)
- При готовности WP-321 v4-lint pack-drift → заменить `stub-pack-drift.sh` на `python3 tools/v4-lint.py pack-drift`

## Откат (если что-то сломается)

```bash
# В PACK-personal: убрать workflow
cd ~/IWE/PACK-personal
git rm .github/workflows/notify-curriculum.yml
git commit -m "revert: temporarily disable Pack-watcher trigger"
git push origin main

# В DS-principles-curriculum (если уже в main):
cd ~/IWE/DS-principles-curriculum
git checkout main
git rm .github/workflows/pack-drift-watcher.yml
git commit -m "revert: temporarily disable Pack-watcher receiver"
git push origin main
```

Issue-шаблон и stub-pack-drift.sh можно оставить — они независимы от workflow.
