check-format:
	black --check --line-length 120 . ; \
	isort --check-only --profile black . ;

format:
	black --line-length 120 . ; \
	isort --profile black .

clean:
	rm -rf *.pyc __pycache__ .pytest_cache .coverage .mypy_cache

install:
	pip install -r requirements-dev.txt && \
	pip install -r llm/requirements.txt && \
	pip install -r frontend/requirements.txt && \
	pip install -r db/requirements.txt

build-local:
	docker compose up -d