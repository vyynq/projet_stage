import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

_last_verification_codes: dict[str, str] = {}


def get_last_verification_code(email: str) -> str | None:
    return _last_verification_codes.get(email.lower())


def send_verification_email(email: str, code: str):
    _last_verification_codes[email.lower()] = code

    mode = os.getenv("EMAIL_DELIVERY_MODE", "console")
    if mode == "console" or not os.getenv("SMTP_HOST"):
        print(f"[EMAIL_VERIFICATION] Code pour {email}: {code}")
        return

    message = EmailMessage()
    message["Subject"] = "Votre code de verification Airbnb Menage"
    message["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", "no-reply@example.com"))
    message["To"] = email
    message.set_content(
        "Bonjour,\n\n"
        f"Votre code de verification est : {code}\n\n"
        "Ce code expire dans 10 minutes.\n"
    )

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
