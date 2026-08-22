from flask import (
    Blueprint,
    render_template,
    session,
    request,
    flash,
    redirect,
    url_for,
    jsonify
)

from database import get_db
from decorators import login_required


wallet_bp = Blueprint("wallet", __name__)


# =========================================================
# SUPPORTED CURRENCIES
# =========================================================

SUPPORTED_FIAT = {
    "USD",
    "AED",
    "EUR",
    "GBP",
}

SUPPORTED_CRYPTO = {
    "BTC",
    "ETH",
    "USDT",
    "USDC",
}

SUPPORTED_CURRENCIES = SUPPORTED_FIAT | SUPPORTED_CRYPTO


# =========================================================
# DEVELOPMENT REFERENCE RATES
# =========================================================
#
# Value of 1 unit of each currency in USD.
#
# These are ONLY for development/testing.
# Replace with a trusted server-side pricing provider
# before enabling real-money exchange.
#

REFERENCE_RATES_USD = {
    "USD": 1.0,
    "AED": 0.272294,
    "EUR": 1.17,
    "GBP": 1.35,
    "BTC": 117000.0,
    "ETH": 4300.0,
    "USDT": 1.0,
    "USDC": 1.0,
}


EXCHANGE_FEE_RATE = 0.005


# =========================================================
# HELPERS
# =========================================================

def get_asset_balance(db, user_id, currency):
    """
    Return the user's available balance for a currency.

    USD uses the legacy wallets table.
    Every other currency uses wallet_assets.
    """

    if currency == "USD":

        wallet = db.execute(
            """
            SELECT balance
            FROM wallets
            WHERE user_id=?
            """,
            (user_id,)
        ).fetchone()

        return float(
            wallet["balance"]
        ) if wallet else 0.0

    asset = db.execute(
        """
        SELECT balance
        FROM wallet_assets
        WHERE user_id=?
        AND currency=?
        """,
        (
            user_id,
            currency
        )
    ).fetchone()

    return float(
        asset["balance"]
    ) if asset else 0.0


def ensure_asset(db, user_id, currency):
    """
    Make sure a non-USD wallet asset exists.
    """

    if currency == "USD":
        return

    db.execute(
        """
        INSERT OR IGNORE INTO wallet_assets
        (
            user_id,
            currency,
            balance,
            pending,
            lifetime_earnings
        )
        VALUES (?, ?, 0, 0, 0)
        """,
        (
            user_id,
            currency
        )
    )


def update_asset_balance(
    db,
    user_id,
    currency,
    new_balance
):
    """
    Update a user's balance for any supported currency.
    """

    if currency == "USD":

        db.execute(
            """
            UPDATE wallets
            SET balance=?
            WHERE user_id=?
            """,
            (
                new_balance,
                user_id
            )
        )

        return

    ensure_asset(
        db,
        user_id,
        currency
    )

    db.execute(
        """
        UPDATE wallet_assets
        SET
            balance=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE user_id=?
        AND currency=?
        """,
        (
            new_balance,
            user_id,
            currency
        )
    )


def get_exchange_rate(
    from_currency,
    to_currency
):
    """
    Calculate the server-side conversion rate.

    Example:

        BTC -> USD

        117000 / 1 = 117000

    Therefore:

        1 BTC = 117000 USD
    """

    from_usd = REFERENCE_RATES_USD.get(
        from_currency
    )

    to_usd = REFERENCE_RATES_USD.get(
        to_currency
    )

    if not from_usd or not to_usd:
        return None

    return from_usd / to_usd


# =========================================================
# WALLET
# =========================================================

@wallet_bp.route("/wallet")
@login_required
def wallet():

    db = get_db()
    user_id = session["user_id"]

    # -----------------------------------------------------
    # Legacy USD wallet
    # -----------------------------------------------------

    wallet = db.execute(
        """
        SELECT *
        FROM wallets
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchone()

    legacy_usd = float(
        wallet["balance"]
        if wallet and wallet["balance"] is not None
        else 0
    )

    # -----------------------------------------------------
    # All wallet assets
    # -----------------------------------------------------

    wallet_assets = db.execute(
        """
        SELECT
            currency,
            balance,
            pending,
            lifetime_earnings
        FROM wallet_assets
        WHERE user_id=?
        ORDER BY
            CASE currency
                WHEN 'USD' THEN 1
                WHEN 'AED' THEN 2
                WHEN 'EUR' THEN 3
                WHEN 'GBP' THEN 4
                WHEN 'BTC' THEN 5
                WHEN 'ETH' THEN 6
                WHEN 'USDT' THEN 7
                WHEN 'USDC' THEN 8
                ELSE 99
            END
        """,
        (user_id,)
    ).fetchall()

    # -----------------------------------------------------
    # Split fiat / crypto for the wallet UI
    # -----------------------------------------------------

    fiat_assets = []
    crypto_assets = []

    for asset_row in wallet_assets:

        # sqlite3.Row is read-only.
        # Convert it to a normal dictionary so we can
        # safely modify the asset later.
        asset = dict(asset_row)

        currency = asset["currency"]

        if currency in SUPPORTED_FIAT:

            fiat_assets.append(asset)

        elif currency in SUPPORTED_CRYPTO:

            crypto_assets.append(asset)

    # -----------------------------------------------------
    # Make sure legacy USD is represented.
    #
    # The old wallets table is still the source of truth
    # for the existing USD balance.
    # -----------------------------------------------------

    usd_asset_exists = any(
        asset["currency"] == "USD"
        for asset in fiat_assets
    )

    if not usd_asset_exists:

        fiat_assets.insert(
            0,
            {
                "currency": "USD",
                "balance": legacy_usd,
                "pending": 0,
                "lifetime_earnings": 0
            }
        )

    else:

        # Keep the legacy USD wallet balance authoritative.
        for asset in fiat_assets:

            if asset["currency"] == "USD":

                asset["balance"] = legacy_usd

                break

    # -----------------------------------------------------
    # Portfolio calculations
    # -----------------------------------------------------

    total_balance_usd = 0.0
    total_pending_usd = 0.0
    total_lifetime_earnings_usd = 0.0

    for asset_row in wallet_assets:

        asset = dict(asset_row)

        currency = asset["currency"]

        rate = REFERENCE_RATES_USD.get(
            currency,
            0
        )

        balance = float(
            asset["balance"]
            if asset["balance"] is not None
            else 0
        )

        pending = float(
            asset["pending"]
            if asset["pending"] is not None
            else 0
        )

        lifetime = float(
            asset["lifetime_earnings"]
            if asset["lifetime_earnings"] is not None
            else 0
        )

        total_balance_usd += (
            balance * rate
        )

        total_pending_usd += (
            pending * rate
        )

        total_lifetime_earnings_usd += (
            lifetime * rate
        )

    # Add legacy USD balance if wallet_assets does not
    # contain USD.
    if not usd_asset_exists:

        total_balance_usd += legacy_usd

    # -----------------------------------------------------
    # Transactions
    # -----------------------------------------------------

    transactions = db.execute(
        """
        SELECT
            transaction_type,
            currency,
            amount,
            balance_after,
            status,
            description,
            created_at
        FROM wallet_transactions
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT 30
        """,
        (user_id,)
    ).fetchall()

    # -----------------------------------------------------
    # Exchange history
    # -----------------------------------------------------

    exchange_transactions = db.execute(
        """
        SELECT
            id,
            from_currency,
            from_amount,
            to_currency,
            to_amount,
            exchange_rate,
            fee,
            status,
            created_at
        FROM exchange_transactions
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()

    # -----------------------------------------------------
    # Render
    # -----------------------------------------------------

    return render_template(
        "profile/wallet.html",
        wallet=wallet,
        wallet_assets=wallet_assets,
        fiat_assets=fiat_assets,
        crypto_assets=crypto_assets,
        transactions=transactions,
        exchange_transactions=exchange_transactions,
        total_balance_usd=total_balance_usd,
        total_pending_usd=total_pending_usd,
        total_lifetime_earnings_usd=total_lifetime_earnings_usd,
        supported_fiat=sorted(SUPPORTED_FIAT),
        supported_crypto=sorted(SUPPORTED_CRYPTO)
    )


# =========================================================
# EXCHANGE QUOTE
# =========================================================

@wallet_bp.route("/wallet/exchange/quote")
@login_required
def exchange_quote():

    from_currency = request.args.get(
        "from_currency",
        ""
    ).strip().upper()

    to_currency = request.args.get(
        "to_currency",
        ""
    ).strip().upper()

    try:

        amount = float(
            request.args.get(
                "amount",
                0
            )
        )

    except (TypeError, ValueError):

        return jsonify({
            "error": "Invalid amount."
        }), 400

    if amount <= 0:

        return jsonify({
            "error": "Invalid amount."
        }), 400

    if from_currency not in SUPPORTED_CURRENCIES:

        return jsonify({
            "error": "Unsupported source currency."
        }), 400

    if to_currency not in SUPPORTED_CURRENCIES:

        return jsonify({
            "error": "Unsupported destination currency."
        }), 400

    if from_currency == to_currency:

        return jsonify({
            "error": "Currencies must be different."
        }), 400

    from_usd = REFERENCE_RATES_USD[
        from_currency
    ]

    to_usd = REFERENCE_RATES_USD[
        to_currency
    ]

    rate = from_usd / to_usd

    gross_amount = (
        amount * rate
    )

    fee = (
        gross_amount * EXCHANGE_FEE_RATE
    )

    received = (
        gross_amount - fee
    )

    return jsonify({
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "rate": rate,
        "fee": fee,
        "received": received
    })


# =========================================================
# EXCHANGE
# =========================================================

@wallet_bp.route(
    "/wallet/exchange",
    methods=["POST"]
)
@login_required
def exchange():

    db = get_db()

    user_id = session["user_id"]

    # -----------------------------------------------------
    # INPUT
    # -----------------------------------------------------

    from_currency = request.form.get(
        "from_currency",
        ""
    ).strip().upper()

    to_currency = request.form.get(
        "to_currency",
        ""
    ).strip().upper()

    try:

        from_amount = float(
            request.form.get(
                "from_amount",
                0
            )
        )

    except (TypeError, ValueError):

        flash(
            "Invalid exchange amount.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if from_currency not in SUPPORTED_CURRENCIES:

        flash(
            "Unsupported source currency.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    if to_currency not in SUPPORTED_CURRENCIES:

        flash(
            "Unsupported destination currency.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    if from_currency == to_currency:

        flash(
            "You cannot exchange a currency into itself.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    if from_amount <= 0:

        flash(
            "Exchange amount must be greater than zero.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    # -----------------------------------------------------
    # SERVER-SIDE RATE
    # -----------------------------------------------------

    exchange_rate = get_exchange_rate(
        from_currency,
        to_currency
    )

    if exchange_rate is None:

        flash(
            "Exchange rate unavailable.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    # -----------------------------------------------------
    # CALCULATE
    # -----------------------------------------------------

    gross_to_amount = (
        from_amount * exchange_rate
    )

    fee = (
        gross_to_amount * EXCHANGE_FEE_RATE
    )

    to_amount = (
        gross_to_amount - fee
    )

    if to_amount <= 0:

        flash(
            "Exchange amount is too small.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    # -----------------------------------------------------
    # BALANCE CHECK
    # -----------------------------------------------------

    current_balance = get_asset_balance(
        db,
        user_id,
        from_currency
    )

    if current_balance < from_amount:

        flash(
            f"Insufficient {from_currency} balance.",
            "error"
        )

        return redirect(
            url_for("wallet.wallet")
        )

    # -----------------------------------------------------
    # BALANCES
    # -----------------------------------------------------

    new_from_balance = (
        current_balance - from_amount
    )

    current_to_balance = get_asset_balance(
        db,
        user_id,
        to_currency
    )

    new_to_balance = (
        current_to_balance + to_amount
    )

    # -----------------------------------------------------
    # DATABASE TRANSACTION
    # -----------------------------------------------------

    try:

        # Make sure destination asset exists.
        ensure_asset(
            db,
            user_id,
            to_currency
        )

        # Debit source.
        update_asset_balance(
            db,
            user_id,
            from_currency,
            new_from_balance
        )

        # Credit destination.
        update_asset_balance(
            db,
            user_id,
            to_currency,
            new_to_balance
        )

        # -------------------------------------------------
        # SOURCE LEDGER
        # -------------------------------------------------

        db.execute(
            """
            INSERT INTO wallet_transactions
            (
                user_id,
                transaction_type,
                currency,
                amount,
                balance_after,
                status,
                reference_type,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "exchange",
                from_currency,
                -from_amount,
                new_from_balance,
                "completed",
                "exchange",
                (
                    f"{from_currency} → "
                    f"{to_currency}"
                )
            )
        )

        # -------------------------------------------------
        # DESTINATION LEDGER
        # -------------------------------------------------

        db.execute(
            """
            INSERT INTO wallet_transactions
            (
                user_id,
                transaction_type,
                currency,
                amount,
                balance_after,
                status,
                reference_type,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "exchange",
                to_currency,
                to_amount,
                new_to_balance,
                "completed",
                "exchange",
                (
                    f"{from_currency} → "
                    f"{to_currency}"
                )
            )
        )

        # -------------------------------------------------
        # EXCHANGE RECORD
        # -------------------------------------------------

        db.execute(
            """
            INSERT INTO exchange_transactions
            (
                user_id,
                from_currency,
                from_amount,
                to_currency,
                to_amount,
                exchange_rate,
                fee,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                from_currency,
                from_amount,
                to_currency,
                to_amount,
                exchange_rate,
                fee,
                "completed"
            )
        )

        db.commit()

        flash(
            (
                f"Exchange completed: "
                f"{from_amount:g} "
                f"{from_currency} → "
                f"{to_amount:g} "
                f"{to_currency}"
            ),
            "success"
        )

    except Exception:

        db.rollback()

        flash(
            "The exchange could not be completed.",
            "error"
        )

    return redirect(
        url_for("wallet.wallet")
    )