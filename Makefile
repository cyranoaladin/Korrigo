.PHONY: up down logs migrate superuser test shell init_pmf

KORRIGO_ENV_FILE ?= /etc/korrigo-ops/runtime.env
export KORRIGO_ENV_FILE
PROD_COMPOSE = bash scripts/prod_compose.sh

up:
	bash scripts/prod_up.sh

down:
	bash scripts/prod_down.sh

logs:
	$(PROD_COMPOSE) logs -f

migrate:
	$(PROD_COMPOSE) run --rm --no-deps -T backend python manage.py migrate --noinput

superuser:
	@echo "Creating superuser..."
	$(PROD_COMPOSE) run --rm backend python manage.py createsuperuser

test:
	@echo "Running Full Test Suite (Unit, Integration, E2E)..."
	$(PROD_COMPOSE) exec -T backend pytest

shell:
	$(PROD_COMPOSE) exec backend python manage.py shell

init_pmf:
	@echo "Initializing PMF Data (Users, Groups)..."
	$(PROD_COMPOSE) exec backend python manage.py init_pmf
