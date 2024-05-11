export COMPOSE_FILE=deployment/docker-compose.yml:deployment/docker-compose.override.yml
SHELL := /bin/bash

build:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Building in production mode"
	@echo "------------------------------------------------------------------"
	@docker-compose build

up:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Running in production mode"
	@echo "------------------------------------------------------------------"
	@docker-compose ${ARGS} up -d nginx django

dev:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Running in dev mode"
	@echo "------------------------------------------------------------------"
	@docker-compose ${ARGS} up -d dev

shell:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Shelling in in production mode"
	@echo "------------------------------------------------------------------"
	@docker-compose exec django /bin/bash

dev-entrypoint:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Running in DEVELOPMENT mode"
	@echo "------------------------------------------------------------------"
	@docker-compose ${ARGS} exec -T dev "/home/web/django_project/entrypoint.sh"

dev-runserver:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Start django runserver in dev container"
	@echo "------------------------------------------------------------------"
	@docker-compose $(ARGS) exec -T dev bash -c "nohup python manage.py runserver 0.0.0.0:5000 &"

dev-load-demo-data:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Load demo data for dev"
	@echo "------------------------------------------------------------------"

dev-test:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Run tests"
	@echo "------------------------------------------------------------------"
	@docker-compose exec -T dev python manage.py collectstatic --noinput
	@docker-compose exec -T dev python manage.py test --keepdb --noinput

serve:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Execute webpack serve command"
	@echo "------------------------------------------------------------------"
	@cd django_project/frontend; npm install --verbose; npm run serve;

down:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Removing production instance!!! "
	@echo "------------------------------------------------------------------"
	@docker-compose down

test-flake:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Running flake8"
	@echo "------------------------------------------------------------------"
	@pip install flake8==6.0.0
	@pip install flake8-docstrings
	@python3 -m flake8 django_project

wait-db:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Check database is ready or not"
	@echo "------------------------------------------------------------------"
	@docker-compose ${ARGS} exec -T db su - postgres -c "until pg_isready; do sleep 5; done"

sleep:
	@echo
	@echo "------------------------------------------------------------------"
	@echo "Sleep for 50 seconds"
	@echo "------------------------------------------------------------------"
	@sleep 50
	@echo "Done"