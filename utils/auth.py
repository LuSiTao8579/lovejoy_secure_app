from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "warning")
            return redirect(url_for("loging"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("admin access only","danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped

def start_session(user):
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    session["role"] = user["role"]

def end_session():
    session.clear()