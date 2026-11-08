.PHONY: check build up down test
check:
	python3 -m unittest discover -s tests -p 'test_*.py'
	docker compose config --quiet
	python3 -m py_compile docker/*.py scripts/*.py tests/*.py
build: check
	docker compose build
up:
	python3 scripts/preflight.py
	docker compose up -d --wait bootstrap tor agent-net executor-net executor teep

down:
	docker compose down

test: check
	python3 scripts/preflight.py private-hermes-test
	python3 -u tests/smoke.py
