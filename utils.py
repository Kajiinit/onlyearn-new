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
    Send OTP email using the Resend API.
    """

    try:
        import resend

        api_key = current_app.config.get("RESEND_API_KEY")

        if not api_key:
            print("RESEND_API_KEY is missing")
            return False

        resend.api_key = api_key

        params = {
            "from": "OnlyEarn <onboarding@resend.dev>",
            "to": [email],
            "subject": subject,
            "html": f"""
            <div style="
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 40px auto;
                padding: 30px;
                background: #111111;
                color: #ffffff;
                border-radius: 16px;
            ">

                <h1 style="
                    color: #00ff88;
                    margin-bottom: 25px;
                ">
                    OnlyEarn
                </h1>

                <p>Hi {name},</p>

                <p>{intro}:</p>

                <div style="
                    text-align: center;
                    font-size: 34px;
                    font-weight: bold;
                    letter-spacing: 8px;
                    color: #00ff88;
                    background: #1c1c1c;
                    padding: 20px;
                    margin: 25px 0;
                    border-radius: 12px;
                ">
                    {code}
                </div>

                <p>
                    This verification code will expire in
                    <strong>10 minutes</strong>.
                </p>

                <p style="color: #999999;">
                    If you did not request this code, you can safely
                    ignore this email.
                </p>

                <hr style="
                    border: 0;
                    border-top: 1px solid #333333;
                    margin: 30px 0;
                ">

                <p style="color: #777777;">
                    OnlyEarn
                </p>

            </div>
            """
        }

        response = resend.Emails.send(params)

        print("RESEND EMAIL SENT:", response)

        return True

    except Exception as error:

        print("RESEND ERROR:", error)

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
