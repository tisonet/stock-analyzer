.PHONY: install install-backend install-frontend backend frontend test dev

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
