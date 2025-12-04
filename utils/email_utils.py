from flask import current_app

def send_password_reset_email(to_email: str, token: str):
    reset_link = f"http://localhost:5000/reset-password?token={token}"

    current_app.logger.info(f"[DEV] password reset link for {to_email}:{reset_link}")