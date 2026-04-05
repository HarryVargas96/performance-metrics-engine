SYNC=poetry run python src/services/sync.py
STATUS=poetry run python src/status.py
DASHBOARD=poetry run streamlit run src/dashboard.py

sync:
	$(SYNC)

status:
	$(STATUS)

dashboard:
	$(DASHBOARD)

install:
	poetry install

.PHONY: sync status dashboard install
