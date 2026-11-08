.DEFAULT_GOAL := check
.PHONY: init check build up down test
init:
	python3 scripts/init-config.py
check:
	python3 -m unittest discover -s tests -p 'test_*.py'
	docker compose config --quiet
	python3 -m compileall -q components scripts tests
build: init check
	docker compose build
up: init
	python3 scripts/preflight.py
	docker compose up -d --wait bootstrap tor agent-net executor-net executor teep x402_treazury-setup x402_treazury

down:
	docker compose down

test: check
	python3 scripts/preflight.py private-hermes-test
	python3 -u tests/smoke.py

.PHONY: x402_treazury-setup
x402_treazury-setup: init
	docker compose run --rm x402_treazury-setup

.PHONY: x402_treazury-test
x402_treazury-test: check
	python3 scripts/preflight.py private-hermes-x402-treazury-test
	python3 -u tests/x402_treazury_smoke.py
