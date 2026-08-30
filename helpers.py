import os
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    session,
    current_app,
    flash,
    redirect,
    url_for,
)

from werkzeug.utils import secure_filename
from PIL import Image

from database import get_db


# ---------------------------------------
# Allowed file extensions
# ---------------------------------------

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
}

ALLOWED_PORTFOLIO_EXTENSIONS = (
    ALLOWED_EXTENSIONS
    | {
        "pdf",
        "txt",
    }
)


# ---------------------------------------
# Money parser
# ---------------------------------------

def parse_money(value):
    try:
        cleaned = (
            str(value)
            .replace(",", "")
            .replace("$", "")
            .strip()
        )

        amount = Decimal(cleaned)

        if amount < 0:
            return Decimal("0.00")

        return amount.quantize(
            Decimal("0.01")
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return Decimal("0.00")


# ---------------------------------------
# Cart helpers
# ---------------------------------------

def get_cart():
    return session.setdefault(
        "cart",
        {}
    )


def cart_count():
    return sum(
        int(q)
        for q in get_cart().values()
    )


def cart_items():

    cart = get_cart()

    if not cart:
        return [], Decimal("0.00")

    ids = [
        int(pid)
        for pid in cart.keys()
    ]

    placeholders = ",".join(
        "?"
        for _ in ids
    )

    db = get_db()

    products = db.execute(
        f"""
        SELECT
            products.*,
            users.name AS seller_name

        FROM products

        JOIN users
            ON users.id = products.seller

        WHERE products.id IN ({placeholders})
        """,
        ids,
    ).fetchall()

    items = []

    total = Decimal("0.00")

    for product in products:

        quantity = max(
            int(
                cart.get(
                    str(product["id"]),
                    1,
                )
            ),
            1,
        )

        price = parse_money(
            product["price"]
        )

        subtotal = price * quantity

        total += subtotal

        items.append(
            {
                "product": product,
                "quantity": quantity,
                "price": price,
                "subtotal": subtotal,
            }
        )

    return (
        items,
        total.quantize(
            Decimal("0.01")
        ),
    )

# ---------------------------------------
# Order helpers
# ---------------------------------------

def create_order_from_cart(
    form_data,
    payment_method,
    payment_status="pending",
    crypto_currency=None,
):

    items, total = cart_items()

    if not items:
        return None

    full_name = form_data.get(
        "full_name",
        ""
    ).strip()

    phone = form_data.get(
        "phone",
        ""
    ).strip()

    address = form_data.get(
        "address",
        ""
    ).strip()

    city = form_data.get(
        "city",
        ""
    ).strip()

    if not all(
        [
            full_name,
            phone,
            address,
            city,
        ]
    ):
        flash(
            "Delivery information required.",
            "warning",
        )
        return None

    crypto_address = None

    if payment_method == "crypto":

        crypto_address = {
            "BTC": current_app.config["CRYPTO_BTC_ADDRESS"],
            "ETH": current_app.config["CRYPTO_ETH_ADDRESS"],
            "USDT": current_app.config["CRYPTO_USDT_ADDRESS"],
        }.get(
            crypto_currency
        )

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO orders
        (
            buyer,
            full_name,
            phone,
            address,
            city,
            payment_method,
            payment_status,
            total,
            crypto_currency,
            crypto_address
        )

        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            session["user_id"],
            full_name,
            phone,
            address,
            city,
            payment_method,
            payment_status,
            float(total),
            crypto_currency,
            crypto_address,
        ),
    )

    order_id = cursor.lastrowid

    for item in items:

        product = item["product"]

        db.execute(
            """
            INSERT INTO order_items
            (
                order_id,
                product_id,
                seller,
                title,
                quantity,
                price
            )

            VALUES (?,?,?,?,?,?)
            """,
            (
                order_id,
                product["id"],
                product["seller"],
                product["title"],
                item["quantity"],
                float(item["price"]),
            ),
        )

    db.commit()

    session["cart"] = {}

    return order_id


def order_with_items(order_id):

    db = get_db()

    order = db.execute(
        """
        SELECT *
        FROM orders
        WHERE id=?
        AND buyer=?
        """,
        (
            order_id,
            session["user_id"],
        ),
    ).fetchone()

    if not order:
        return None, []

    items = db.execute(
        """
        SELECT *
        FROM order_items
        WHERE order_id=?
        """,
        (order_id,),
    ).fetchall()

    return order, items


# ---------------------------------------
# User helpers
# ---------------------------------------

def current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    return get_db().execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        user_id = session.get("user_id")

        if not user_id:

            flash(
                "Please log in to continue.",
                "warning",
            )

            return redirect(
                url_for("auth.login")
            )

        user = get_db().execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if not user:

            session.clear()

            flash(
                "Your session is no longer valid. Please log in again.",
                "warning",
            )

            return redirect(
                url_for("auth.login")
            )

        return view(
            *args,
            **kwargs,
        )

    return wrapped_view

# ---------------------------------------
# File helpers
# ---------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1,
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


def allowed_portfolio_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1,
        )[1].lower()
        in ALLOWED_PORTFOLIO_EXTENSIONS
    )


def save_product_image(file):

    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):

        flash(
            "Upload PNG, JPG, JPEG, GIF or WebP image.",
            "warning",
        )

        return None

    filename = secure_filename(
        file.filename
    )

    if not filename or "." not in filename:

        flash(
            "Invalid image file.",
            "warning",
        )

        return None

    ext = filename.rsplit(
        ".",
        1,
    )[1].lower()

    try:

        image = Image.open(file.stream)

        image.verify()

        if image.format.lower() not in {
            "png",
            "jpeg",
            "gif",
            "webp",
        }:
            raise ValueError("Unsupported image format.")

        file.stream.seek(0)

    except Exception:

        flash(
            "Invalid or corrupted image file.",
            "warning",
        )

        return None

    new_name = (
        f"{uuid4().hex}.{ext}"
    )

    file.save(
        os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            new_name,
        )
    )

    return new_name
