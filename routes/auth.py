import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)
from database import get_db
from utils import (
    generate_otp,
    otp_expiry,
    issue_verification_code,
    send_password_reset_email,
)


auth_bp = Blueprint("auth", __name__)


# -------------------------
# REGISTER
# -------------------------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("auth.register"))

        db = get_db()

        try:

            cursor = db.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    email_verified
                )
                VALUES (?, ?, ?, 0)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                ),
            )


            db.execute(
                """
                INSERT INTO wallets
                (
                    user_id
                )
                VALUES (?)
                """,
                (cursor.lastrowid,),
            )


            db.commit()


        except sqlite3.IntegrityError:

            flash(
                "An account with that email already exists.",
                "danger"
            )

            return redirect(
                url_for("auth.register")
            )


        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE id=?
            """,
            (cursor.lastrowid,),
        ).fetchone()


        session.clear()

        session["pending_verification_user_id"] = user["id"]

        issue_verification_code(user)


        return redirect(
            url_for("auth.verify_email")
        )


    return render_template(
        "auth/register.html"
    )



# -------------------------
# VERIFY EMAIL
# -------------------------

@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():

    user_id = session.get(
        "pending_verification_user_id"
    )


    if not user_id:

        flash(
            "Please register first.",
            "warning"
        )

        return redirect(
            url_for("auth.register")
        )


    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id=?
        """,
        (user_id,),
    ).fetchone()


    if not user:

        session.clear()

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("auth.register")
        )


    if user["email_verified"]:

        session.pop(
            "pending_verification_user_id",
            None
        )

        return redirect(
            url_for("auth.login")
        )


    if request.method == "POST":

        code = request.form.get(
            "code",
            ""
        ).strip()


        if not user["verification_expires"]:

            flash(
                "Verification expired.",
                "danger"
            )

            return redirect(
                url_for("auth.verify_email")
            )


        expires = datetime.fromisoformat(
            user["verification_expires"]
        )


        if datetime.utcnow() > expires:

            flash(
                "Code expired.",
                "warning"
            )

            return redirect(
                url_for("auth.verify_email")
            )


        if check_password_hash(
            user["verification_code"],
            code
        ):

            db.execute(
                """
                UPDATE users
                SET
                    email_verified=1,
                    verification_code=NULL,
                    verification_expires=NULL
                WHERE id=?
                """,
                (user["id"],),
            )

            db.commit()


            session.clear()


            flash(
                "Email verified successfully.",
                "success"
            )


            return redirect(
                url_for("auth.login")
            )


        flash(
            "Invalid verification code.",
            "danger"
        )


    return render_template(
    "auth/verify_email.html",
    user=user
)



# -------------------------
# LOGIN
# -------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,
            (email,),
        ).fetchone()


        if user and check_password_hash(
            user["password"],
            password
        ):


            if not user["email_verified"]:

                session.clear()

                session[
                    "pending_verification_user_id"
                ] = user["id"]

                issue_verification_code(user)


                return redirect(
                    url_for("auth.verify_email")
                )


            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]


            flash(
                "Welcome back.",
                "success"
            )


            return redirect(
                 url_for("dashboard.dashboard")
                )


        flash(
            "Invalid email or password.",
            "danger"
        )


    return render_template(
        "auth/login.html"
    )

# -------------------------
# FORGOT PASSWORD
# -------------------------

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if user:

            code = generate_otp()

            db.execute(
                """
                UPDATE users
                SET password_reset_code = ?,
                    password_reset_expires = ?
                WHERE id = ?
                """,
                (
                    generate_password_hash(code),
                    otp_expiry(),
                    user["id"],
                )
            )

            db.commit()

            send_password_reset_email(
                user["email"],
                user["name"],
                code
            )

            session["reset_email"] = user["email"]

        flash(
            "If the email exists, a password reset code has been sent.",
            "success"
        )

        return redirect(
            url_for("auth.reset_password")
        )

    return render_template(
        "auth/forgot_password.html"
    )


# -------------------------
# RESET PASSWORD
# -------------------------

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")

    if not email:
        flash(
            "Please request a password reset first.",
            "warning"
        )
        return redirect(
            url_for("auth.forgot_password")
        )


    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()


    if not user:
        flash(
            "User not found.",
            "danger"
        )
        return redirect(
            url_for("auth.forgot_password")
        )


    if request.method == "POST":

        code = request.form.get(
            "code",
            ""
        ).strip()

        new_password = request.form.get(
            "password",
            ""
        )


        if not check_password_hash(
            user["password_reset_code"],
            code
        ):

            flash(
                "Invalid reset code.",
                "danger"
            )

            return render_template(
                "auth/reset_password.html"
            )


        if datetime.fromisoformat(
            user["password_reset_expires"]
        ) < datetime.utcnow():

            flash(
                "Reset code expired.",
                "danger"
            )

            return redirect(
                url_for("auth.forgot_password")
            )


        db.execute(
            """
            UPDATE users
            SET password = ?,
                password_reset_code = NULL,
                password_reset_expires = NULL
            WHERE id = ?
            """,
            (
                generate_password_hash(new_password),
                user["id"],
            )
        )

        db.commit()

        session.pop(
            "reset_email",
            None
        )


        flash(
            "Password updated successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )


    return render_template(
        "auth/reset_password.html"
    )

# -------------------------
# LOGOUT
# -------------------------


@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("pages.home")
    )
