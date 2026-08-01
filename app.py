
import os
import json
import random
import smtplib
import sqlite3
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from uuid import uuid4
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    import stripe
except ImportError:
    stripe = None

try:
    from authlib.integrations.flask_client import OAuth
except ImportError:
    OAuth = None


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATABASE = os.path.join(PROJECT_ROOT, "database.db")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "static", "uploads")

PROFILE_FOLDER = os.path.join(BASE_DIR, "..", "static", "profile")
PROFILE_USER_FOLDER = os.path.join(PROFILE_FOLDER, "users")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_USER_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_PORTFOLIO_EXTENSIONS = ALLOWED_EXTENSIONS | {"pdf", "txt"}

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static")
)
app.config["SECRET_KEY"] = os.environ.get("ONLYEARN_SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROFILE_USER_FOLDER"] = PROFILE_USER_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY", "")
app.config["STRIPE_CURRENCY"] = os.environ.get("STRIPE_CURRENCY", "usd")
app.config["CRYPTO_BTC_ADDRESS"] = os.environ.get("CRYPTO_BTC_ADDRESS", "bc1q-onlyearn-demo-wallet")
app.config["CRYPTO_ETH_ADDRESS"] = os.environ.get("CRYPTO_ETH_ADDRESS", "0xOnlyEarnDemoWallet")
app.config["CRYPTO_USDT_ADDRESS"] = os.environ.get("CRYPTO_USDT_ADDRESS", "TOnlyEarnDemoWallet")
app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST", "")
app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME", "")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD", "")
app.config["SMTP_FROM_EMAIL"] = os.environ.get("SMTP_FROM_EMAIL", app.config["SMTP_USERNAME"])
app.config["SMTP_USE_SSL"] = os.environ.get("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes"}
app.config["SMTP_TIMEOUT"] = int(os.environ.get("SMTP_TIMEOUT", "15"))
app.config["SHOW_DEV_OTP"] = os.environ.get("ONLYEARN_SHOW_DEV_OTP", "false").lower() in {"1", "true", "yes"}
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
app.config["APPLE_CLIENT_ID"] = os.environ.get("APPLE_CLIENT_ID", "")
app.config["APPLE_CLIENT_SECRET"] = os.environ.get("APPLE_CLIENT_SECRET", "")

oauth = OAuth(app) if OAuth else None
if oauth and app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]:
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
if oauth and app.config["APPLE_CLIENT_ID"] and app.config["APPLE_CLIENT_SECRET"]:
    oauth.register(
        name="apple",
        client_id=app.config["APPLE_CLIENT_ID"],
        client_secret=app.config["APPLE_CLIENT_SECRET"],
        server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email name"},
    )


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROFILE_FOLDER, exist_ok=True)

    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email_verified INTEGER DEFAULT 1,
            verification_code TEXT,
            verification_expires TEXT
        )
    """)

    user_columns = [
        row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
    ]
    if "email_verified" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 1")
    if "verification_code" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")

    if "verification_expires" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN verification_expires TEXT")
    if "password_reset_code" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_reset_code TEXT")
    if "password_reset_expires" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_reset_expires TEXT")
    if "profile_image" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN profile_image TEXT DEFAULT 'default.png'"
        )

    if "phone" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
        )

    if "location" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN location TEXT"
        )

    if "bio" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN bio TEXT"
        )

    if "verified" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0"
        )

    if "headline" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN headline TEXT"
        )

    if "website" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN website TEXT"
        )

    if "linkedin" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN linkedin TEXT"
        )

    if "portfolio_url" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN portfolio_url TEXT"
        )

    if "cover_image" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN cover_image TEXT DEFAULT 'default-cover.jpg'"
        )
    if "address" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")
    if "profile_type" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_type TEXT DEFAULT 'freelancer'")
    if "auth_provider" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT")
    if "auth_subject" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_subject TEXT")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            degree TEXT NOT NULL,
            institution TEXT NOT NULL,
            year TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            start_date TEXT,
            end_date TEXT,
            description TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            file_path TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            budget TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            applicant INTEGER NOT NULL,
            status TEXT DEFAULT 'Applied',
            UNIQUE(job_id, applicant),
            FOREIGN KEY (job_id) REFERENCES jobs (id),
            FOREIGN KEY (applicant) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT,
            allow_negotiation INTEGER DEFAULT 1,
            seller INTEGER NOT NULL,
            FOREIGN KEY (seller) REFERENCES users (id)
        )
    """)

    product_columns = [
        row[1] for row in cursor.execute("PRAGMA table_info(products)").fetchall()
    ]
    if "allow_negotiation" not in product_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN allow_negotiation INTEGER DEFAULT 1")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender INTEGER NOT NULL,
            receiver INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender) REFERENCES users (id),
            FOREIGN KEY (receiver) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            balance REAL DEFAULT 0,
            pending REAL DEFAULT 0,
            lifetime_earnings REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            order_status TEXT DEFAULT 'placed',
            total REAL NOT NULL,
            stripe_session_id TEXT,
            crypto_currency TEXT,
            crypto_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            seller INTEGER NOT NULL,
            title TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (seller) REFERENCES users (id)
        )
    """)

    db.commit()
    db.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def parse_money(value):
    try:
        cleaned = str(value).replace(",", "").replace("$", "").strip()
        amount = Decimal(cleaned)
        if amount < 0:
            return Decimal("0.00")
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def get_cart():
    cart = session.setdefault("cart", {})
    return cart


def cart_count():
    return sum(int(quantity) for quantity in get_cart().values())


def cart_items():
    cart = get_cart()
    if not cart:
        return [], Decimal("0.00")

    ids = [int(product_id) for product_id in cart.keys()]
    placeholders = ",".join("?" for _ in ids)
    products = get_db().execute(
        f"""
        SELECT products.*, users.name AS seller_name
        FROM products
        JOIN users ON users.id = products.seller
        WHERE products.id IN ({placeholders})
        """,
        ids,
    ).fetchall()

    items = []
    total = Decimal("0.00")
    for product in products:
        quantity = max(int(cart.get(str(product["id"]), 1)), 1)
        price = parse_money(product["price"])
        subtotal = price * quantity
        total += subtotal
        items.append({
            "product": product,
            "quantity": quantity,
            "price": price,
            "subtotal": subtotal,
        })

    return items, total.quantize(Decimal("0.01"))


def create_order_from_cart(form_data, payment_method, payment_status="pending", crypto_currency=None):
    items, total = cart_items()
    if not items:
        return None

    full_name = form_data.get("full_name", "").strip()
    phone = form_data.get("phone", "").strip()
    address = form_data.get("address", "").strip()
    city = form_data.get("city", "").strip()

    if not full_name or not phone or not address or not city:
        flash("Delivery name, phone, address, and city are required.", "warning")
        return None

    crypto_address = None
    if payment_method == "crypto":
        crypto_address = {
            "BTC": app.config["CRYPTO_BTC_ADDRESS"],
            "ETH": app.config["CRYPTO_ETH_ADDRESS"],
            "USDT": app.config["CRYPTO_USDT_ADDRESS"],
        }.get(crypto_currency, app.config["CRYPTO_USDT_ADDRESS"])

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO orders (
            buyer, full_name, phone, address, city, payment_method,
            payment_status, total, crypto_currency, crypto_address
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            INSERT INTO order_items (order_id, product_id, seller, title, quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
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
    return order_id


def order_with_items(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND buyer = ?", (order_id, session["user_id"])).fetchone()
    if not order:
        return None, []
    items = db.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)).fetchall()
    return order, items


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def otp_expiry():
    return (datetime.utcnow() + timedelta(minutes=10)).isoformat()


def send_otp_email(email, name, code, subject, intro):
    if not app.config["SMTP_HOST"] or not app.config["SMTP_FROM_EMAIL"]:
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = app.config["SMTP_FROM_EMAIL"]
    message["To"] = email
    message.set_content(
        f"Hi {name},\n\n{intro}: {code}.\n"
        "This code expires in 10 minutes.\n\nOnlyEarn"
    )

    smtp_class = smtplib.SMTP_SSL if app.config["SMTP_USE_SSL"] else smtplib.SMTP
    with smtp_class(
        app.config["SMTP_HOST"],
        app.config["SMTP_PORT"],
        timeout=app.config["SMTP_TIMEOUT"],
    ) as server:
        if not app.config["SMTP_USE_SSL"]:
            server.starttls()
        if app.config["SMTP_USERNAME"] and app.config["SMTP_PASSWORD"]:
            server.login(app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"])
        server.send_message(message)

    return True


def send_verification_email(email, name, code):
    return send_otp_email(
        email,
        name,
        code,
        "OnlyEarn email verification code",
        "Your OnlyEarn verification code",
    )


def issue_verification_code(user):
    code = generate_otp()
    get_db().execute(
        """
        UPDATE users
        SET verification_code = ?, verification_expires = ?, email_verified = 0
        WHERE id = ?
        """,
        (generate_password_hash(code), otp_expiry(), user["id"]),
    )
    get_db().commit()

    try:
        sent = send_verification_email(user["email"], user["name"], code)
    except Exception as exc:
        sent = False
        print(f"Email verification send failed for {user['email']}: {exc}")

    if sent:
        flash("Verification code sent to your email.", "success")
    elif app.config["SHOW_DEV_OTP"]:
        flash(f"Development OTP for {user['email']}: {code}", "warning")
    else:
        flash("We could not send your verification email. Please try again later.", "danger")

def send_password_reset_email(email, name, code):
    return send_otp_email(
        email,
        name,
        code,
        "OnlyEarn password reset code",
        "Your OnlyEarn password reset code",
    )

@app.context_processor
def inject_user():
    return {"current_user": current_user(), "cart_count": cart_count()}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_portfolio_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PORTFOLIO_EXTENSIONS


def save_product_image(file):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        flash("Upload a PNG, JPG, GIF, or WebP image.", "warning")
        return None

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid4().hex}.{extension}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
    return unique_name


@app.route("/")
def home():
    return render_template("home/home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        db = get_db()

        try:
            cursor = db.execute(
                "INSERT INTO users (name, email, password, email_verified) VALUES (?, ?, ?, 0)",
                (name, email, password_hash),
            )
            db.execute("INSERT INTO wallets (user_id) VALUES (?)", (cursor.lastrowid,))
            db.commit()
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))

        user = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        session["pending_verification_user_id"] = user["id"]
        issue_verification_code(user)
        return redirect(url_for("verify_email"))

    return render_template("auth/register.html")


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        flash("Register or log in to verify your email.", "warning")
        return redirect(url_for("login"))

    user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        session.pop("pending_verification_user_id", None)
        flash("Verification user not found.", "danger")
        return redirect(url_for("register"))

    if user["email_verified"]:
        session.pop("pending_verification_user_id", None)
        flash("Email already verified. You can log in.", "success")
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        expires = datetime.fromisoformat(user["verification_expires"]) if user["verification_expires"] else datetime.utcnow()

        if datetime.utcnow() > expires:
            flash("That verification code expired. Please request a new one.", "warning")
            return redirect(url_for("verify_email"))

        if user["verification_code"] and check_password_hash(user["verification_code"], code):
            get_db().execute(
                """
                UPDATE users
                SET email_verified = 1, verification_code = NULL, verification_expires = NULL
                WHERE id = ?
                """,
                (user["id"],),
            )
            get_db().commit()
            session.pop("pending_verification_user_id", None)
            flash("Email verified. You can log in now.", "success")
            return redirect(url_for("login"))

        flash("Invalid verification code.", "danger")
        return redirect(url_for("verify_email"))

    return render_template("auth/verify_email.html", user=user)


@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        flash("No pending verification found.", "warning")
        return redirect(url_for("login"))

    user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash("Verification user not found.", "danger")
        return redirect(url_for("register"))

    issue_verification_code(user)
    return redirect(url_for("verify_email"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            if not user["email_verified"]:
                session.clear()
                session["pending_verification_user_id"] = user["id"]
                issue_verification_code(user)
                return redirect(url_for("verify_email"))

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("auth/login.html")


@app.route("/login/<provider>")
def social_login(provider):
    if provider not in {"google", "apple"}:
        return redirect(url_for("login"))

    client = oauth.create_client(provider) if oauth else None
    if client is None:
        flash(f"{provider.title()} sign-in is not configured yet.", "warning")
        return redirect(url_for("login"))

    return client.authorize_redirect(url_for("social_callback", provider=provider, _external=True))


@app.route("/login/<provider>/callback", methods=["GET", "POST"])
def social_callback(provider):
    if provider not in {"google", "apple"}:
        return redirect(url_for("login"))

    client = oauth.create_client(provider) if oauth else None
    if client is None:
        flash(f"{provider.title()} sign-in is not configured yet.", "warning")
        return redirect(url_for("login"))

    try:
        token = client.authorize_access_token()
        userinfo = token.get("userinfo") or client.parse_id_token(token)
        if provider == "apple" and request.form.get("user"):
            apple_user = json.loads(request.form["user"])
            first_name = apple_user.get("name", {}).get("firstName", "")
            last_name = apple_user.get("name", {}).get("lastName", "")
            userinfo["name"] = " ".join(part for part in (first_name, last_name) if part)
    except Exception as exc:
        print(f"{provider.title()} sign-in failed: {exc}")
        flash(f"We could not complete {provider.title()} sign-in. Please try again.", "danger")
        return redirect(url_for("login"))

    email = (userinfo.get("email") or "").strip().lower()
    subject = str(userinfo.get("sub") or "")
    name = (userinfo.get("name") or email.split("@", 1)[0]).strip()
    if not email or not subject:
        flash(f"{provider.title()} did not provide a usable email address.", "danger")
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE auth_provider = ? AND auth_subject = ?",
        (provider, subject),
    ).fetchone()
    if not user:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            db.execute(
                "UPDATE users SET auth_provider = ?, auth_subject = ?, email_verified = 1 WHERE id = ?",
                (provider, subject, user["id"]),
            )
        else:
            cursor = db.execute(
                """
                INSERT INTO users (name, email, password, email_verified, auth_provider, auth_subject)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (name, email, generate_password_hash(uuid4().hex), provider, subject),
            )
            db.execute("INSERT INTO wallets (user_id) VALUES (?)", (cursor.lastrowid,))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    flash(f"Signed in with {provider.title()}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()


        if user:

            code = generate_otp()

            db.execute(
                """
                UPDATE users
                SET password_reset_code=?,
                    password_reset_expires=?
                WHERE id=?
                """,
                (
                    generate_password_hash(code),
                    otp_expiry(),
                    user["id"]
                )
            )

            db.commit()


            session["reset_email"] = user["email"]


            try:

                sent = send_password_reset_email(
                    user["email"],
                    user["name"],
                    code
                )


            except Exception as exc:

                sent = False

                print(
                    f"Password reset email failed: {exc}"
                )


            if sent:

                flash(
                    "Password reset code sent to your email.",
                    "success"
                )


            elif app.config["SHOW_DEV_OTP"]:
                flash(f"Development reset OTP: {code}", "warning")
            else:
                flash("We could not send the reset email. Please try again later.", "danger")


        else:

            # Do not reveal whether email exists
            flash(
                "If this email exists, a reset code has been sent.",
                "success"
            )


        return redirect(
            url_for("reset_password")
        )


    return render_template(
        "auth/forgot_password.html"
    )

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")
    print(
    "RESET SESSION FOUND:",
    email
)
    if not email:
        return redirect(
            url_for("forgot_password")
        )


    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()


    if not user:
        flash(
            "Invalid password reset request.",
            "danger"
        )

        session.pop(
            "reset_email",
            None
        )

        return redirect(
            url_for("forgot_password")
        )


    if request.method == "POST":

        code = request.form.get("code", "").strip()
        new_password = request.form.get("password", "")


        if not user["password_reset_code"]:
            flash(
                "No reset code found. Request a new one.",
                "danger"
            )

            return redirect(
                url_for("forgot_password")
            )


        if not check_password_hash(
            user["password_reset_code"],
            code
        ):

            flash(
                "Invalid reset code.",
                "danger"
            )

            return redirect(
                url_for("reset_password")
            )


        if datetime.fromisoformat(
            user["password_reset_expires"]
        ) < datetime.utcnow():

            flash(
                "Reset code expired. Request a new one.",
                "danger"
            )

            session.pop(
                "reset_email",
                None
            )

            return redirect(
                url_for("forgot_password")
            )


        db.execute(
            """
            UPDATE users
            SET password=?,
                password_reset_code=NULL,
                password_reset_expires=NULL
            WHERE id=?
            """,
            (
                generate_password_hash(new_password),
                user["id"]
            )
        )

        db.commit()


        session.pop(
            "reset_email",
            None
        )


        flash(
            "Password changed successfully. Login now.",
            "success"
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "auth/reset_password.html"
    )
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = session["user_id"]
    stats = {
        "jobs": db.execute("SELECT COUNT(*) AS total FROM jobs WHERE created_by = ?", (user_id,)).fetchone()["total"],
        "products": db.execute("SELECT COUNT(*) AS total FROM products WHERE seller = ?", (user_id,)).fetchone()["total"],
        "applications": db.execute(
            "SELECT COUNT(*) AS total FROM applications WHERE applicant = ?", (user_id,)
        ).fetchone()["total"],
    }
    wallet = db.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
    return render_template("dashboard/dashboard.html", stats=stats, wallet=wallet)


@app.route("/jobs")
def jobs():
    rows = get_db().execute("""
        SELECT jobs.*, users.name AS employer_name
        FROM jobs
        JOIN users ON users.id = jobs.created_by
        ORDER BY jobs.id DESC
    """).fetchall()
    return render_template("jobs/jobs.html", jobs=rows)


@app.route("/jobs/create", methods=["GET", "POST"])
@login_required
def create_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        budget = request.form.get("budget", "").strip()

        if not title or not description or not budget:
            flash("Job title, description, and budget are required.", "warning")
            return redirect(url_for("create_job"))

        get_db().execute(
            "INSERT INTO jobs (title, description, budget, created_by) VALUES (?, ?, ?, ?)",
            (title, description, budget, session["user_id"]),
        )
        get_db().commit()
        flash("Job posted.", "success")
        return redirect(url_for("jobs"))

    return render_template("jobs/post_job.html")


@app.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
def apply_to_job(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if job["created_by"] == session["user_id"]:
        flash("You cannot apply to your own job.", "warning")
        return redirect(url_for("jobs"))

    try:
        db.execute(
            "INSERT INTO applications (job_id, applicant, status) VALUES (?, ?, 'Applied')",
            (job_id, session["user_id"]),
        )
        db.commit()
        flash("Application sent.", "success")
    except sqlite3.IntegrityError:
        flash("You already applied to this job.", "warning")

    return redirect(url_for("jobs"))


@app.route("/jobs/<int:job_id>/applicants")
@login_required
def applicants(job_id):
    db = get_db()
    job = db.execute("""
        SELECT jobs.*, users.name AS employer_name
        FROM jobs
        JOIN users ON users.id = jobs.created_by
        WHERE jobs.id = ?
    """, (job_id,)).fetchone()

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if job["created_by"] != session["user_id"]:
        flash("Only the employer can view applicants.", "danger")
        return redirect(url_for("jobs"))

    rows = db.execute("""
        SELECT applications.*, users.name, users.email
        FROM applications
        JOIN users ON users.id = applications.applicant
        WHERE applications.job_id = ?
        ORDER BY applications.id DESC
    """, (job_id,)).fetchall()
    return render_template("jobs/applicants.html", job=job, applicants=rows)


@app.route("/applications/<int:application_id>/<status>", methods=["POST"])
@login_required
def update_application_status(application_id, status):
    allowed_statuses = {"Shortlisted", "Hired", "Rejected"}
    if status not in allowed_statuses:
        flash("Invalid application status.", "danger")
        return redirect(url_for("jobs"))

    db = get_db()
    application = db.execute("""
        SELECT applications.*, jobs.created_by
        FROM applications
        JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.id = ?
    """, (application_id,)).fetchone()

    if not application or application["created_by"] != session["user_id"]:
        flash("You cannot update this application.", "danger")
        return redirect(url_for("jobs"))

    db.execute("UPDATE applications SET status = ? WHERE id = ?", (status, application_id))
    db.commit()
    flash(f"Applicant marked as {status.lower()}.", "success")
    return redirect(url_for("applicants", job_id=application["job_id"]))


@app.route("/products")
def products():
    rows = get_db().execute("""
        SELECT products.*, users.name AS seller_name
        FROM products
        JOIN users ON users.id = products.seller
        ORDER BY products.id DESC
    """).fetchall()
    return render_template("onlysell/products.html", products=rows)


@app.route("/products/create", methods=["GET", "POST"])
@login_required
def create_product():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()
        category = request.form.get("category", "").strip()
        allow_negotiation = 1 if request.form.get("allow_negotiation") == "on" else 0
        image = save_product_image(request.files.get("image"))

        if not title or not description or not price or not category:
            flash("Product title, description, price, and category are required.", "warning")
            return redirect(url_for("create_product"))

        if parse_money(price) <= 0:
            flash("Enter a valid product price greater than zero.", "warning")
            return redirect(url_for("create_product"))

        get_db().execute(
            """
            INSERT INTO products (title, description, price, category, image, allow_negotiation, seller)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, price, category, image, allow_negotiation, session["user_id"]),
        )
        get_db().commit()
        flash("Product listed.", "success")
        return redirect(url_for("products"))

    return render_template("onlysell/sell.html")


@app.route("/products/<int:product_id>")
def product_detail(product_id):
    product = get_db().execute("""
        SELECT products.*, users.name AS seller_name, users.email AS seller_email
        FROM products
        JOIN users ON users.id = products.seller
        WHERE products.id = ?
    """, (product_id,)).fetchone()

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    return render_template("onlysell/product.html", product=product)


@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = get_db().execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    quantity = request.form.get("quantity", "1")
    try:
        quantity = max(int(quantity), 1)
    except ValueError:
        quantity = 1

    cart_data = get_cart()
    key = str(product_id)
    cart_data[key] = int(cart_data.get(key, 0)) + quantity
    session["cart"] = cart_data
    session.modified = True
    flash("Added to cart.", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    cart_data = get_cart()
    quantity = request.form.get("quantity", "1")

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    key = str(product_id)
    if quantity <= 0:
        cart_data.pop(key, None)
    else:
        cart_data[key] = quantity

    session["cart"] = cart_data
    session.modified = True
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart_data = get_cart()
    cart_data.pop(str(product_id), None)
    session["cart"] = cart_data
    session.modified = True
    flash("Item removed.", "success")
    return redirect(url_for("cart"))


@app.route("/checkout")
@login_required
def checkout():
    items, total = cart_items()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("products"))

    crypto_options = {
        "BTC": app.config["CRYPTO_BTC_ADDRESS"],
        "ETH": app.config["CRYPTO_ETH_ADDRESS"],
        "USDT": app.config["CRYPTO_USDT_ADDRESS"],
    }
    stripe_ready = stripe is not None and bool(app.config["STRIPE_SECRET_KEY"])
    return render_template(
        "onlysell/checkout.html",
        items=items,
        total=total,
        crypto_options=crypto_options,
        stripe_ready=stripe_ready,
    )


@app.route("/checkout/stripe", methods=["POST"])
@login_required
def stripe_checkout():
    if stripe is None or not app.config["STRIPE_SECRET_KEY"]:
        flash("Stripe is not configured yet. Add STRIPE_SECRET_KEY and install stripe.", "warning")
        return redirect(url_for("checkout"))

    order_id = create_order_from_cart(request.form, "stripe", "pending")
    if not order_id:
        return redirect(url_for("checkout"))

    items, total = cart_items()
    stripe.api_key = app.config["STRIPE_SECRET_KEY"]
    line_items = []

    for item in items:
        product = item["product"]
        unit_amount = int(item["price"] * 100)
        line_items.append({
            "price_data": {
                "currency": app.config["STRIPE_CURRENCY"],
                "product_data": {"name": product["title"]},
                "unit_amount": unit_amount,
            },
            "quantity": item["quantity"],
        })

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=url_for("stripe_success", order_id=order_id, _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("checkout", _external=True),
        metadata={"order_id": str(order_id), "buyer_id": str(session["user_id"])},
    )

    get_db().execute(
        "UPDATE orders SET stripe_session_id = ? WHERE id = ?",
        (checkout_session.id, order_id),
    )
    get_db().commit()
    return redirect(checkout_session.url, code=303)


@app.route("/checkout/stripe/success/<int:order_id>")
@login_required
def stripe_success(order_id):
    session_id = request.args.get("session_id", "")
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND buyer = ?",
        (order_id, session["user_id"]),
    ).fetchone()

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("products"))

    if session_id and session_id == order["stripe_session_id"]:
        db.execute(
            "UPDATE orders SET payment_status = 'paid', order_status = 'processing' WHERE id = ?",
            (order_id,),
        )
        db.commit()
        session["cart"] = {}
        flash("Payment complete. Your order is processing.", "success")

    return redirect(url_for("order_success", order_id=order_id))


@app.route("/checkout/crypto", methods=["POST"])
@login_required
def crypto_checkout():
    crypto_currency = request.form.get("crypto_currency", "USDT")
    order_id = create_order_from_cart(request.form, "crypto", "awaiting_crypto", crypto_currency)
    if not order_id:
        return redirect(url_for("checkout"))

    session["cart"] = {}
    flash("Crypto order placed. Complete payment using the wallet details below.", "success")
    return redirect(url_for("crypto_payment", order_id=order_id))


@app.route("/orders/<int:order_id>/crypto")
@login_required
def crypto_payment(order_id):
    order, items = order_with_items(order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("products"))
    return render_template("payments/crypto_payment.html", order=order, items=items)


@app.route("/orders/<int:order_id>/success")
@login_required
def order_success(order_id):
    order, items = order_with_items(order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("products"))
        
    return render_template("onlysell/order_success.html", order=order, items=items)


@login_required
@app.route("/profile")
@login_required
def profile():
    user = current_user()
    db = get_db()

    education = db.execute(
        "SELECT * FROM education WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    experience = db.execute(
        "SELECT * FROM experience WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    skills = db.execute(
        "SELECT * FROM skills WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    portfolio_items = db.execute(
        "SELECT * FROM portfolio_items WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    verification = db.execute(
        "SELECT * FROM verification_requests WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()

    return render_template(
        "profile/profile.html",
        user=user,
        education=education,
        experience=experience,
        skills=skills,
        portfolio_items=portfolio_items,
        verification=verification,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    db = get_db()
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        address = request.form.get("address", "").strip()
        headline = request.form.get("headline", "").strip()
        bio = request.form.get("bio", "").strip()
        website = request.form.get("website", "").strip()
        linkedin = request.form.get("linkedin", "").strip()
        portfolio_url = request.form.get("portfolio_url", "").strip()
        profile_type = request.form.get("profile_type", "freelancer")

        if not name:
            flash("Your name is required.", "danger")
            return redirect(url_for("edit_profile"))
        if len(bio.split()) > 500:
            flash("Your bio must be 500 words or fewer.", "danger")
            return redirect(url_for("edit_profile"))
        if profile_type not in {"freelancer", "employer"}:
            profile_type = "freelancer"

        profile_image = request.files.get("profile_image")
        image_filename = None

        if profile_image and profile_image.filename:
            if not allowed_file(profile_image.filename):
                flash("Use a PNG, JPG, GIF, or WebP profile image.", "danger")
                return redirect(url_for("edit_profile"))
            filename = secure_filename(profile_image.filename)
            image_filename = f"{user_id}_{uuid4().hex}_{filename}"
            profile_image.save(os.path.join(PROFILE_USER_FOLDER, image_filename))

        if image_filename:
            db.execute(
                """
                UPDATE users
                SET name=?,
                    phone=?,
                    location=?,
                    bio=?,
                    address=?,
                    headline=?,
                    website=?,
                    linkedin=?,
                    portfolio_url=?,
                    profile_type=?,
                    profile_image=?
                WHERE id=?
                """,
                (name, phone, location, bio, address, headline, website, linkedin, portfolio_url, profile_type, image_filename, user_id),
            )
        else:
            db.execute(
                """
                UPDATE users
                SET name=?,
                    phone=?,
                    location=?,
                    bio=?,
                    address=?,
                    headline=?,
                    website=?,
                    linkedin=?,
                    portfolio_url=?,
                    profile_type=?
                WHERE id=?
                """,
                (name, phone, location, bio, address, headline, website, linkedin, portfolio_url, profile_type, user_id),
            )

        skill_names = {skill.strip() for skill in request.form.get("skills", "").split(",") if skill.strip()}
        db.execute("DELETE FROM skills WHERE user_id = ?", (user_id,))
        db.executemany("INSERT INTO skills (user_id, name) VALUES (?, ?)", [(user_id, skill[:80]) for skill in skill_names])

        degree = request.form.get("degree", "").strip()
        institution = request.form.get("institution", "").strip()
        if degree and institution:
            db.execute("INSERT INTO education (user_id, degree, institution, year) VALUES (?, ?, ?, ?)", (user_id, degree, institution, request.form.get("education_year", "").strip()))

        job_title = request.form.get("job_title", "").strip()
        company = request.form.get("company", "").strip()
        if job_title and company:
            db.execute(
                """INSERT INTO experience (user_id, job_title, company, location, start_date, end_date, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, job_title, company, request.form.get("experience_location", "").strip(), request.form.get("start_date", "").strip(), request.form.get("end_date", "").strip(), request.form.get("experience_description", "").strip()),
            )

        portfolio_file = request.files.get("portfolio_file")
        portfolio_title = request.form.get("portfolio_title", "").strip()
        if portfolio_file and portfolio_file.filename:
            if not portfolio_title or not allowed_portfolio_file(portfolio_file.filename):
                flash("Add a portfolio title and use an image, PDF, or text file.", "danger")
                return redirect(url_for("edit_profile"))
            file_name = f"portfolio_{user_id}_{uuid4().hex}_{secure_filename(portfolio_file.filename)}"
            portfolio_file.save(os.path.join(UPLOAD_FOLDER, file_name))
            db.execute(
                "INSERT INTO portfolio_items (user_id, title, description, file_path) VALUES (?, ?, ?, ?)",
                (user_id, portfolio_title, request.form.get("portfolio_description", "").strip(), file_name),
            )

        db.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    skills = db.execute("SELECT name FROM skills WHERE user_id = ? ORDER BY name", (user_id,)).fetchall()
    return render_template("profile/edit_profile.html", user=user, skills=skills)


@app.route("/profile/verification", methods=["POST"])
@login_required
def request_verification():
    db = get_db()
    existing = db.execute("SELECT status FROM verification_requests WHERE user_id = ?", (session["user_id"],)).fetchone()
    if existing:
        flash(f"Your verification request is {existing['status']}.", "warning")
    else:
        db.execute("INSERT INTO verification_requests (user_id) VALUES (?)", (session["user_id"],))
        db.commit()
        flash("Verification requested. Our team will review your profile.", "success")
    return redirect(url_for("profile"))


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    db = get_db()
    if request.method == "POST":
        receiver_id = request.form.get("receiver_id")
        body = request.form.get("body", "").strip()

        if not receiver_id or not body:
            flash("Choose a user and write a message.", "warning")
            return redirect(url_for("messages"))

        receiver = db.execute("SELECT id FROM users WHERE id = ?", (receiver_id,)).fetchone()
        if not receiver or int(receiver_id) == session["user_id"]:
            flash("Choose a valid receiver.", "warning")
            return redirect(url_for("messages"))

        db.execute(
            "INSERT INTO messages (sender, receiver, body) VALUES (?, ?, ?)",
            (session["user_id"], receiver_id, body),
        )
        db.commit()
        flash("Message sent.", "success")
        return redirect(url_for("messages"))

    users = db.execute(
        "SELECT id, name, email FROM users WHERE id != ? ORDER BY name",
        (session["user_id"],),
    ).fetchall()
    rows = db.execute("""
        SELECT messages.*, sender.name AS sender_name, receiver.name AS receiver_name
        FROM messages
        JOIN users AS sender ON sender.id = messages.sender
        JOIN users AS receiver ON receiver.id = messages.receiver
        WHERE messages.sender = ? OR messages.receiver = ?
        ORDER BY messages.id DESC
    """, (session["user_id"], session["user_id"])).fetchall()
    return render_template("msg/messages.html", users=users, messages=rows)


@app.route("/wallet")
@login_required
def wallet():
    row = get_db().execute("SELECT * FROM wallets WHERE user_id = ?", (session["user_id"],)).fetchone()
    return render_template("profile/wallet.html", wallet=row)

@app.route("/faq")
def faq():
    return render_template("pages/faq.html")


@app.route("/only-advice")
def only_advice():
    return render_template("pages/only_advice.html")

@app.route("/about")
def about():
    return render_template("pages/about.html")



@app.route("/careers")
def careers():
    return render_template("pages/careers.html")


@app.route("/contact")
def contact():
    return render_template("pages/contact.html")


@app.route("/help")
def help():
    return render_template("pages/help.html")


@app.route("/privacy")
def privacy():
    return render_template("pages/privacy.html")


@app.route("/terms")
def terms():
    return render_template("pages/terms.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)

