# docs-staging.nomad — WP-322 Ф16
# Nomad job для staging-среды руководств v4.
# Служит статический VitePress build на staging.docs.aisystant.app
#
# Deploy из CI:
#   nomad job run -var image_tag=<sha> infra/nomad/docs-staging.nomad
#
# Requirements:
#   - Nomad cluster с docker driver
#   - Consul (для service discovery)
#   - Caddy / Fabio (для reverse proxy, см. infra/caddy/)
#   - GitHub Container Registry access (ghcr.io/aisystant/docs-staging)

variable "image_tag" {
  type        = string
  description = "Docker image tag (обычно git sha)"
  default     = "latest"
}

variable "domain" {
  type        = string
  description = "Staging domain"
  default     = "staging.docs.aisystant.app"
}

job "docs-staging" {
  datacenters = ["dc1"]
  type        = "service"

  group "docs" {
    count = 1

    network {
      mode = "bridge"
      port "http" {
        to = 80
      }
    }

    service {
      name = "docs-staging"
      port = "http"
      tags = [
        "staging",
        "docs",
        # Fabio route tag (если используется Fabio вместо Caddy)
        "urlprefix-${var.domain}/",
      ]

      check {
        type     = "http"
        path     = "/"
        interval = "10s"
        timeout  = "2s"

        check_restart {
          limit           = 3
          grace           = "30s"
          ignore_warnings = false
        }
      }
    }

    task "nginx" {
      driver = "docker"

      config {
        image = "ghcr.io/aisystant/docs-staging:${var.image_tag}"
        ports = ["http"]
      }

      resources {
        cpu    = 100
        memory = 128
      }
    }
  }
}
