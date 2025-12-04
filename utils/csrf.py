import secrets
from flask import session,request,abort

def generate_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["_csrf_token"] = token
    return token

def validate_csrf():
    #revise the request(for check)
    if request.method in ("POST","PUT","DELETE","PATCH"):
        session_token = session.get("_csrf_token", None)
        form_token = request.form.get("csrf_token","")
        if not session_token or not form_token or session_token != form_token:
            abort(400)  #csrf check failed