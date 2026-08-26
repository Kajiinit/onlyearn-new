import random
import smtplib
import sqlite3
import secrets
from datetime import datetime, timedelta
from email.message import EmailMessage
import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import flash, current_app
from werkzeug.security import generate_password_hash

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )

def generate_otp():
    """
    Generate secure 6 digit OTP
    """
    return str(secrets.randbelow(900000) + 100000)



def otp_expiry():
    """
    OTP expires after 10 minutes
    """
    return (
        datetime.utcnow() + timedelta(minutes=10)
    ).isoformat()



def send_otp_email(email, name, code, subject, intro):
    """
    Send OTP email using SMTP
    """

    app = current_app

    print("\n===== SMTP DEBUG =====")
    print("HOST:", app.config.get("SMTP_HOST"))
    print("PORT:", app.config.get("SMTP_PORT"))
    print("USERNAME:", app.config.get("SMTP_USERNAME"))
    print("FROM:", app.config.get("SMTP_FROM_EMAIL"))
    print(
        "PASSWORD LENGTH:",
        len(app.config.get("SMTP_PASSWORD", ""))
    )


    smtp_host = app.config.get("SMTP_HOST")
    smtp_port = app.config.get("SMTP_PORT")
    smtp_username = app.config.get("SMTP_USERNAME")
    smtp_password = app.config.get("SMTP_PASSWORD")
    sender_email = app.config.get("SMTP_FROM_EMAIL")

    if not smtp_host or not sender_email:
        print("SMTP configuration missing")
        return False


    try:

        message = EmailMessage()

        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = email


        message.set_content(
            f"""
Hi {name},

{intro}: {code}

This verification code will expire in 10 minutes.

OnlyEarn
"""
        )


        # SSL connection (Port 465)
        if app.config.get("SMTP_USE_SSL"):

            with smtplib.SMTP_SSL(
                smtp_host,
                smtp_port,
                timeout=15
            ) as server:

                if smtp_username and smtp_password:
                    server.login(
                        smtp_username,
                        smtp_password
                    )

                server.send_message(message)


        # TLS connection (Port 587)
        else:

            with smtplib.SMTP(
                smtp_host,
                smtp_port,
                timeout=15
            ) as server:

                server.ehlo()

                server.starttls()

                server.ehlo()


                if smtp_username and smtp_password:
                    server.login(
                        smtp_username,
                        smtp_password
                    )

                server.send_message(message)


        print("EMAIL SENT SUCCESSFULLY")
        return True


    except Exception as error:

        print(
            "SMTP ERROR:",
            error
        )

        return False




def send_verification_email(email, name, code):

    return send_otp_email(
        email,
        name,
        code,
        "OnlyEarn Email Verification Code",
        "Your OnlyEarn verification code is",
    )




def send_password_reset_email(email, name, code):

    return send_otp_email(
        email,
        name,
        code,
        "OnlyEarn Password Reset Code",
        "Your OnlyEarn password reset code is",
    )

def issue_verification_code(user):

    code = generate_otp()

    db = sqlite3.connect(
        current_app.config["DATABASE"]
    )

    db.row_factory = sqlite3.Row


    db.execute(
        """
        UPDATE users
        SET verification_code = ?,
            verification_expires = ?,
            email_verified = 0
        WHERE id = ?
        """,
        (
            generate_password_hash(code),
            otp_expiry(),
            user["id"],
        ),
    )


    db.commit()


    try:
        sent = send_verification_email(
            user["email"],
            user["name"],
            code,
        )

    except Exception as exc:
        sent = False
        print(
            "Email verification failed:",
            exc
        )


    db.close()


    if sent:

        flash(
            "Verification code sent to your email.",
            "success"
        )

    elif current_app.config.get("SHOW_DEV_OTP"):

        flash(
            f"Development OTP: {code}",
            "warning"
        )

    else:

        flash(
            "We could not send your verification email.",
            "danger"
        )
