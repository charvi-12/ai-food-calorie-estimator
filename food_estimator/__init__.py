import os
from pathlib import Path

from flask import Flask, jsonify, render_template
from werkzeug.exceptions import RequestEntityTooLarge

from .database import initialize_database, register_database
from .routes import bp

PROJECT_DIR = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    test_config = test_config or {}
    instance_path = test_config.get("INSTANCE_PATH")
    flask_options = {
        "instance_relative_config": True,
        "static_folder": str(PROJECT_DIR / "static"),
        "template_folder": str(PROJECT_DIR / "templates"),
    }
    if instance_path:
        flask_options["instance_path"] = instance_path
        flask_options["instance_relative_config"] = False
    app = Flask(__name__, **flask_options)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "food_estimator.sqlite3"),
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        DEBUG=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
    app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    initialize_database(app.config["DATABASE"])
    register_database(app)
    app.register_blueprint(bp)

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error):
        return render_template(
            "error.html",
            message="That image is larger than the 8 MB upload limit. Choose a smaller image.",
        ), 413

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="That page could not be found."), 404

    @app.errorhandler(500)
    def internal_error(_error):
        app.logger.exception("An unhandled application error occurred.")
        return render_template(
            "error.html",
            message="Something went wrong. Please try again; see the application log for details.",
        ), 500

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app
