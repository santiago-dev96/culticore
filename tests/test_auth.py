import pytest
from werkzeug.security import check_password_hash

from flaskr.auth import validate_password
from flaskr.db import get_db


@pytest.mark.parametrize(
    ("password", "confirmation", "expected_error"),
    [
        ("", "", "The password is required"),
        ("Short1!", "Short1!", "The length of the password must be at least 12 characters"),
        (
            "A" * 32 + "1a!",
            "A" * 32 + "1a!",
            "The length of the password must be at most 32 characters",
        ),
        ("ValidPassword!", "ValidPassword!", "The password must have at least one number"),
        ("VALIDPASSWORD1!", "VALIDPASSWORD1!", "The password must have at least one lowercase letter"),
        ("validpassword1!", "validpassword1!", "The password must have at least one uppercase letter"),
        ("ValidPassword12", "ValidPassword12", "The password must have at least one special character"),
        ("ValidPassword1!", "", "The password confirmation is required"),
        ("ValidPassword1!", "DifferentPassword1!", "The password and the password confirmation must be equal"),
        ("ValidPassword1!", "ValidPassword1!", None),
    ],
)
def test_validate_password(password, confirmation, expected_error):
    assert validate_password(password, confirmation) == expected_error


def test_login_page(client):
    response = client.get("/auth/login")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("form_data", "expected_message"),
    [
        ({"password": "ValidPassword1!"}, "The username is required"),
        ({"username": "   ", "password": "ValidPassword1!"}, "The username is just whitespace"),
        ({"username": "ab", "password": "ValidPassword1!"}, "The length of the username must be greater than 3"),
        (
            {"username": "u" * 51, "password": "ValidPassword1!"},
            "The length of the username must be less than 50",
        ),
        ({"username": "new-user", "password": "weak", "password_confirmation": "weak"},
         "The length of the password must be at least 12 characters"),
    ],
)
def test_register_rejects_invalid_input(client, app, form_data, expected_message):
    response = client.post("/auth/register", data=form_data)

    assert response.status_code == 400
    assert expected_message.encode() in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_register_creates_user_and_starts_session(client, app):
    response = client.post(
        "/auth/register",
        data={
            "username": "new-user",
            "password": "ValidPassword1!",
            "password_confirmation": "ValidPassword1!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as session:
        assert session["user_id"] == 1
    with app.app_context():
        registered_user = get_db().execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            ("new-user",),
        ).fetchone()
    assert registered_user["username"] == "new-user"
    assert check_password_hash(registered_user["password_hash"], "ValidPassword1!")


@pytest.mark.parametrize(
    ("form_data", "expected_message"),
    [
        ({"password": "ValidPassword1!"}, "Missing username"),
        ({"username": "test-user"}, "Missing password"),
        ({"username": "unknown", "password": "ValidPassword1!"}, "Invalid username"),
        ({"username": "test-user", "password": "WrongPassword1!"}, "Invalid password"),
    ],
)
def test_login_rejects_invalid_credentials(
    client, user, form_data, expected_message
):
    response = client.post("/auth/login", data=form_data)

    assert response.status_code in (400, 401)
    assert expected_message.encode() in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_login_starts_session_and_redirects_to_dashboard(client, user):
    response = client.post(
        "/auth/login",
        data={"username": user["username"], "password": user["password"]},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as session:
        assert session["user_id"] == user["id"]


def test_logout_clears_session(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user["id"]

    response = client.post("/auth/logout")

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_login_required_redirects_anonymous_user(client):
    response = client.get("/auth/users/1")

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login?redirect_to=/auth/users/1?"


def test_account_rejects_access_to_another_user(authenticated_client, user):
    response = authenticated_client.get(f"/auth/users/{user['id'] + 1}")

    assert response.status_code == 401


def test_edit_account_updates_username(authenticated_client, user, app):
    response = authenticated_client.post(
        f"/auth/users/{user['id']}/edit", data={"username": "updated-user"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/auth/users/{user['id']}"
    with app.app_context():
        row = get_db().execute(
            "SELECT username FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    assert row["username"] == "updated-user"


@pytest.mark.parametrize("username", ["", "   "])
def test_edit_account_rejects_empty_username(authenticated_client, user, username):
    response = authenticated_client.post(
        f"/auth/users/{user['id']}/edit", data={"username": username}
    )

    assert response.status_code == 400


def test_change_password_updates_password(authenticated_client, user, app):
    new_password = "AnotherValid1!"
    response = authenticated_client.post(
        f"/auth/users/{user['id']}/change_password",
        data={
            "current_password": user["password"],
            "password": new_password,
            "password_confirmation": new_password,
        },
    )

    assert response.status_code == 302
    with app.app_context():
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    assert check_password_hash(row["password_hash"], new_password)


def test_change_password_rejects_wrong_current_password(
    authenticated_client, user
):
    response = authenticated_client.post(
        f"/auth/users/{user['id']}/change_password",
        data={
            "current_password": "WrongPassword1!",
            "password": "AnotherValid1!",
            "password_confirmation": "AnotherValid1!",
        },
    )

    assert response.status_code == 401


def test_delete_account_removes_user(authenticated_client, user, app):
    response = authenticated_client.post(f"/auth/users/{user['id']}/delete")

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    with app.app_context():
        assert (
            get_db()
            .execute("SELECT COUNT(*) FROM users WHERE id = ?", (user["id"],))
            .fetchone()[0]
            == 0
        )
