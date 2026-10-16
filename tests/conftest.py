import pytest
from werkzeug.security import generate_password_hash

from flaskr import create_app
from flaskr.db import get_db, init_db


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite"),
            "SECRET_KEY": "test",
        }
    )

    with app.app_context():
        init_db()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    username = "test-user"
    password = "ValidPassword1!"

    with app.app_context():
        cursor = get_db().execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password, "pbkdf2:sha256")),
        )
        user_id = cursor.lastrowid
        get_db().commit()

    return {"id": user_id, "username": username, "password": password}


@pytest.fixture
def authenticated_client(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user["id"]

    return client
