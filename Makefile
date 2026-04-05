# Comandos abreviados para Performance Metrics Engine (PME)
# Uso: make <comando>

AUTH=poetry run python src/api/auth_setup.py
SYNC=poetry run python src/services/sync.py
STATUS=poetry run python src/status.py
DASHBOARD=poetry run streamlit run src/dashboard.py

auth:
	$(AUTH)

sync:
	$(SYNC)

status:
	$(STATUS)

dashboard:
	$(DASHBOARD)

install:
	poetry install

.PHONY: auth sync status dashboard install
