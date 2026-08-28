import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from helpers import ( current_user, cart_count)
from extensions import limiter

from database import ( close_db, init_db, init_db_continue)

# ---------------------------------------
# Project path
# ---------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = BASE_DIR

DATABASE = os.path.join(
    PROJECT_ROOT,
    "database.db"
)
# ---------------------------------------
# Load environment
# ---------------------------------------

try:
    from dotenv import load_dotenv

    load_dotenv(
        os.path.join(PROJECT_ROOT, ".env")
    )

except ImportError:
    pass

# ---------------------------------------
# Flask App
# ---------------------------------------

app = Flask(
    __name__,
    template_folder=os.path.join(
        PROJECT_ROOT,
        "templates"
    ),
    static_folder=os.path.join(
        PROJECT_ROOT,
        "static"
    )
)
limiter.init_app(app)

app.config["SECRET_KEY"] = os.environ.get(
    "ONLYEARN_SECRET_KEY",
    "change-this-secret-key"
)

csrf = CSRFProtect(app)
app.config["DATABASE"] = DATABASE
app.teardown_appcontext(close_db)

# ---------------------------------------
# Upload folders
# ---------------------------------------

UPLOAD_FOLDER = os.path.join(
    PROJECT_ROOT,
    "static",
    "uploads"
)

PROFILE_FOLDER = os.path.join(
    PROJECT_ROOT,
    "static",
    "profile"
)

PROFILE_USER_FOLDER = os.path.join(
    PROFILE_FOLDER,
    "users"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    PROFILE_USER_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["PROFILE_USER_FOLDER"] = PROFILE_USER_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    4 * 1024 * 1024
)

# ---------------------------------------
# Payment settings
# ---------------------------------------

app.config["STRIPE_SECRET_KEY"] = os.environ.get(
    "STRIPE_SECRET_KEY",
    ""
)

app.config["STRIPE_CURRENCY"] = os.environ.get(
    "STRIPE_CURRENCY",
    "usd"
)

app.config["CRYPTO_BTC_ADDRESS"] = os.environ.get(
    "CRYPTO_BTC_ADDRESS",
    "bc1q-onlyearn-demo-wallet"
)

app.config["CRYPTO_ETH_ADDRESS"] = os.environ.get(
    "CRYPTO_ETH_ADDRESS",
    "0xOnlyEarnDemoWallet"
)

app.config["CRYPTO_USDT_ADDRESS"] = os.environ.get(
    "CRYPTO_USDT_ADDRESS",
    "TOnlyEarnDemoWallet"
)

# ---------------------------------------
# SMTP
# ---------------------------------------

app.config["SMTP_HOST"] = os.environ.get(
    "SMTP_HOST",
    ""
)

app.config["SMTP_PORT"] = int(
    os.environ.get(
        "SMTP_PORT",
        "587"
    )
)

app.config["SMTP_USERNAME"] = os.environ.get(
    "SMTP_USERNAME",
    ""
)

app.config["SMTP_PASSWORD"] = os.environ.get(
    "SMTP_PASSWORD",
    ""
)

app.config["SMTP_FROM_EMAIL"] = os.environ.get(
    "SMTP_FROM_EMAIL",
    app.config["SMTP_USERNAME"]
)

app.config["SHOW_DEV_OTP"] = os.environ.get(
    "ONLYEARN_SHOW_DEV_OTP",
    "false"
).lower() in {
    "1",
    "true",
    "yes"
}

# ---------------------------------------
# Optional packages
# ---------------------------------------

try:
    import stripe

except ImportError:
    stripe = None

try:
    from authlib.integrations.flask_client import OAuth

except ImportError:
    OAuth = None

# ---------------------------------------
# OAuth
# ---------------------------------------

oauth = None

if OAuth:

    oauth = OAuth(app)

    app.extensions["oauth"] = oauth


# ---------------------------------------
# Context processor
# ---------------------------------------
@app.context_processor
def inject_user():

    return {
        "current_user": current_user(),
        "cart_count": cart_count()
    }

# ---------------------------------------
# Register blueprints
# ---------------------------------------

from routes.auth import auth_bp
from routes.pages import pages_bp
from routes.wallet import wallet_bp
from routes.messages import messages_bp
from routes.profile import profile_bp
from routes.jobs import jobs_bp
from routes.products import products_bp
from routes.cart import cart_bp
from routes.checkout import checkout_bp
from routes.dashboard import dashboard_bp
from routes.advice import advice_bp

app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(wallet_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(checkout_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(advice_bp)



# ---------------------------------------
# Initialize database
# ---------------------------------------

with app.app_context():
    init_db()
    init_db_continue()


# ---------------------------------------
# Local development
# ---------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5001
    )