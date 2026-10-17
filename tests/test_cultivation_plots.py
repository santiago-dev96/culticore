import pytest

from flaskr.db import get_db


@pytest.fixture
def cultivation_plot(app, user):
    with app.app_context():
        cursor = get_db().execute(
            """
            INSERT INTO cultivation_plots
                (user_id, name, crop, number_of_plants, water_spent, harvest)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user["id"], "Back garden", "tomato", 5, 10.0, 2.0),
        )
        plot_id = cursor.lastrowid
        get_db().commit()

    return plot_id


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/"),
        ("get", "/new_cultivation_plot"),
        ("post", "/new_cultivation_plot"),
        ("get", "/cultivation_plots/1"),
        ("get", "/cultivation_plots/1/log_operation"),
        ("post", "/cultivation_plots/1/log_operation"),
        ("get", "/cultivation_plots/1/operations"),
        ("get", "/cultivation_plots/1/edit"),
        ("post", "/cultivation_plots/1/edit"),
        ("post", "/cultivation_plots/1/delete"),
    ],
)
def test_cultivation_plot_routes_require_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login?redirect_to=")


def test_dashboard_shows_only_current_users_plots(authenticated_client, app, user):
    with app.app_context():
        other_user_id = (
            get_db()
            .execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("other-user", "unused"),
            )
            .lastrowid
        )
        get_db().execute(
            "INSERT INTO cultivation_plots (user_id, name, crop) VALUES (?, ?, ?)",
            (user["id"], "My plot", "carrot"),
        )
        get_db().execute(
            "INSERT INTO cultivation_plots (user_id, name, crop) VALUES (?, ?, ?)",
            (other_user_id, "Their plot", "potato"),
        )
        get_db().commit()

    response = authenticated_client.get("/")

    assert response.status_code == 200
    assert b"My plot" in response.data
    assert b"Their plot" not in response.data


def test_new_cultivation_plot_page(authenticated_client):
    response = authenticated_client.get("/new_cultivation_plot")

    assert response.status_code == 200
    assert b"New cultivation plot" in response.data


@pytest.mark.parametrize(
    ("form_data", "expected_message"),
    [
        ({"crop": "tomato"}, "The name of the plot is required"),
        ({"name": "Back garden"}, "The crop is required"),
    ],
)
def test_new_cultivation_plot_rejects_missing_required_fields(
    authenticated_client, app, form_data, expected_message
):
    response = authenticated_client.post("/new_cultivation_plot", data=form_data)

    assert response.status_code == 400
    assert expected_message.encode() in response.data
    with app.app_context():
        assert (
            get_db().execute("SELECT COUNT(*) FROM cultivation_plots").fetchone()[0]
            == 0
        )


def test_new_cultivation_plot_creates_plot_and_initial_operation(
    authenticated_client, app, user
):
    response = authenticated_client.post(
        "/new_cultivation_plot",
        data={"name": "Kitchen garden", "crop": "basil"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT * FROM cultivation_plots WHERE name = ?", ("Kitchen garden",)
            )
            .fetchone()
        )
        operation = (
            get_db()
            .execute(
                "SELECT * FROM operations WHERE cultivation_plot_id = ?", (plot["id"],)
            )
            .fetchone()
        )

    assert plot["user_id"] == user["id"]
    assert plot["crop"] == "basil"
    assert plot["number_of_plants"] == 0
    assert operation["number_of_plants"] == 0
    assert operation["water_spent"] == 0
    assert operation["harvest"] == 0


@pytest.mark.parametrize("number_of_plants", ["-4", "not-a-number"])
def test_new_cultivation_plot_normalizes_invalid_plant_counts(
    authenticated_client, app, number_of_plants
):
    response = authenticated_client.post(
        "/new_cultivation_plot",
        data={
            "name": "Kitchen garden",
            "crop": "basil",
            "number-of-plants": number_of_plants,
        },
    )

    assert response.status_code == 302
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT number_of_plants FROM cultivation_plots WHERE name = ?",
                ("Kitchen garden",),
            )
            .fetchone()
        )

    assert plot["number_of_plants"] == 0


def test_cultivation_plot_page_returns_plot_and_operations(
    authenticated_client, app, cultivation_plot
):
    with app.app_context():
        get_db().executemany(
            """
            INSERT INTO operations
                (cultivation_plot_id, number_of_plants, water_spent, harvest, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (cultivation_plot, 1, 2.0, 3.0, "2025-01-01 00:00:00"),
                (cultivation_plot, 2, 4.0, 6.0, "2025-01-02 00:00:00"),
            ],
        )
        get_db().commit()

    response = authenticated_client.get(f"/cultivation_plots/{cultivation_plot}")

    assert response.status_code == 200
    assert b"Back garden" in response.data
    assert b"Harvest trends" in response.data


def test_cultivation_plot_page_returns_404_for_unknown_plot(authenticated_client):
    response = authenticated_client.get("/cultivation_plots/999")

    assert response.status_code == 404


def test_log_operation_page(authenticated_client, cultivation_plot):
    response = authenticated_client.get(
        f"/cultivation_plots/{cultivation_plot}/log_operation"
    )

    assert response.status_code == 200
    assert b"Log operation" in response.data
    assert b" required" not in response.data
    assert b'text-danger">*</span>' not in response.data
    assert (
        b'<button type="submit" class="btn btn-primary" disabled>Submit</button>'
        in response.data
    )
    assert b"input.value === ''" in response.data


@pytest.mark.parametrize(
    "form_data",
    [
        {},
        {"number_of_plants": "0", "water_spent": "0", "harvest": "0"},
        {"number_of_plants": "", "water_spent": "0"},
    ],
)
def test_log_operation_rejects_all_missing_or_zero_values(
    authenticated_client, app, cultivation_plot, form_data
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/log_operation", data=form_data
    )

    assert response.status_code == 400
    assert b"At least one operation value must be non-zero" in response.data
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT number_of_plants, water_spent, harvest FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )
        operation_count = (
            get_db()
            .execute(
                "SELECT COUNT(*) FROM operations WHERE cultivation_plot_id = ?",
                (cultivation_plot,),
            )
            .fetchone()[0]
        )

    assert tuple(plot) == (5, 10.0, 2.0)
    assert operation_count == 0


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("number_of_plants", "many", "The number of plants must be a whole number"),
        (
            "water_spent",
            "a lot",
            "The amount of water must be a number greater than zero",
        ),
        ("harvest", "a lot", "The harvest must be a number greater than zero"),
    ],
)
def test_log_operation_rejects_non_numeric_values(
    authenticated_client, app, cultivation_plot, field, value, expected_message
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/log_operation",
        data={field: value},
    )

    assert response.status_code == 400
    assert expected_message.encode() in response.data
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT number_of_plants, water_spent, harvest FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )
        operation_count = (
            get_db()
            .execute(
                "SELECT COUNT(*) FROM operations WHERE cultivation_plot_id = ?",
                (cultivation_plot,),
            )
            .fetchone()[0]
        )

    assert tuple(plot) == (5, 10.0, 2.0)
    assert operation_count == 0


def test_log_operation_creates_record_and_updates_plot_totals(
    authenticated_client, app, cultivation_plot
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/log_operation",
        data={"number_of_plants": "-2", "water_spent": "3.5", "harvest": "1.25"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/cultivation_plots/{cultivation_plot}"
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT number_of_plants, water_spent, harvest FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )
        operation = (
            get_db()
            .execute(
                """
            SELECT number_of_plants, water_spent, harvest
            FROM operations WHERE cultivation_plot_id = ?
            """,
                (cultivation_plot,),
            )
            .fetchone()
        )

    assert tuple(plot) == (3, 13.5, 3.25)
    assert tuple(operation) == (-2, 3.5, 1.25)


def test_log_operation_accepts_partial_input(
    authenticated_client, app, cultivation_plot
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/log_operation",
        data={"water_spent": "3.5"},
    )

    assert response.status_code == 302
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT number_of_plants, water_spent, harvest FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )
        operation = (
            get_db()
            .execute(
                """
            SELECT number_of_plants, water_spent, harvest
            FROM operations WHERE cultivation_plot_id = ?
            """,
                (cultivation_plot,),
            )
            .fetchone()
        )

    assert tuple(plot) == (5, 13.5, 2.0)
    assert tuple(operation) == (0, 3.5, 0.0)


@pytest.mark.parametrize(
    "path_suffix",
    ["", "/log_operation", "/operations", "/edit", "/delete"],
)
def test_cultivation_plot_routes_return_404_for_unknown_plot(
    authenticated_client, path_suffix
):
    method = "post" if path_suffix == "/delete" else "get"

    response = getattr(authenticated_client, method)(
        f"/cultivation_plots/999{path_suffix}"
    )

    assert response.status_code == 404


def test_operations_page_lists_operations_newest_first(
    authenticated_client, app, cultivation_plot
):
    with app.app_context():
        get_db().executemany(
            """
            INSERT INTO operations
                (cultivation_plot_id, number_of_plants, water_spent, harvest, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (cultivation_plot, 1, 2.0, 3.0, "2025-01-01 00:00:00"),
                (cultivation_plot, 2, 4.0, 6.0, "2025-01-02 00:00:00"),
            ],
        )
        get_db().commit()

    response = authenticated_client.get(
        f"/cultivation_plots/{cultivation_plot}/operations"
    )

    assert response.status_code == 200
    assert response.data.index(b"2025-01-02") < response.data.index(b"2025-01-01")


def test_edit_cultivation_plot_page(authenticated_client, cultivation_plot):
    response = authenticated_client.get(f"/cultivation_plots/{cultivation_plot}/edit")

    assert response.status_code == 200
    assert b"Back garden" in response.data


@pytest.mark.parametrize(
    "form_data",
    [
        {"name": ""},
        {"name": "   ", "crop": "tomato"},
        {"name": "Back garden", "crop": " "},
    ],
)
def test_edit_cultivation_plot_rejects_blank_required_fields(
    authenticated_client, app, cultivation_plot, form_data
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/edit", data=form_data
    )

    assert response.status_code == 400
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT name, crop FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )

    assert tuple(plot) == ("Back garden", "tomato")


def test_edit_cultivation_plot_updates_name_and_crop(
    authenticated_client, app, cultivation_plot
):
    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/edit",
        data={"name": "Greenhouse", "crop": "pepper"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/cultivation_plots/{cultivation_plot}"
    with app.app_context():
        plot = (
            get_db()
            .execute(
                "SELECT name, crop FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()
        )

    assert tuple(plot) == ("Greenhouse", "pepper")


def test_delete_cultivation_plot_removes_plot_and_operations(
    authenticated_client, app, cultivation_plot
):
    with app.app_context():
        get_db().execute(
            """
            INSERT INTO operations
                (cultivation_plot_id, number_of_plants, water_spent, harvest)
            VALUES (?, ?, ?, ?)
            """,
            (cultivation_plot, 1, 2.0, 3.0),
        )
        get_db().commit()

    response = authenticated_client.post(
        f"/cultivation_plots/{cultivation_plot}/delete"
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT COUNT(*) FROM cultivation_plots WHERE id = ?",
                (cultivation_plot,),
            )
            .fetchone()[0]
            == 0
        )
        assert (
            get_db()
            .execute(
                "SELECT COUNT(*) FROM operations WHERE cultivation_plot_id = ?",
                (cultivation_plot,),
            )
            .fetchone()[0]
            == 0
        )
