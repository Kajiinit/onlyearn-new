from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session
)

from decorators import login_required
from helpers import (
    create_order_from_cart,
    order_with_items
)

try:
    import stripe
except ImportError:
    stripe = None


checkout_bp = Blueprint(
    "checkout",
    __name__
)


@checkout_bp.route(
    "/checkout",
    methods=["GET"]
)
@login_required
def checkout():

    from helpers import cart_items

    items, total = cart_items()

    if not items:

        flash(
            "Your cart is empty.",
            "warning"
        )

        return redirect(
            url_for("cart.cart")
        )

    stripe_ready = (
        stripe is not None
        and bool(
            current_app.config.get(
                "STRIPE_SECRET_KEY"
            )
        )
    )

    crypto_options = {
        "BTC": current_app.config.get(
            "CRYPTO_BTC_ADDRESS",
            ""
        ),
        "ETH": current_app.config.get(
            "CRYPTO_ETH_ADDRESS",
            ""
        ),
        "USDT": current_app.config.get(
            "CRYPTO_USDT_ADDRESS",
            ""
        ),
    }

    return render_template(
        "onlysell/checkout.html",
        items=items,
        total=total,
        stripe_ready=stripe_ready,
        crypto_options=crypto_options
    )


@checkout_bp.route(
    "/checkout/stripe",
    methods=["POST"]
)
@login_required
def stripe_checkout():

    if stripe is None:

        flash(
            "Stripe is not available.",
            "error"
        )

        return redirect(
            url_for("checkout.checkout")
        )

    secret_key = current_app.config.get(
        "STRIPE_SECRET_KEY"
    )

    if not secret_key:

        flash(
            "Stripe is not configured.",
            "error"
        )

        return redirect(
            url_for("checkout.checkout")
        )

    order_id = create_order_from_cart(
        request.form,
        "stripe"
    )

    if not order_id:

        return redirect(
            url_for("cart.cart")
        )

    order, items = order_with_items(
        order_id
    )

    if not order or not items:

        flash(
            "Unable to create your order.",
            "error"
        )

        return redirect(
            url_for("cart.cart")
        )

    stripe.api_key = secret_key

    currency = current_app.config.get(
        "STRIPE_CURRENCY",
        "usd"
    ).lower()

    line_items = []

    for item in items:

        line_items.append(
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": item["title"]
                    },
                    "unit_amount": int(
                        round(
                            float(item["price"]) * 100
                        )
                    ),
                },
                "quantity": int(
                    item["quantity"]
                ),
            }
        )

    try:

        stripe_session = (
            stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                metadata={
                    "order_id": str(order_id),
                    "buyer_id": str(
                        session["user_id"]
                    )
                },
                success_url=url_for(
                    "checkout.order_success",
                    order_id=order_id,
                    _external=True
                ),
                cancel_url=url_for(
                    "checkout.checkout",
                    _external=True
                ),
            )
        )

        db = __import__(
            "database"
        ).get_db()

        db.execute(
            """
            UPDATE orders
            SET stripe_session_id=?
            WHERE id=?
            AND buyer=?
            """,
            (
                stripe_session.id,
                order_id,
                session["user_id"]
            )
        )

        db.commit()

        return redirect(
            stripe_session.url,
            code=303
        )

    except Exception:

        db = __import__(
            "database"
        ).get_db()

        db.rollback()

        flash(
            "Stripe checkout could not be started.",
            "error"
        )

        return redirect(
            url_for("checkout.checkout")
        )


@checkout_bp.route(
    "/checkout/crypto",
    methods=["POST"]
)
@login_required
def crypto_checkout():

    crypto_currency = request.form.get(
        "crypto_currency",
        ""
    ).strip().upper()

    crypto_options = {
        "BTC": current_app.config.get(
            "CRYPTO_BTC_ADDRESS"
        ),
        "ETH": current_app.config.get(
            "CRYPTO_ETH_ADDRESS"
        ),
        "USDT": current_app.config.get(
            "CRYPTO_USDT_ADDRESS"
        ),
    }

    if crypto_currency not in crypto_options:

        flash(
            "Unsupported cryptocurrency.",
            "error"
        )

        return redirect(
            url_for("checkout.checkout")
        )

    if not crypto_options[crypto_currency]:

        flash(
            "This cryptocurrency payment option is not configured.",
            "error"
        )

        return redirect(
            url_for("checkout.checkout")
        )

    order_id = create_order_from_cart(
        request.form,
        "crypto",
        payment_status="pending",
        crypto_currency=crypto_currency
    )

    if not order_id:

        return redirect(
            url_for("cart.cart")
        )

    return redirect(
        url_for(
            "checkout.crypto_payment",
            order_id=order_id
        )
    )


@checkout_bp.route(
    "/crypto-payment/<int:order_id>"
)
@login_required
def crypto_payment(order_id):

    order, items = order_with_items(
        order_id
    )

    if not order:

        flash(
            "Order not found.",
            "danger"
        )

        return redirect(
            url_for("products.products")
        )

    return render_template(
        "payments/crypto_payment.html",
        order=order,
        items=items
    )


@checkout_bp.route(
    "/order-success/<int:order_id>"
)
@login_required
def order_success(order_id):

    order, items = order_with_items(
        order_id
    )

    if not order:

        flash(
            "Order not found.",
            "danger"
        )

        return redirect(
            url_for("products.products")
        )

    return render_template(
        "onlysell/order_success.html",
        order=order,
        items=items
    )
