# Local setup and first run

For Windows, double-click `RUN_RAILCROWD.bat`. It creates a Python 3.12 virtual environment, installs requirements when missing, initializes the SQLite database, inserts demo catalog rows and starts Flask.

Alternatively, in PowerShell from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python setup.py
python -m flask --app backend.run run --debug
```

Open `http://127.0.0.1:5000`.

Demo accounts:

- Admin: `admin` / `Admin@12345`
- Passenger: `demo` / `Demo@12345`

The setup script is idempotent. It also adds the nullable moderation audit columns to a legacy local SQLite `crowd_reports` table created before the admin moderation feature. Back up the `instance` directory before experimenting with database changes.

To check the service:

- `http://127.0.0.1:5000/health`
- `http://127.0.0.1:5000/trains/`
- `http://127.0.0.1:5000/trains/12727`
- `http://127.0.0.1:5000/trains/12727/crowd.json`
