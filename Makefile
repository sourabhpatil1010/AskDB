.PHONY: up down build logs backend-shell frontend-shell

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose up --build -d

logs:
	docker-compose logs -f

backend-shell:
	docker-compose exec backend /bin/bash

frontend-shell:
	docker-compose exec frontend /bin/sh
