from flask import (
    Blueprint,
    render_template,
    redirect,
    request,
    url_for,
    flash,
    session
)
from helpers import cart_items, get_cart

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart")
def cart():

    items, total = cart_items()

    return render_template(
    "onlysell/cart.html",
    items=items,
    total=total
)


@cart_bp.route(
    "/cart/add/<int:product_id>",
    methods=["POST"]
)
def add_to_cart(product_id):

    cart_data = get_cart()

    key = str(product_id)

    cart_data[key] = (
        int(cart_data.get(key, 0))
        + 1
    )

    session["cart"] = cart_data

    session.modified = True

    flash(
        "Added to cart.",
        "success"
    )

    return redirect(
        request.referrer
        or
        url_for("products.products")
    )

@cart_bp.route(
    "/cart/update/<int:product_id>",
    methods=["POST"]
)
def update_cart(product_id):

    cart_data = get_cart()

    quantity = int(
        request.form.get(
            "quantity",
            1
        )
    )

    key = str(product_id)


    if quantity <= 0:
        cart_data.pop(
            key,
            None
        )

    else:
        cart_data[key] = quantity


    session["cart"] = cart_data
    session.modified = True


    flash(
        "Cart updated.",
        "success"
    )

    return redirect(
        url_for("cart.cart")
    )



@cart_bp.route(
    "/cart/remove/<int:product_id>",
    methods=["POST"]
)
def remove_from_cart(product_id):

    cart_data = get_cart()

    cart_data.pop(
        str(product_id),
        None
    )


    session["cart"] = cart_data
    session.modified = True


    flash(
        "Item removed.",
        "success"
    )

    return redirect(
        url_for("cart.cart")
    )