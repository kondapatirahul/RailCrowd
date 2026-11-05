# Increment 21 — Public Train Search & Train Catalog

## Included
- `Station`, `Train`, and `TrainStop` SQLAlchemy models.
- Public train search by train number, train name, source/destination station name or code.
- Train detail page with ordered route stops.
- Empty and not-found states.
- Responsive train search styling.
- Catalog service kept separate from route handlers.

## Required application integration
The application factory must register the new blueprint after extensions are initialized:

```python
from backend.app.modules.trains import trains_bp
app.register_blueprint(trains_bp, url_prefix="/trains")
```

Import the models after `db.init_app(app)` so Flask-Migrate discovers them:

```python
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop
```

If your factory uses relative imports, adapt the import paths to match its existing style. Do not replace the complete factory file; add these imports and registration alongside the existing blueprints.

## Template and CSS integration
The templates extend `layouts/base.html`. Add the stylesheet to the base layout's existing stylesheet block:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/train_search.css') }}">
```

Add a navigation link if desired:

```html
<a href="{{ url_for('trains.search') }}">Find Trains</a>
```

## Migration
After merging the increment and integrating the blueprint/model imports:

```powershell
flask --app backend.run db migrate -m "add train and station catalog"
```

Review the generated migration under `backend/migrations/versions/`, then:

```powershell
flask --app backend.run db upgrade
flask --app backend.run db current
```

Do not run `db init` when the existing migration repository is already configured. Confirm `MIGRATIONS_DIR` points to `backend/migrations`.

## Optional seed data
No unverified train schedules are inserted automatically. Add only verified catalog records. A small development seed script can be added in a later increment.

## Tests
```powershell
pytest tests/integration/test_public_train_search.py -q
```

## Data accuracy
This catalog is not an official live railway timetable. Do not represent catalog values as live running status, official schedule, or passenger occupancy.
