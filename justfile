# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later

# CloudNativeGIS Justfile
# Modern task runner for development, testing, and release workflows

# Default recipe - show all available tasks
default:
    @just --list

# =============================================================================
# Development
# =============================================================================

# Start development server
dev:
    @echo "Starting development server..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml up -d dev

# Start production server
up:
    @echo "Starting production server..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml up -d nginx django

# Stop all containers
down:
    @echo "Stopping containers..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml down

# Shell into development container
shell:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec dev /bin/bash

# Shell into production container
shell-prod:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec django /bin/bash

# Wait for database to be ready
wait-db:
    @echo "Waiting for database..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T db su - postgres -c "until pg_isready; do sleep 5; done"

# Run development entrypoint
dev-entrypoint:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev "/home/web/django_project/entrypoint.sh"

# Start Django runserver in dev container
dev-runserver:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev bash -c "nohup python manage.py runserver 0.0.0.0:5000 &"

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test:
    @echo "Running tests..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev python manage.py collectstatic --noinput
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev python manage.py test cloud_native_gis.tests --keepdb --noinput

# Run tests with coverage
test-cov:
    @echo "Running tests with coverage..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev pytest --cov=cloud_native_gis --cov-report=html --cov-report=term

# =============================================================================
# Code Quality
# =============================================================================

# Run all linters
lint:
    @echo "Running linters..."
    pre-commit run --all-files

# Run ruff linter only
lint-ruff:
    ruff check django_project/

# Format all code
format:
    @echo "Formatting code..."
    ruff format django_project/
    ruff check --fix django_project/

# Run type checking
typecheck:
    @echo "Running type checks..."
    mypy django_project/cloud_native_gis/

# Run pre-commit on all files
check:
    pre-commit run --all-files

# Run REUSE compliance check
reuse-lint:
    reuse lint

# =============================================================================
# Documentation
# =============================================================================

# Build and serve documentation
docs:
    @echo "Serving documentation..."
    cd docs && mkdocs serve -f mkdocs-base.yml

# Build documentation only
docs-build:
    @echo "Building documentation..."
    cd docs && mkdocs build -f mkdocs-base.yml

# =============================================================================
# Frontend
# =============================================================================

# Serve frontend (webpack dev server)
serve:
    @echo "Starting frontend dev server..."
    cd django_project/frontend && npm install --verbose && npm run serve

# Serve maputnik dev server
serve-maputnik:
    cd maputnik && npm install --verbose && npm run start

# Build maputnik for Django
build-maputnik:
    @echo "Building maputnik..."
    cd maputnik && npm install --verbose && npm run build-django
    python3 maputnik_html_to_django.py

# =============================================================================
# Docker
# =============================================================================

# Build Docker images
docker-build:
    @echo "Building Docker images..."
    docker compose -f deployment/docker-compose.yml build

# Remove all containers and volumes
docker-clean:
    @echo "Cleaning Docker resources..."
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml down -v --remove-orphans

# View Docker logs
docker-logs:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml logs -f

# =============================================================================
# Package Building
# =============================================================================

# Build Python package (wheel + sdist)
build:
    @echo "Building Python package..."
    python -m build

# Build wheel only
build-wheel:
    python -m build --wheel

# Build source distribution only
build-sdist:
    python -m build --sdist

# Clean build artifacts
clean-build:
    @echo "Cleaning build artifacts..."
    rm -rf dist/ build/ *.egg-info/ django_project/*.egg-info/

# Check package before publishing
publish-check:
    @echo "Checking package..."
    twine check dist/*

# =============================================================================
# Publishing
# =============================================================================

# Publish to TestPyPI
publish-test:
    @echo "Publishing to TestPyPI..."
    twine upload --repository testpypi dist/*

# Publish to PyPI
publish:
    @echo "Publishing to PyPI..."
    twine upload dist/*

# =============================================================================
# Versioning
# =============================================================================

# Show current version
version:
    @python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

# Bump patch version (0.0.X)
bump-patch:
    cz bump --increment PATCH

# Bump minor version (0.X.0)
bump-minor:
    cz bump --increment MINOR

# Bump major version (X.0.0)
bump-major:
    cz bump --increment MAJOR

# =============================================================================
# Release
# =============================================================================

# Generate changelog
changelog:
    @echo "Generating changelog..."
    git-cliff -o CHANGELOG.md

# Create a release (builds package, checks, and tags)
release version:
    @echo "Creating release {{version}}..."
    just changelog
    git add CHANGELOG.md
    git commit -m "chore: update changelog for {{version}}"
    git tag -a "v{{version}}" -m "Release {{version}}"
    just build
    just publish-check
    @echo "Release v{{version}} prepared. Run 'git push && git push --tags' to publish."

# Create GitHub release from latest tag
release-github:
    @echo "Creating GitHub release..."
    gh release create $(git describe --tags --abbrev=0) dist/* --generate-notes

# Full release workflow
release-full type="patch":
    @echo "Running full release workflow ({{type}})..."
    just bump-{{type}}
    just changelog
    just build
    @echo "Package built. Review and then run 'just publish' and 'just release-github'"

# =============================================================================
# Database
# =============================================================================

# Run Django migrations
migrate:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev python manage.py migrate

# Create Django migrations
makemigrations:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev python manage.py makemigrations

# Create superuser
createsuperuser:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec dev python manage.py createsuperuser

# Collect static files
collectstatic:
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml exec -T dev python manage.py collectstatic --noinput

# =============================================================================
# Utilities
# =============================================================================

# Initialize development environment
init:
    @echo "Initializing development environment..."
    cp -n deployment/.template.env deployment/.env || true
    cp -n deployment/docker-compose.override.template deployment/docker-compose.override.yml || true
    pre-commit install
    @echo "Environment initialized. Run 'just dev' to start."

# Full setup and start
setup: init docker-build dev wait-db dev-entrypoint dev-runserver
    @echo "Setup complete! Access the app at http://localhost:5000/"

# Clean everything
clean: clean-build docker-clean
    @echo "Cleaned all artifacts."
