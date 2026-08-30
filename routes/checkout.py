from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from decorators import login_required
from helpers import (
    create_order_from_cart,
    order_with_items
)


checkout_bp = Blueprint(
    "checkout",
    __name__
)


@checkout_bp.route(
    "/checkout",
    methods=["GET", "POST"]
)
@login_required
def checkout():

    if request.method == "POST":

        payment_method = request.form.get(
            "payment_method",
            "cash"
        )

        order_id = create_order_from_cart(
            request.form,
            payment_method
        )


        if not order_id:

            flash(
                "Your cart is empty.",
                "warning"
            )

            return redirect(
                url_for("cart.cart")
            )


        return redirect(
            url_for(
                "checkout.order_success",
                order_id=order_id
            )
        )


    return render_template(
        "onlysell/checkout.html"
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