# Action пилота: закрытие WP-322 (осталось после агента 20 мая)

> Дата: 2026-05-20
> Агент: Kimi
> Контекст: WP-322 CI/CD конвейер для руководств v4

## Что агент сделал 20 мая

- ✅ **Ф11** — auto-issue при `pack-gap > 0` в PR (`content-validation.yaml`)
- ✅ **Ф10** — mermaid-диаграмма потока артефактов Э0→Э12 (`WRITING-PIPELINE.md`)
- ✅ Проверка workflow: все 10 workflow в `.github/workflows/` синтаксически корректны
- ✅ Smoke-test: `v4-lint` 9 команд работают, structure/guide PASS

---

## Что требует action пилота

### 1. GitHub Secrets (fine-grained PAT'ы)

| Secret | Scope | Куда добавить | Зачем |
|--------|-------|---------------|-------|
| `DOCS_READ_TOKEN` | `aisystant/docs` Contents:R | DS-principles-curriculum | `completeness` step без warning |
| `DOCS_WRITE_TOKEN` | `aisystant/docs` Contents:W + PR:W | DS-principles-curriculum | `build-skeleton.yml` → PR в docs |
| `PACK_READ_TOKEN` | `aisystant/PACK-personal` Contents:R | DS-principles-curriculum | Fallback если repo приватный |
| `CURRICULUM_DISPATCH_TOKEN` | `aisystant/DS-principles-curriculum` Contents:R + Metadata:R + Actions:W | PACK-personal | Cross-repo trigger pack-drift, TTL 90 дней |
| `NOMAD_ADDR` + `NOMAD_TOKEN` | Nomad cluster | aisystant/docs | Deploy staging из CI |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram bot | DS-principles-curriculum | Release notifications (опционально) |

**Инструкция:** Settings → Secrets and variables → Actions → New repository secret.

### 2. Branch protection rules (GitHub UI)

**Репо:** `aisystant/DS-principles-curriculum`, ветка `main`.

Settings → Branches → Add rule:
- ✅ **Require a pull request before merging**
- ✅ **Require status checks to pass before merging**
  - `lint (structure)`
  - `lint (porter)`
  - `lint (cross-guide)`
  - `lint (pack-drift)`
  - `Pack-sufficiency gate`
  - `smoke-test` (если есть отдельный)
- ✅ **Require conversation resolution before merging**
- ✅ **Include administrators** (опционально, но рекомендуется)

**Это блокирует:**
- Ф15 (auto-merge) — без required checks `gh pr merge --auto` не сработает
- Ф2 (staging gate) — без branch protection maintainer может merge мимо красного check

### 3. Git tag для semver-bot

```bash
cd /path/to/DS-principles-curriculum
git tag v0.1.0
git push origin v0.1.0
```

Без тега `semver-bot.py` не сможет вычислить первый bump.

### 4. Staging deploy (Nomad + DNS + Caddy)

**Шаги:**

1. **DNS:** Добавить A-запись `staging.docs.aisystant.app` → IP Nomad worker node.
2. **Nomad job:**
   ```bash
   nomad job run -var image_tag=latest infra/nomad/docs-staging.nomad
   ```
3. **Caddy reload:**
   ```bash
   sudo caddy reload --config infra/caddy/docs-staging.Caddyfile
   ```
4. **GitHub Secrets в aisystant/docs:** `NOMAD_ADDR`, `NOMAD_TOKEN`.
5. **Обновить `staging-build.yaml`:** Добавить шаги `docker build/push` + `nomad job run` (snippet в `docs/staging-deploy.md`).

Подробнее: `docs/staging-deploy.md` (уже в репо).

### 5. Fine-grained PAT замена (security followup Ф1.3)

Текущий `CURRICULUM_DISPATCH_TOKEN` (если это user-bound `gho_*`) имеет scope `repo+workflow` = доступ ко всем репо. **Рекомендуется заменить на fine-grained PAT:**

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Generate new token:
   - Repository access: `aisystant/DS-principles-curriculum`
   - Permissions: Contents (Read), Metadata (Read), Actions (Write)
   - Expiration: 90 дней
3. Обновить secret `CURRICULUM_DISPATCH_TOKEN` в `PACK-personal`.

### 6. Проверка e2e Pack-watcher (Ф1.3)

После настройки PAT:
1. Сделать тестовый коммит в `PACK-personal/.../PD.FORM.089-learner-rcs.md`
2. Проверить, что issue создан в `DS-principles-curriculum` ≤2 мин
3. Проверить heartbeat в Actions summary (step «No-op log + heartbeat»)

---

## Порядок выполнения (рекомендуемый)

1. Git tag `v0.1.0` (1 мин)
2. Fine-grained PAT'ы (15 мин)
3. Branch protection rules (10 мин)
4. Test auto-merge на `[hotfix]` PR (Ф15) — создать тестовый PR, поставить label
5. Nomad staging (20 мин) — если инфраструктура готова
6. e2e Pack-watcher (5 мин)

---

## После выполнения

- Закрыть Ф2, Ф15, Ф16 в WP-322.md
- Запустить `v4-lint completeness --guide 1 --content-dir <docs>` для проверки полноты
- Приступить к Ф9 (применение чек-листов к контенту WP-300)
