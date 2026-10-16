# Instructions

## About the project

This project is an app that serves as a dashboard or management tool for cultivation plots.
It is a web app written in Python using the
[Flask](https://flask.palletsprojects.com/en/stable/) web framework.
The root of the app is the `flaskr` directory.

- Static assets live in the `flaskr/static` directory.
- View templates live in the `flaskr/templates` directory.
- The templates are written in [Jinja](https://jinja.palletsprojects.com/en/stable/).
- [Bootstrap](https://getbootstrap.com/docs/5.3/getting-started/introduction/) is the UI framework used in the view templates.
- The entrypoint of the app is in the `flaskr/__init__.py` file.
- The authentication logic is in the `flaskr/auth.py` file.
- The cultivation plot management logic is in the `flaskr/cultivation_plots.py` file.
- The database connection logic is in the `flaskr/db.py` file.
- The error handling logic is in the `flaskr/errors.py` file.
- The database schema is defined in the `flaskr/schema.sql` file.
- The tool to format Python code is [Black](https://black.readthedocs.io/).
- The tool to lint Python code is [Ruff](https://docs.astral.sh/ruff/).
- The tool to run the unit tests is [pytest](https://docs.pytest.org/en/stable/).

## Never do this

- Run `python` or any Python CLI tool without first checking if there is a virtual environment active by inspecting the `VIRTUAL_ENV` environment variable and seeing if the value of the variable matches with the project path. If there is not virtual environment active, activate it with the command `source .venv/bin/activate`. If
  the `.venv` file does not exist just create it using `python3 -m venv .venv`.
- Commit the `.env` file.
- Commit API keys or any other sensitive information.
- Install a Python module without updating the `requirements.txt` file right after using `pip freeze > requirements.txt`.
- Edit the `flaskr/instance` directory.
- Write long commit messages, messages should be short and simple, like `Make login page response` or `Remove useless log`.
- Commit without running the full suite unit tests first.
- Commit without formatting the changed files first (the Python files).
- Commit without linting the changed Python files first.

## Useful commands

- Install: `pip install -r requirements.txt`.
- Start: `bash scripts/start.sh`.
- Initialize the database: `bash scripts/init_db.sh`.
- Generate a secret to serve as value for the `FLASK_SECRET_KEY` environment variable in the `.env` file: `python scripts/print_secret.py`.
- Lint: `ruff check flaskr scripts`.
