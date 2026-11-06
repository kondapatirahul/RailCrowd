# Increment 27 commit plan — exactly 8 meaningful commits

1. `backend/app/modules/trains/services/saved_train_service.py` — `added saved train catalogue service`
2. `backend/app/modules/trains/routes.py` — `implemented passenger save and remove train actions`
3. `frontend/templates/public/train_search.html` — `integrated saved train actions into search results`
4. `frontend/templates/public/train_detail.html` — `added saved train control to train details`
5. `frontend/static/css/saved_train_catalog.css` — `styled saved train controls across catalogue pages`
6. `tests/unit/test_saved_train_service.py` — `tested saved train lookup service`
7. `tests/integration/test_saved_train_catalog_actions.py` — `tested saved train catalogue actions`
8. `docs/INCREMENT_27_SAVED_TRAINS_IN_CATALOG.md` and `docs/INCREMENT_27_COMMIT_PLAN.md` — `documented saved train catalogue integration`

No database migration is required. Exactly eight commits; do not create empty commits.
