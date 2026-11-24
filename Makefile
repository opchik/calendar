VENV := backend/.venv
PYTHON := $(VENV)/bin/python

.PHONY: install db migrate backend frontend build up down logs check clean

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt
	npm ci

db:
	docker compose up -d db

migrate:
	cd backend && .venv/bin/alembic upgrade head

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	npm run dev

build:
	npm run build

up: build
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f calendar

check:
	$(PYTHON) -m compileall -q backend
	npm run build
	docker compose config >/dev/null

clean:
	rm -rf static .svelte-kit backend/.venv
