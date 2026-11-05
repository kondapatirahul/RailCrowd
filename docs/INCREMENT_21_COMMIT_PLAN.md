# Increment 21 — 8 meaningful commits

Branch: `public_train_search`

1. `added station database model` — `backend/app/models/station.py`
2. `added train and route stop models` — `backend/app/models/train.py`
3. `created train catalog search service` — `backend/app/modules/trains/services/`
4. `implemented public train search and detail routes` — `backend/app/modules/trains/`
5. `created public train search interface` — `frontend/templates/public/train_search.html`
6. `added train detail and empty state pages` — `frontend/templates/public/train_detail.html`, `frontend/templates/public/train_not_found.html`
7. `added responsive train search styling` — `frontend/static/css/train_search.css`
8. `added train search tests and documentation` — `tests/integration/test_public_train_search.py`, `docs/`

The database migration is generated locally and should be staged with commit 8. If your migration is generated after the first seven commits, stage it together with the test and documentation files for commit 8.
