from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from database import get_db


advice_bp = Blueprint(
    "advice",
    __name__,
    url_prefix="/only-advice"
)


# ---------------------------------------
# CURRENT USER
# ---------------------------------------

def get_current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    db = get_db()

    return db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()


# ---------------------------------------
# ONLYADVICE HOME
# ---------------------------------------

@advice_bp.route("/")
def home():

    db = get_db()

    advisors = db.execute(
        """
        SELECT
            advisors.*,
            users.name,
            users.profile_image,
            users.headline,
            users.bio AS user_bio,
            users.location
        FROM advisors
        JOIN users
            ON advisors.user_id = users.id
        WHERE advisors.is_verified = 1
        ORDER BY
            advisors.rating DESC,
            advisors.total_reviews DESC
        """
    ).fetchall()

    return render_template(
        "advice/home.html",
        advisors=advisors
    )


# ---------------------------------------
# BROWSE ADVISORS
# ---------------------------------------

@advice_bp.route("/advisors")
def advisors():

    db = get_db()

    category = request.args.get(
        "category",
        ""
    ).strip()

    search = request.args.get(
        "search",
        ""
    ).strip()

    query = """
        SELECT
            advisors.*,
            users.name,
            users.profile_image,
            users.headline,
            users.bio AS user_bio,
            users.location
        FROM advisors
        JOIN users
            ON advisors.user_id = users.id
        WHERE advisors.is_verified = 1
    """

    params = []

    if category:

        query += """
            AND advisors.category = ?
        """

        params.append(category)

    if search:

        query += """
            AND (
                users.name LIKE ?
                OR users.bio LIKE ?
                OR users.headline LIKE ?
                OR advisors.expertise LIKE ?
                OR advisors.department LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    query += """
        ORDER BY
            advisors.rating DESC,
            advisors.total_reviews DESC
    """

    advisors = db.execute(
        query,
        params
    ).fetchall()

    return render_template(
        "advice/advisors.html",
        advisors=advisors,
        category=category,
        search=search
    )


# ---------------------------------------
# ADVISOR PROFILE
# ---------------------------------------

@advice_bp.route("/advisor/<int:advisor_id>")
def advisor_profile(advisor_id):

    db = get_db()

    advisor = db.execute(
        """
        SELECT
            advisors.*,

            users.id AS user_id,
            users.name,
            users.email,
            users.profile_image,
            users.headline,
            users.bio AS user_bio,
            users.location,
            users.website,
            users.linkedin,
            users.phone,
            users.address,
            users.portfolio_url,
            users.cover_image

        FROM advisors

        JOIN users
            ON advisors.user_id = users.id

        WHERE advisors.id = ?
        """,
        (advisor_id,)
    ).fetchone()

    if advisor is None:

        return "Advisor not found", 404

    return render_template(
        "advice/advisor_profile.html",
        advisor=advisor
    )


# ---------------------------------------
# BECOME AN ADVISOR
# ---------------------------------------

@advice_bp.route(
    "/become-advisor",
    methods=["GET", "POST"]
)
def become_advisor():

    user = get_current_user()

    if user is None:

        flash(
            "Please login to become an advisor.",
            "error"
        )

        return redirect(
            url_for("auth.login")
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT *
        FROM advisors
        WHERE user_id = ?
        """,
        (user["id"],)
    ).fetchone()

    if request.method == "POST":

        category = request.form.get(
            "category",
            ""
        ).strip()

        department = request.form.get(
            "department",
            ""
        ).strip()

        expertise = request.form.get(
            "expertise",
            ""
        ).strip()

        rate_per_minute = request.form.get(
            "rate_per_minute",
            ""
        ).strip()

        availability = request.form.get(
            "availability",
            ""
        ).strip()

        if not category:

            flash(
                "Please select a category.",
                "error"
            )

            return redirect(
                url_for("advice.become_advisor")
            )

        if not department:

            flash(
                "Please enter your department or profession.",
                "error"
            )

            return redirect(
                url_for("advice.become_advisor")
            )

        if not expertise:

            flash(
                "Please describe your expertise.",
                "error"
            )

            return redirect(
                url_for("advice.become_advisor")
            )

        if not rate_per_minute:

            flash(
                "Please enter your consultation rate.",
                "error"
            )

            return redirect(
                url_for("advice.become_advisor")
            )

        # ---------------------------------------
        # USE EXISTING ONLYEARN PROFILE BIO
        # ---------------------------------------

        user_bio = user["bio"] or ""

        if existing:

            db.execute(
                """
                UPDATE advisors

                SET
                    category = ?,
                    department = ?,
                    expertise = ?,
                    bio = ?,
                    rate_per_minute = ?,
                    availability = ?,
                    updated_at = CURRENT_TIMESTAMP

                WHERE user_id = ?
                """,
                (
                    category,
                    department,
                    expertise,
                    user_bio,
                    rate_per_minute,
                    availability,
                    user["id"]
                )
            )

        else:

            db.execute(
                """
                INSERT INTO advisors (
                    user_id,
                    category,
                    department,
                    expertise,
                    bio,
                    rate_per_minute,
                    availability,
                    created_at,
                    updated_at
                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    user["id"],
                    category,
                    department,
                    expertise,
                    user_bio,
                    rate_per_minute,
                    availability
                )
            )

        db.commit()

        flash(
            "Your OnlyAdvice profile has been saved.",
            "success"
        )

        return redirect(
            url_for(
                "advice.my_advisor_profile"
            )
        )

    return render_template(
        "advice/become_advisor.html",
        user=user,
        advisor=existing
    )


# ---------------------------------------
# MY ADVISOR PROFILE
# ---------------------------------------

@advice_bp.route("/my-advisor-profile")
def my_advisor_profile():

    user = get_current_user()

    if user is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("auth.login")
        )

    db = get_db()

    advisor = db.execute(
        """
        SELECT
            advisors.*,

            users.id AS profile_user_id,
            users.name,
            users.email,
            users.profile_image,
            users.headline,
            users.bio AS user_bio,
            users.phone,
            users.location,
            users.website,
            users.linkedin,
            users.portfolio_url,
            users.cover_image

        FROM advisors

        JOIN users
            ON advisors.user_id = users.id

        WHERE advisors.user_id = ?
        """,
        (user["id"],)
    ).fetchone()

    if advisor is None:

        return redirect(
            url_for(
                "advice.become_advisor"
            )
        )

    return render_template(
        "advice/advisor_profile.html",
        advisor=advisor,
        own_profile=True
    )