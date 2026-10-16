import pytest

from flaskr import create_app
from flaskr.db import init_db


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
