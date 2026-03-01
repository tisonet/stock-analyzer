.PHONY: install install-backend install-frontend backend frontend test dev cache-clear cache-list

install: install-backend install-frontend

install-backend:
	python3 -m pip install -r requirements.txt

install-frontend:
	cd src/frontend && npm install

backend:
	python3 -m uvicorn src.backend.api.routes:app --reload --port 8000

frontend:
	cd src/frontend && npm run dev

test:
	python3 -m pytest tests/ -v

dev:
	make -j2 backend frontend

# Clear cache for a specific ticker:  make cache-clear TICKER=AAPL
# Clear entire cache:                  make cache-clear
TICKER ?=
cache-clear:
	python3 scripts/cache_clear.py "$(TICKER)"

cache-list:
	python3 scripts/cache_list.py
