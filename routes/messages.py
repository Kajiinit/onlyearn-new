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


@messages_bp.route("/messages", methods=["GET", "POST"])
@login_required
def messages():

    db = get_db()

    if request.method == "POST":

        receiver_id = request.form.get("receiver_id")
        body = request.form.get("body", "").strip()

        if not receiver_id or not body:
            flash(
                "Choose a user and write a message.",
                "warning"
            )
            return redirect(
                url_for("messages.messages")
            )


        receiver = db.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (receiver_id,)
        ).fetchone()


        if not receiver or int(receiver_id) == session["user_id"]:

            flash(
                "Choose a valid receiver.",
                "warning"
            )

            return redirect(
                url_for("messages.messages")
            )


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
                session["user_id"],
                receiver_id,
                body
            )
        )

        db.commit()


        flash(
            "Message sent.",
            "success"
        )


        return redirect(
            url_for("messages.messages")
        )


    users = db.execute(
        """
        SELECT id, name, email
        FROM users
        WHERE id != ?
        ORDER BY name
        """,
        (session["user_id"],)
    ).fetchall()


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
            session["user_id"],
            session["user_id"]
        )
    ).fetchall()


    return render_template(
        "msg/messages.html",
        users=users,
        messages=rows
    )