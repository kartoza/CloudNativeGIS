SHELL := /bin/bash

# Hetzner Cloud snapshot with CloudNativeGIS Processing pre-installed
# (see cng-lite.pkr.hcl). Needs `packer` and a Hetzner Cloud API token
# (Read & Write) as HCLOUD_TOKEN.
#
#   make generate-snapshot VERSION=0.0.2
#   make spin-up [SERVER_NAME=...]   # newest snapshot, or VERSION's
#   make delete SERVER_NAME=...
#
# Settings come from .env when present (created from .env.template on first
# run); command-line vars still win, e.g. `make generate-snapshot LOCATION=nbg1`.
-include .env

VERSION ?=
SERVER_TYPE ?= cx23
LOCATION ?= fsn1
# Server spin-up starts; any type with at least SERVER_TYPE's disk.
SPINUP_SERVER_TYPE ?=
SPINUP_LOCATION ?=
SSH_KEYS ?=
FIREWALL_ID ?=
# SERVER_NAME=... or server_name=...
SERVER_NAME ?= $(server_name)
# Packer and hetzner.py read the token from the environment.
export HCLOUD_TOKEN

.PHONY: check-token generate-snapshot spin-up delete

.env:
	@cp .env.template .env
	@echo "Created .env from .env.template"

check-token: .env
	@if [ -z "$$HCLOUD_TOKEN" ]; then \
		echo "Set HCLOUD_TOKEN (Hetzner Cloud API token, Read & Write) in .env first." >&2; \
		exit 1; \
	fi

generate-snapshot: check-token
	@if [ -z "$(VERSION)" ]; then \
		echo "Set VERSION in .env, or: make generate-snapshot VERSION=<cloudnativegis-processing image tag>" >&2; \
		exit 1; \
	fi
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Generating Hetzner snapshot for cloudnativegis-processing:$(VERSION)"
	@echo "------------------------------------------------------------------"
	@packer init .
	@packer build \
		-var version=$(VERSION) \
		-var server_type=$(SERVER_TYPE) \
		-var location=$(LOCATION) \
		${ARGS} .

# Start a server from the snapshot with its own LITE_API_TOKEN; prints its URL
# and token and saves them to .servers/<name>.env.
spin-up: check-token
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Spinning up cng-lite from snapshot $(if $(VERSION),$(VERSION),(newest))"
	@echo "------------------------------------------------------------------"
	@VERSION="$(VERSION)" \
		SERVER_TYPE="$(or $(SPINUP_SERVER_TYPE),$(SERVER_TYPE))" \
		LOCATION="$(or $(SPINUP_LOCATION),$(LOCATION))" \
		SSH_KEYS="$(SSH_KEYS)" \
		FIREWALL_ID="$(FIREWALL_ID)" \
		python3 hetzner.py spin-up "$(SERVER_NAME)"

# Delete a server started by spin-up (billed until deleted).
delete: check-token
	@if [ -z "$(SERVER_NAME)" ]; then \
		echo "Usage: make delete SERVER_NAME=<name>  (see .servers/)" >&2; \
		exit 1; \
	fi
	@python3 hetzner.py delete "$(SERVER_NAME)"
