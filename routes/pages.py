from flask import Blueprint, render_template


pages_bp = Blueprint(
    "pages",
    __name__
)


# ---------------------------------------
# HOME
# ---------------------------------------

@pages_bp.route("/")
def home():

    return render_template(
        "home/home.html"
    )


# ---------------------------------------
# FAQ
# ---------------------------------------

@pages_bp.route("/faq")
def faq():

    return render_template(
        "pages/faq.html"
    )

# ---------------------------------------
# ABOUT
# ---------------------------------------

@pages_bp.route("/about")
def about():

    return render_template(
        "pages/about.html"
    )


# ---------------------------------------
# CAREERS
# ---------------------------------------

@pages_bp.route("/careers")
def careers():

    return render_template(
        "pages/careers.html"
    )


# ---------------------------------------
# CONTACT
# ---------------------------------------

@pages_bp.route("/contact")
def contact():

    return render_template(
        "pages/contact.html"
    )


# ---------------------------------------
# HELP
# ---------------------------------------

@pages_bp.route("/help")
def help():

    return render_template(
        "pages/help.html"
    )


# ---------------------------------------
# PRIVACY
# ---------------------------------------

@pages_bp.route("/privacy")
def privacy():

    return render_template(
        "pages/privacy.html"
    )


# ---------------------------------------
# TERMS
# ---------------------------------------

@pages_bp.route("/terms")
def terms():

    return render_template(
        "pages/terms.html"
    )
