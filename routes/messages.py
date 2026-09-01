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


messages_bp = Blueprint("messages", __name__)


# =========================================================
# ONLYCHAT — MESSAGES
# =========================================================

@messages_bp.route(
    "/messages",
    methods=["GET", "POST"]
)
@login_required
def messages():

    db = get_db()
    user_id = session["user_id"]

    # -----------------------------------------------------
    # SEND MESSAGE
    # -----------------------------------------------------

    if request.method == "POST":

        receiver_id_raw = request.form.get(
            "receiver_id",
            ""
        ).strip()

        body = request.form.get(
            "body",
            ""
        ).strip()

        # -------------------------------------------------
        # Validate receiver ID
        # -------------------------------------------------

        try:

            receiver_id = int(
                receiver_id_raw
            )

        except (TypeError, ValueError):

            flash(
                "Choose a valid receiver.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )

        # -------------------------------------------------
        # Validate message
        # -------------------------------------------------

        if not body:

            flash(
                "Write a message.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )

        # Prevent excessively large messages.
        if len(body) > 5000:

            flash(
                "Message is too long. Maximum 5000 characters.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )

        # -------------------------------------------------
        # Prevent messaging yourself
        # -------------------------------------------------

        if receiver_id == user_id:

            flash(
                "You cannot message yourself.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )

        # -------------------------------------------------
        # Verify receiver exists
        # -------------------------------------------------

        receiver = db.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (receiver_id,)
        ).fetchone()

        if not receiver:

            flash(
                "Choose a valid receiver.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )

        # -------------------------------------------------
        # Save message
        # -------------------------------------------------

        try:

            db.execute(
                """
                INSERT INTO messages
                (
                    sender,
                    receiver,
                    body
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    receiver_id,
                    body
                )
            )

            db.commit()

            flash(
                "Message sent.",
                "success"
            )

        except Exception:

            db.rollback()

            flash(
                "The message could not be sent.",
                "danger"
            )

        return redirect(
            url_for("messages.messages")
        )

    # -----------------------------------------------------
    # USERS AVAILABLE FOR MESSAGING
    # -----------------------------------------------------

    users = db.execute(
        """
        SELECT id, name, email
        FROM users
        WHERE id != ?
        ORDER BY name
        """,
        (user_id,)
    ).fetchall()

    # -----------------------------------------------------
    # MESSAGE HISTORY
    # -----------------------------------------------------

    rows = db.execute(
        """
        SELECT
            messages.*,
            sender.name AS sender_name,
            receiver.name AS receiver_name

        FROM messages

        JOIN users AS sender
            ON sender.id = messages.sender

        JOIN users AS receiver
            ON receiver.id = messages.receiver

        WHERE messages.sender = ?
           OR messages.receiver = ?

        ORDER BY messages.id DESC
        """,
        (
            user_id,
            user_id
        )
    ).fetchall()

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------

    return render_template(
        "msg/messages.html",
        users=users,
        messages=rows
    )
