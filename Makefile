.DEFAULT_GOAL := check
.PHONY: init check build up down test
init:
	python3 scripts/init-config.py
check:
	python3 -m unittest discover -s tests -p 'test_*.py'
	python3 scripts/stack.py config
	docker compose -f compose.yaml -f compose.funnel.yaml config --quiet
	python3 -m compileall -q components scripts tests
build: init check
	python3 scripts/stack.py build
up: init
	python3 scripts/stack.py up

down:
	python3 scripts/stack.py down

test: check
	python3 scripts/preflight.py private-hermes-test
	python3 -u tests/smoke.py

.PHONY: x402_treazury-setup
x402_treazury-setup: init
	python3 scripts/stack.py compose run --rm x402_treazury-setup

.PHONY: x402_treazury-test
x402_treazury-test: check
	python3 scripts/preflight.py private-hermes-x402-treazury-test
	python3 -u tests/x402_treazury_smoke.py

.PHONY: webapp-credentials webapp-rotate webapp-test
webapp-credentials: init
webapp-rotate: init
	python3 scripts/webapp-credentials.py --rotate
webapp-test: check
	python3 scripts/preflight.py private-hermes-webapp-test --funnel
	python3 -u tests/webapp_smoke.py

.PHONY: chat gateway
chat:
	python3 scripts/stack.py compose run --rm hermes chat
gateway:
	python3 scripts/stack.py compose up -d hermes
