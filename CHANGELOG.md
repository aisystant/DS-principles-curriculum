# Changelog

Автоматически поддерживается `tools/semver-bot.py` (WP-322 Ф6).
Формат: `[version] — YYYY-MM-DD`.

Лейблы PR, влияющие на версию:
- `hotfix` → patch bump (0.0.X)
- `new-concept` / `new-section` → minor bump (0.X.0)
- `new-guide` → major bump (X.0.0)
- `pilot-approved` + ≥5 PR — триггер следующего релиза

## [0.1.0] — 2026-05-19

### Инфраструктура CI/CD (WP-322)

- CI pipeline: structure / porter / cross-guide / pack-drift / pack-gap / completeness / smoke-test
- Matrix параллелизм lint-jobs (Ф12)
- Auto-merge для [hotfix] PR (Ф15)
- Pack-watcher: cross-repo trigger PACK-personal → DS-principles-curriculum (Ф1)
- Staging workflow (Ф2 фундамент, gate без Nomad)
- build-skeleton workflow_dispatch → PR в aisystant/docs (Ф3)
- pilot-feedback issue template + triage workflow (Ф5)

### Методический фундамент (WP-322 Ф0)

- PD.FORM.103 guide development pipeline в PACK-personal
- CHECKLIST-{guide,section,subsection}-v1.md
- v4-lint.py: 5 команд (structure/porter/cross-guide/pack-drift/completeness)
- Нормализация 110 подразделов S1-S10 (format_version 4.1)
