import functools
import re

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


def validate_password(password, password_confirmation):
    if not password:
        return "The password is required"
    if len(password) < 12:
        return "The length of the password must be at least 12 characters"
    if len(password) > 32:
        return "The length of the password must be at most 32 characters"
    if not re.search(r"\d", password):
        return "The password must have at least one number"
    if not re.search(r"[a-z]", password):
        return "The password must have at least one lowercase letter"
    if not re.search(r"[A-Z]", password):
        return "The password must have at least one uppercase letter"
    if not re.search(r"[^a-zA-Z0-9\s]", password):
        return "The password must have at least one special character"
    if not password_confirmation:
        return "The password confirmation is required"
    if password != password_confirmation:
        return "The password and the password confirmation must be equal"
    return None

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registers a user account."""

    # Render the sign-up form.

    if request.method == "GET":
        return render_template("auth/register.html.jinja")

    # Validate the username

    username = request.form.get('username')
    if not username:
        flash('The username is required', 'danger')
        return render_template('auth/register.html.jinja', form=request.form), 400
    if username.strip() == '':
        flash('The username is just whitespace', 'danger')
        return render_template('auth/register.html.jinja', form=request.form), 400
    if len(username) < 3:
        flash('The length of the username must be greater than 3', 'danger')
        return render_template('auth/register.html.jinja', form=request.form), 400
    if len(username) > 50:
        flash('The length of the username must be less than 50', 'danger')
        return render_template('auth/register.html.jinja', form=request.form), 400

    # Get the password, it should contain at least 1 digit, 1 letter,
    # a special character and that the password confirmation is equal
    # to the given password. The length of the password should be
    # at least 12 and at most 32.

    password = request.form.get('password')
    error_msg = validate_password(password, request.form.get('password_confirmation'))
    if error_msg:
        flash(error_msg, 'danger')
        return render_template("auth/register.html.jinja", form=request.form), 400

    # Now save the user in the database.

    db = get_db()
    cursor = db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password, 'pbkdf2:sha256')), # type: ignore
    )
    db.commit()
    user_id = cursor.lastrowid
    cursor.close()

    # And start a session for the user.
    session["user_id"] = user_id

    return redirect(url_for("cultivation_plots.index"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Logs in the user account."""

    # Render the login form.

    if request.method == "GET":
        return render_template("auth/login.html.jinja")

    # Logs in the user if the credentials are correct.

    # We clear the session first.

    session.clear()

    # And now we validate the credentials.

    username = request.form.get("username")
    if not username:
        flash("Missing username", "danger")
        return render_template("auth/login.html.jinja"), 400

    password = request.form.get("password")
    if not password:
        flash("Missing password", "danger")
        return render_template("auth/login.html.jinja"), 400

    # Now try to get the user and update the session.

    db = get_db()
    cursor = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    some_user = cursor.fetchone()
    cursor.close()
    if not some_user:
        flash("Invalid username", "danger")
        return render_template("auth/login.html.jinja", form=request.form), 401
    if not check_password_hash(some_user["password_hash"], password):
        flash("Invalid password", "danger")
        return render_template("auth/login.html.jinja", form=request.form), 401
    session["user_id"] = some_user["id"]
    flash("You're logged in.", "success")
    if "redirect_to" in request.args:
        return redirect(request.args["redirect_to"])
    return redirect(url_for("cultivation_plots.index"))



@bp.before_app_request
def load_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
                'SELECT * FROM users WHERE id = ?', (user_id,)
                ).fetchone()


@bp.route('/logout', methods=['POST'])
def logout():
    """Logs out the user."""

    session.clear()
    flash("You're logged out", "info")
    return redirect(url_for("auth.login"))


def login_required(view):
    """Decorator for routes that require a session."""

    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(
                    url_for("auth.login",
                            redirect_to=request.full_path)
                    )
        return view(*args, **kwargs)

    return wrapped_view


@bp.route('/users/<int:id>')
@login_required
def account(id):
    if id != g.user['id']:
        return abort(401)
    return render_template('/auth/account.html.jinja', user=g.user)


@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    if id != g.user['id']:
        return abort(401)
    if request.method == 'GET':
        return render_template('/auth/edit.html.jinja', user=g.user)
    username = request.form.get('username')
    if not username or username.strip() == '':
        flash('The username is required', 'danger')
        return render_template('/auth/edit.html.jinja', user=g.user), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, id))
    db.commit()
    cursor.close()
    flash('Account updated', 'success')
    return redirect(url_for('auth.account', id=id))


@bp.route('/users/<int:id>/change_password', methods=['GET', 'POST'])
@login_required
def change_password(id):
    if id != g.user['id']:
        return abort(401)
    if request.method == 'GET':
        return render_template('/auth/change_password.html.jinja', user=g.user)
    current_password = request.form.get('current_password')
    if not current_password:
        flash('The current password is required', 'danger')
        return render_template('/auth/change_password.html.jinja', user=g.user), 400
    if not check_password_hash(g.user['password_hash'], current_password):
        flash('The current password is wrong', 'danger')
        return render_template('/auth/change_password.html.jinja', user=g.user), 401
    new_password = request.form.get('password')
    error_msg = validate_password(new_password, request.form.get('password_confirmation'))
    if error_msg:
        flash(error_msg, 'danger')
        return render_template('/auth/change_password.html.jinja', user=g.user), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_password), id)) # type: ignore
    db.commit()
    cursor.close()
    flash('Password changed', 'success')
    return redirect(url_for('auth.account', id=id))


@bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_account(id):
    if id != g.user['id']:
        return abort(401)
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('auth.login'))
