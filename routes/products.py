from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from database import get_db
from decorators import login_required
from utils import save_product_image


products_bp = Blueprint("products", __name__)


# ---------------------------------------
# Products list
# ---------------------------------------

@products_bp.route("/products")
def products():

    rows = get_db().execute(
        """
        SELECT products.*,
               users.name AS seller_name

        FROM products

        JOIN users
        ON users.id = products.seller

        ORDER BY products.id DESC

        """
    ).fetchall()


    return render_template(
        "onlysell/products.html",
        products=rows
    )



# ---------------------------------------
# Product detail
# ---------------------------------------

@products_bp.route("/products/<int:product_id>")
def product_detail(product_id):

    product = get_db().execute(
        """
        SELECT products.*,
               users.name AS seller_name,
               users.email AS seller_email

        FROM products

        JOIN users
        ON users.id = products.seller

        WHERE products.id = ?

        """,
        (product_id,)
    ).fetchone()


    if not product:

        flash(
            "Product not found.",
            "danger"
        )

        return redirect(
            url_for("products.products")
        )


    return render_template(
        "onlysell/product.html",
        product=product
    )



# ---------------------------------------
# Create product
# ---------------------------------------

@products_bp.route(
    "/products/create",
    methods=["GET", "POST"]
)
@login_required
def create_product():

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        price = request.form.get(
            "price",
            ""
        ).strip()


        category = request.form.get(
            "category",
            ""
        ).strip()


        image = save_product_image(
            request.files.get("image")
        )


        if not all(
            [
                title,
                description,
                price,
                category
            ]
        ):

            flash(
                "All product fields required.",
                "warning"
            )

            return redirect(
                url_for("products.create_product")
            )


        db = get_db()


        db.execute(
            """
            INSERT INTO products
            (
                title,
                description,
                price,
                category,
                image,
                seller
            )

            VALUES (?,?,?,?,?,?)

            """,
            (
                title,
                description,
                price,
                category,
                image,
                session["user_id"]
            )
        )


        db.commit()


        flash(
            "Product listed.",
            "success"
        )


        return redirect(
            url_for("products.products")
        )


    return render_template(
        "onlysell/sell.html"
    )