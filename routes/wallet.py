from flask import Blueprint, render_template, session

from database import get_db
from decorators import login_required


wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/wallet")
@login_required
def wallet():
    row = get_db().execute(
        "SELECT * FROM wallets WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()

    return render_template(
        "profile/wallet.html",
        wallet=row
    )