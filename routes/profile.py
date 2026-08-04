from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for
)

from database import get_db
from decorators import login_required


profile_bp = Blueprint("profile", __name__)

def current_user():
    db = get_db()

    if "user_id" not in session:
        return None

    return db.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

@profile_bp.route("/profile")
@login_required
def profile():

    user = current_user()
    db = get_db()

    education = db.execute(
        "SELECT * FROM education WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    experience = db.execute(
        "SELECT * FROM experience WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    skills = db.execute(
        "SELECT * FROM skills WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    portfolio_items = db.execute(
        """
        SELECT *
        FROM portfolio_items
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    verification = db.execute(
        """
        SELECT *
        FROM verification_requests
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    return render_template(
        "profile/profile.html",
        user=user,
        education=education,
        experience=experience,
        skills=skills,
        portfolio_items=portfolio_items,
        verification=verification,
    )



@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():

    db = get_db()
    user_id = session["user_id"]

    if request.method == "POST":

        name = request.form.get("name","").strip()
        phone = request.form.get("phone","").strip()
        location = request.form.get("location","").strip()
        bio = request.form.get("bio","").strip()


        db.execute(
            """
            UPDATE users
            SET name=?,
                phone=?,
                location=?,
                bio=?
            WHERE id=?
            """,
            (
                name,
                phone,
                location,
                bio,
                user_id
            )
        )

        db.commit()

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect(
            url_for("profile.profile")
        )


    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id=?
        """,
        (user_id,)
    ).fetchone()


    skills = db.execute(
        """
        SELECT name
        FROM skills
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchall()


    return render_template(
        "profile/edit_profile.html",
        user=user,
        skills=skills
    )