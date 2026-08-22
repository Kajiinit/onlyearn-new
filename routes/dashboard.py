from flask import (
    Blueprint,
    render_template,
    session,
    request,
    jsonify
)

from helpers import login_required
from database import get_db


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


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


    # =====================================
    # EARNINGS BY PERIOD
    # =====================================

    earnings = {

        "day":
        db.execute(
            """
            SELECT COALESCE(SUM(oi.price * oi.quantity), 0) AS total
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.seller=?
            AND o.payment_status='paid'
            AND date(o.created_at)=date('now','localtime')
            """,
            (user_id,)
        ).fetchone()["total"],


        "week":
        db.execute(
            """
            SELECT COALESCE(SUM(oi.price * oi.quantity), 0) AS total
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.seller=?
            AND o.payment_status='paid'
            AND date(o.created_at) >= date('now','localtime','-6 days')
            """,
            (user_id,)
        ).fetchone()["total"],


        "month":
        db.execute(
            """
            SELECT COALESCE(SUM(oi.price * oi.quantity), 0) AS total
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.seller=?
            AND o.payment_status='paid'
            AND strftime('%Y-%m', o.created_at)
                = strftime('%Y-%m','now','localtime')
            """,
            (user_id,)
        ).fetchone()["total"]

    }


    # =====================================
    # TRANSACTIONS
    # =====================================

    transactions = db.execute(
        """
        SELECT
            oi.order_id,
            oi.title,
            oi.quantity,
            oi.price,
            (oi.price * oi.quantity) AS amount,
            o.created_at
        FROM order_items oi
        JOIN orders o
            ON o.id = oi.order_id
        WHERE oi.seller=?
        AND o.payment_status='paid'
        ORDER BY o.created_at DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()


    return render_template(
        "dashboard/dashboard.html",
        stats=stats,
        wallet=wallet,
        earnings=earnings,
        transactions=transactions
    )


@dashboard_bp.route("/dashboard/earnings")
@login_required
def dashboard_custom_earnings():

    db = get_db()

    user_id = session["user_id"]

    start_date = request.args.get("from")
    end_date = request.args.get("to")

    if not start_date or not end_date:
        return jsonify({
            "total": 0
        })


    result = db.execute(
        """
        SELECT COALESCE(
            SUM(oi.price * oi.quantity),
            0
        ) AS total
        FROM order_items oi
        JOIN orders o
            ON o.id = oi.order_id
        WHERE oi.seller=?
        AND o.payment_status='paid'
        AND date(o.created_at)
            BETWEEN date(?) AND date(?)
        """,
        (
            user_id,
            start_date,
            end_date
        )
    ).fetchone()


    return jsonify({
        "total": result["total"]
    })
