import sqlite3

from flask import g

from config import DATABASE


# ---------------------------------------
# Database connection
# ---------------------------------------

def get_db():

    if "db" not in g:

        g.db = sqlite3.connect(
            DATABASE
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.db


# ---------------------------------------
# Close database
# ---------------------------------------

def close_db(error=None):

    db = g.pop(
        "db",
        None
    )

    if db is not None:

        db.close()


# ---------------------------------------
# Initialize main tables
# ---------------------------------------

def init_db():

    db = sqlite3.connect(
        DATABASE
    )

    db.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor = db.cursor()


    # -------------------------------
    # USERS
    # -------------------------------

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


    # ---------------------------------------
    # Add missing user columns
    # ---------------------------------------

    def add_column_if_missing(
        table,
        column,
        definition
    ):

        columns = [

            row[1]

            for row in cursor.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()

        ]

        if column not in columns:

            cursor.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN {column}
                {definition}
                """
            )


    add_column_if_missing(
        "users",
        "password_reset_code",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "password_reset_expires",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "profile_image",
        "TEXT DEFAULT 'default.png'"
    )


    add_column_if_missing(
        "users",
        "phone",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "location",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "bio",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "verified",
        "INTEGER DEFAULT 0"
    )


    add_column_if_missing(
        "users",
        "headline",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "website",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "linkedin",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "portfolio_url",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "cover_image",
        "TEXT DEFAULT 'default-cover.jpg'"
    )


    add_column_if_missing(
        "users",
        "address",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "profile_type",
        "TEXT DEFAULT 'freelancer'"
    )


    add_column_if_missing(
        "users",
        "auth_provider",
        "TEXT"
    )


    add_column_if_missing(
        "users",
        "auth_subject",
        "TEXT"
    )


    # -------------------------------
    # EDUCATION
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS education (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            degree TEXT NOT NULL,

            institution TEXT NOT NULL,

            year TEXT,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # EXPERIENCE
    # -------------------------------

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

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # SKILLS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            name TEXT NOT NULL,

            UNIQUE(user_id, name),

            FOREIGN KEY(user_id)
            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # -------------------------------
    # PORTFOLIO
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            description TEXT,

            file_path TEXT NOT NULL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # -------------------------------
    # VERIFICATION REQUESTS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE NOT NULL,

            status TEXT DEFAULT 'pending',

            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # ---------------------------------------
    # ONLYADVICE ADVISORS
    # ---------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advisors (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL UNIQUE,

            category TEXT NOT NULL,

            department TEXT NOT NULL,

            expertise TEXT NOT NULL,

            bio TEXT NOT NULL,

            rate_per_minute TEXT NOT NULL,

            availability TEXT,

            rating REAL DEFAULT 0,

            total_reviews INTEGER DEFAULT 0,

            is_verified INTEGER DEFAULT 0,

            created_at TEXT,

            updated_at TEXT,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)



    # -------------------------------
    # WALLET ASSETS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet_assets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            currency TEXT NOT NULL,

            balance REAL DEFAULT 0,

            pending REAL DEFAULT 0,

            lifetime_earnings REAL DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, currency),

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # WALLET TRANSACTIONS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            transaction_type TEXT NOT NULL,

            currency TEXT NOT NULL,

            amount REAL NOT NULL,

            balance_after REAL,

            status TEXT DEFAULT 'completed',

            reference_type TEXT,

            reference_id INTEGER,

            description TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # EXCHANGE TRANSACTIONS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            from_currency TEXT NOT NULL,

            from_amount REAL NOT NULL,

            to_currency TEXT NOT NULL,

            to_amount REAL NOT NULL,

            exchange_rate REAL NOT NULL,

            fee REAL DEFAULT 0,

            status TEXT DEFAULT 'completed',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # WALLET INDEXES
    # -------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user
        ON wallet_transactions(user_id)
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_exchange_transactions_user
        ON exchange_transactions(user_id)
    """)


    db.commit()

    db.close()


# ---------------------------------------
# Remaining database tables
# ---------------------------------------

def init_db_continue():

    db = sqlite3.connect(
        DATABASE
    )

    db.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor = db.cursor()


    # -------------------------------
    # JOBS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            budget TEXT NOT NULL,

            created_by INTEGER NOT NULL,

            FOREIGN KEY(created_by)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # APPLICATIONS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL,

            applicant INTEGER NOT NULL,

            status TEXT DEFAULT 'Applied',

            UNIQUE(job_id, applicant),

            FOREIGN KEY(job_id)
            REFERENCES jobs(id),

            FOREIGN KEY(applicant)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # PRODUCTS
    # -------------------------------

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

            FOREIGN KEY(seller)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # MESSAGES
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender INTEGER NOT NULL,

            receiver INTEGER NOT NULL,

            body TEXT NOT NULL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(sender)
            REFERENCES users(id),

            FOREIGN KEY(receiver)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # WALLETS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE NOT NULL,

            balance REAL DEFAULT 0,

            pending REAL DEFAULT 0,

            lifetime_earnings REAL DEFAULT 0,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # ORDERS
    # -------------------------------

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

            FOREIGN KEY(buyer)
            REFERENCES users(id)

        )
    """)


    # -------------------------------
    # ORDER ITEMS
    # -------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id INTEGER NOT NULL,

            product_id INTEGER NOT NULL,

            seller INTEGER NOT NULL,

            title TEXT NOT NULL,

            quantity INTEGER NOT NULL,

            price REAL NOT NULL,

            FOREIGN KEY(order_id)
            REFERENCES orders(id),

            FOREIGN KEY(product_id)
            REFERENCES products(id),

            FOREIGN KEY(seller)
            REFERENCES users(id)

        )
    """)


    db.commit()

    db.close()