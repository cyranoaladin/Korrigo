.PHONY: up down logs migrate superuser test shell

up:
	docker-compose -f infra/docker/docker-compose.prod.yml up --build -d

down:
	docker-compose -f infra/docker/docker-compose.prod.yml down

logs:
	docker-compose -f infra/docker/docker-compose.prod.yml logs -f

migrate:
	docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate

superuser:
	@echo "Creating superuser..."
	docker-compose -f infra/docker/docker-compose.prod.yml run --rm backend python manage.py createsuperuser

test:
	@echo "Running Full Test Suite (Unit, Integration, E2E)..."
	docker-compose -f infra/docker/docker-compose.prod.yml exec -T backend pytest

shell:
	docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py shell

init_pmf:
	@echo "Initializing PMF Data (Users, Groups)..."
	docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py init_pmf
