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
from helpers import save_product_image


products_bp = Blueprint("products", __name__)


# =========================================================
# ONLYSELL — PRODUCTS / MARKETPLACE
# =========================================================

@products_bp.route("/products")
def products():

    db = get_db()

    # -----------------------------------------------------
    # Read marketplace controls
    # -----------------------------------------------------

    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "newest").strip()

    # -----------------------------------------------------
    # Base query
    # -----------------------------------------------------

    query = """
        SELECT
            products.*,
            users.name AS seller_name
        FROM products
        JOIN users
            ON users.id = products.seller
    """

    conditions = []
    params = []

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    if search:
        conditions.append("""
            (
                products.title LIKE ?
                OR products.description LIKE ?
                OR products.category LIKE ?
                OR users.name LIKE ?
            )
        """)

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # -----------------------------------------------------
    # Category
    # -----------------------------------------------------

    if category and category.lower() != "all":

        conditions.append(
            "products.category = ?"
        )

        params.append(category)

    # -----------------------------------------------------
    # WHERE
    # -----------------------------------------------------

    if conditions:

        query += """
            WHERE
        """ + " AND ".join(conditions)

    # -----------------------------------------------------
    # Sorting
    # -----------------------------------------------------

    if sort == "price_low":

        query += """
            ORDER BY CAST(products.price AS REAL) ASC
        """

    elif sort == "price_high":

        query += """
            ORDER BY CAST(products.price AS REAL) DESC
        """

    else:

        # newest is also the default
        query += """
            ORDER BY products.id DESC
        """

    # -----------------------------------------------------
    # Execute
    # -----------------------------------------------------

    rows = db.execute(
        query,
        params
    ).fetchall()

    # -----------------------------------------------------
    # Render
    # -----------------------------------------------------

    return render_template(
        "onlysell/products.html",
        products=rows,
        search=search,
        category=category,
        sort=sort
    )


# =========================================================
# ONLYSELL — PRODUCT DETAIL
# =========================================================

@products_bp.route("/products/<int:product_id>")
def product_detail(product_id):

    product = get_db().execute(
        """
        SELECT
            products.*,
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


# =========================================================
# ONLYSELL — CREATE PRODUCT
# =========================================================

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

        # -------------------------------------------------
        # Validate
        # -------------------------------------------------

        if not all([
            title,
            description,
            price,
            category
        ]):

            flash(
                "All product fields required.",
                "warning"
            )

            return redirect(
                url_for("products.create_product")
            )

        # -------------------------------------------------
        # Save product
        # -------------------------------------------------

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

            VALUES (?, ?, ?, ?, ?, ?)
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
            "Product listed successfully.",
            "success"
        )

        return redirect(
            url_for("products.products")
        )

    return render_template(
        "onlysell/sell.html"
    )
