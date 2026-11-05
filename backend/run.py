"""Development entry point for the RailCrowd Flask application.

Run from the repository root with:
    python -m backend.run
"""

import os

from backend.app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
