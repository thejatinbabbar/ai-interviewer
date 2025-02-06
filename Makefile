check-format:
	black --check --line-length 120 . ; \
	isort --check-only . ;

format:
	black --line-length 120 . ; \
	isort .

clean:
	rm -rf *.pyc

install:
	pip install -r requirements-dev.txt