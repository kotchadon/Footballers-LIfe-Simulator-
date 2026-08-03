from pathlib import Path

from flask import Flask

from .db import close_db, init_db
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        DATABASE=str(Path(app.instance_path) / "footy.sqlite3"),
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)

    with app.app_context():
        init_db()

    return app

