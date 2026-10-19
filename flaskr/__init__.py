import os

from flask import Flask


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_prefixed_env()
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "app_db.sqlite"),
    )

    if test_config is not None:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists. It usually is located at the project root.
    os.makedirs(app.instance_path, exist_ok=True)

    from . import db

    db.init_app(app)

    from . import errors

    errors.setup_error_handlers(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import cultivation_plots

    app.register_blueprint(cultivation_plots.bp)

    return app
