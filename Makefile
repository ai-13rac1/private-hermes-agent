.PHONY: check build up down test
check:
	python3 -m unittest discover -s tests -p 'test_*.py'
	docker compose config --quiet
	python3 -m py_compile docker/*.py scripts/*.py tests/*.py
build: check
	docker compose build
up:
	python3 scripts/preflight.py
	docker compose up -d --wait bootstrap tor agent-net executor-net executor teep research-setup research-desk

down:
	docker compose down

test: check
	python3 scripts/preflight.py private-hermes-test
	python3 -u tests/smoke.py

.PHONY: research-setup
research-setup:
	docker compose run --rm research-setup

.PHONY: research-test
research-test: check
	python3 scripts/preflight.py private-hermes-research-test
	python3 -u tests/research_smoke.py
