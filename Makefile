check-format:
	black --check --line-length 120 . ; \
	isort --check-only --profile black . ;

format:
	black --line-length 120 . ; \
	isort --profile black .

clean:
	rm -rf *.pyc

install:
	pip install -r requirements-dev.txt