# Staging Deploy — Инструкция для пилота (WP-322 Ф16)

> **Статус:** конфиги подготовлены, требуется action пилота для deploy.
> **Цель:** staging-среда на `staging.docs.aisystant.app` для предпросмотра руководств v4.

## Что уже готово (агент)

- `infra/nomad/docs-staging.nomad` — Nomad job spec
- `infra/caddy/docs-staging.Caddyfile` — reverse proxy snippet
- `infra/docker/Dockerfile.staging` — образ nginx со статикой
- `aisystant/docs:staging-v4` — ветка и workflow `staging-build.yaml` (собирает VitePress, upload artifact)

## Что нужно сделать (пилот)

### 1. Nomad job (3 шага)

```bash
# 1. Скопировать job spec на Nomad сервер (или управляющую машину)
scp infra/nomad/docs-staging.nomad nomad-server:/opt/nomad/jobs/

# 2. Запустить job с placeholder image (latest)
nomad job run /opt/nomad/jobs/docs-staging.nomad

# 3. Проверить статус
nomad job status docs-staging
nomad alloc status -json $(nomad job status docs-staging | grep running | head -1 | awk '{print $1}')
```

### 2. DNS

```
staging.docs.aisystant.app  A  <IP_NOMAD_SERVER или LB>
```

Если используется Consul + Fabio — DNS может не понадобиться (Fabio слушает на :80/:443).
Если Caddy на выделенном сервере — DNS указывает на IP сервера Caddy.

### 3. Caddy reverse proxy

```bash
# Добавить infra/caddy/docs-staging.Caddyfile в /etc/caddy/Caddyfile
sudo cat infra/caddy/docs-staging.Caddyfile >> /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Или, если Caddy управляется через Nomad — добавить job `caddy` с соответствующим конфигом.

### 4. GitHub Actions — build + deploy

Добавить в `aisystant/docs/.github/workflows/staging-build.yaml` (после шага build):

```yaml
      - name: Docker Login
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./infra/docker/Dockerfile.staging
          push: true
          tags: |
            ghcr.io/aisystant/docs-staging:${{ github.sha }}
            ghcr.io/aisystant/docs-staging:latest

      - name: Deploy to Nomad
        env:
          NOMAD_ADDR: ${{ secrets.NOMAD_ADDR }}
          NOMAD_TOKEN: ${{ secrets.NOMAD_TOKEN }}
        run: |
          # Установить nomad CLI (если не предустановлен)
          curl -fsSL https://releases.hashicorp.com/nomad/1.7.0/nomad_1.7.0_linux_amd64.zip -o nomad.zip
          unzip nomad.zip && sudo mv nomad /usr/local/bin/

          # Получить nomad job spec из curriculum repo
          curl -sL "https://raw.githubusercontent.com/aisystant/DS-principles-curriculum/main/infra/nomad/docs-staging.nomad" -o docs-staging.nomad

          # Deploy
          nomad job run -var image_tag=${{ github.sha }} docs-staging.nomad
```

**Secrets для aisystant/docs:**
- `NOMAD_ADDR` — например, `https://nomad.aisystant.app:4646`
- `NOMAD_TOKEN` — ACL token с правами на запуск job `docs-staging`

### 5. Branch protection (опционально, но рекомендуется)

В GitHub Settings → Branches → `main` (aisystant/docs):
- Require status checks: `check-pilot-approved` (из staging-build.yaml)
- Require pull request reviews

## Проверка

1. Push в `staging-v4` → GitHub Actions build + push image → Nomad deploy
2. Открыть `https://staging.docs.aisystant.app` → видим staging-версию руководств
3. PR `staging-v4 → main` с label `pilot-approved` → merge в prod

## Troubleshooting

| Симптом | Диагноз |
|---------|---------|
| `502 Bad Gateway` | Nomad job не running, или Caddy upstream неправильный |
| `404` | VitePress base path mismatch (проверить `base` в `.vitepress/config.ts`) |
| Image pull error | GHCR требует `docker login` — проверить `secrets.GITHUB_TOKEN` scope (packages:write) |
| Nomad deploy fail | Проверить `NOMAD_ADDR` и `NOMAD_TOKEN` (ACL) |

## Артефакты

| Файл | Назначение |
|------|-----------|
| `infra/nomad/docs-staging.nomad` | Nomad job spec |
| `infra/caddy/docs-staging.Caddyfile` | Caddy reverse proxy |
| `infra/docker/Dockerfile.staging` | Docker image для staging |
| `docs/staging-deploy.md` | Эта инструкция |
