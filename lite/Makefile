SHELL := /bin/bash

# Settings come from .env when present; command-line vars still win.
-include .env

IMAGE ?= cloudnativegis-processing
TAG ?= latest
PORT ?= 8000
export IMAGE TAG PORT

.PHONY: build up run down logs shell smoke-test clean

.env:
	@cp .env.template .env
	@echo "Created .env from .env.template"

build:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Building $(IMAGE):$(TAG)"
	@echo "------------------------------------------------------------------"
	@docker compose build ${ARGS}

up: .env
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Running $(IMAGE):$(TAG) on port $(PORT)"
	@echo "------------------------------------------------------------------"
	@docker compose up -d ${ARGS}

run: .env
	@docker compose up ${ARGS}

down:
	@docker compose down

logs:
	@docker compose logs -f --tail=100 lite

shell:
	@docker compose exec lite /bin/bash

# Starts the image in the background and waits for /health. Uses plain
# `docker run` so it also works in CI without a .env (release-lite workflow).
smoke-test:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Smoke testing $(IMAGE):$(TAG)"
	@echo "------------------------------------------------------------------"
	@docker run -d --rm --name cloudnativegis-processing-smoke -p $(PORT):8000 $(IMAGE):$(TAG) > /dev/null
	@for i in $$(seq 1 30); do \
		if curl -fsS http://localhost:$(PORT)/health; then \
			echo; echo "Lite service is healthy"; \
			docker stop cloudnativegis-processing-smoke > /dev/null; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Lite service did not become healthy" >&2; \
	docker logs cloudnativegis-processing-smoke; \
	docker stop cloudnativegis-processing-smoke > /dev/null; \
	exit 1

clean:
	@docker compose down --rmi all
