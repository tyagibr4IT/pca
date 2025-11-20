.PHONY: build run lint test

build:
	podman build -t cloudopt/backend:local -f Dockerfile .

run:
	podman run --rm -p 8000:8000 --env-file .env -v $(PWD)/app:/app/app cloudopt/backend:local

lint:
	black app || true
	flake8 app || true
	mypy app || true

test:
	pytest -q