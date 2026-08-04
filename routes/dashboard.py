from flask import (
    Blueprint,
    render_template,
    session
)

from helpers import login_required
from database import get_db


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)
# ---------------------------------------
# Dashboard
# ---------------------------------------
@dashboard_bp.route("/dashboard")
@login_required
def dashboard():

    db = get_db()

    user_id = session["user_id"]

    stats = {

        "jobs":
        db.execute(
            """
            SELECT COUNT(*) AS total
            FROM jobs
            WHERE created_by=?
            """,
            (user_id,)
        ).fetchone()["total"],

        "products":
        db.execute(
            """
            SELECT COUNT(*) AS total
            FROM products
            WHERE seller=?
            """,
            (user_id,)
        ).fetchone()["total"],

        "applications":
        db.execute(
            """
            SELECT COUNT(*) AS total
            FROM applications
            WHERE applicant=?
            """,
            (user_id,)
        ).fetchone()["total"]

    }

    wallet = db.execute(
        """
        SELECT *
        FROM wallets
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchone()

    return render_template(
        "dashboard/dashboard.html",
        stats=stats,
        wallet=wallet
    )
