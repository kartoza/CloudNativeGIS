# Builds a Hetzner Cloud snapshot with CloudNativeGIS Processing pre-installed.
#
# Packer creates a temporary server, provisions it, snapshots it and deletes
# the server. Run via `make generate-snapshot` (needs HCLOUD_TOKEN).
#
# The image is pulled into the snapshot so a server started from it only has
# to start the container. The service is installed but not enabled: each
# server is expected to get its own LITE_API_TOKEN through cloud-init, which
# writes /etc/cng-lite/env and then runs `systemctl start cng-lite`.

packer {
  required_plugins {
    hcloud = {
      source  = "github.com/hetznercloud/hcloud"
      version = ">= 1.6.0"
    }
  }
}

variable "image" {
  type    = string
  default = "ghcr.io/kartoza/cloudnativegis-processing"
}

variable "version" {
  type        = string
  description = "Tag of the processing image baked into the snapshot."
}

variable "location" {
  type    = string
  default = "fsn1"
}

# Smallest x86 type: a snapshot can only be used on server types whose disk is
# at least as large as the one it was taken from.
variable "server_type" {
  type    = string
  default = "cx23"
}

variable "base_image" {
  type    = string
  default = "ubuntu-24.04"
}

source "hcloud" "cng_lite" {
  image         = var.base_image
  location      = var.location
  server_type   = var.server_type
  ssh_username  = "root"
  server_name   = "packer-cng-lite-${var.version}"
  snapshot_name = "cng-lite-${var.version}-{{timestamp}}"
  snapshot_labels = {
    app     = "cng-lite"
    version = var.version
  }
}

build {
  sources = ["source.hcloud.cng_lite"]

  provisioner "file" {
    source      = "${path.root}/cng-lite.service"
    destination = "/etc/systemd/system/cng-lite.service"
  }

  provisioner "shell" {
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
    inline = [
      "cloud-init status --wait > /dev/null || true",
      "curl -fsSL https://get.docker.com | sh",
      "systemctl enable docker",
      "docker pull ${var.image}:${var.version}",
      "sed -i 's|__IMAGE__|${var.image}:${var.version}|' /etc/systemd/system/cng-lite.service",
      "systemctl daemon-reload",
      "mkdir -p /etc/cng-lite && chmod 700 /etc/cng-lite",
      "rm -f /etc/cng-lite/env",
      "apt-get clean",
      "cloud-init clean --logs",
    ]
  }
}
