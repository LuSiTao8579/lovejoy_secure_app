from flask import Flask, render_template,request,redirect,url_for,flash, session
from config import Config
from database.db import (
    close_db,get_db,get_user_by_email,
    create_user,increment_failed_login,
    reset_failed_logins,create_password_reset_token,
    get_password_reset_by_token,mark_password_reset_used,
    update_user_password,create_evaluation_request,
    get_evaluation_requests_by_user,
    get_all_evaluation_requests_with_user,
)
from utils.security import (
    hash_password,check_password_strength,
    verify_password,allowed_image_file,
    generate_safe_image_filename,
)
from utils.auth import start_session,end_session,login_required,admin_required
from utils.csrf import generate_csrf_token,validate_csrf
from utils.email_utils import send_password_reset_email
from datetime import datetime
import os


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY  #using with flash

os.makedirs(app.config["UPLOAD_FOLDER"],exist_ok=True)

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

@app.route("/")
def index():
    return render_template("index.html")    

@app.route("/register",methods = ["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name","").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password","")
        confirm_password = request.form.get("confirm_password", "")

        #check twice password same
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return render_template("register.html")
        
        #check password strength
        ok, msg = check_password_strength(password)
        if not ok:
            flash(msg, "danger")
            return render_template("register.html")
        
        #check email exist
        existing = get_user_by_email(email)
        if existing is not None:
            flash("This email is already registered","danger")
            return render_template("register.html")
        
        #generate hash and count into database
        pw_hash = hash_password(password)
        try:
            create_user(email=email, password_hash=pw_hash,name=name,phone=phone)
        except Exception as e:
            flash("An error occurred while creating your account","danger")
            return render_template("register.html")
        
        #reigster successful
        flash("Registration successful Please login", "success")
        return redirect(url_for("login"))
    #GET request show the table
    return render_template("register.html")


@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        #reminder
        if not user:
            flash("Invalid email or password", "danger")
            return render_template("login.html")
        
        #check whether locked
        locked_util = user.get("locked_util")
        if locked_util is not None:
            now = datetime.utcnow()
            if locked_util > now:
                minutes_left = int((locked_util - now).total_seconds() // 60) + 1
                flash(f"Account locked. try again in about {minutes_left}minutes","danger")
                return render_template("login.html")
            
        #check password
        if not verify_password(password,user["password_hash"]):
            increment_failed_login(user["id"])
            flash("Invalid email or password","danger")
            return render_template("login.html")
        
        #reset failed times and locked time when login success
        reset_failed_logins(user["id"])
        start_session(user)

        flash("Logged in successfully","success")
        return redirect(url_for("index"))
    
    return render_template("login.html",session = session)

@app.route("/logout")
def logout():
    end_session()
    flash("You have been logged out", "info")
    return redirect(url_for("index"))

@app.route("/forgot-password", methods = ["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower

        user = get_user_by_email(email)
        if user:
            token = create_password_reset_token(user["id"])
            send_password_reset_email(email,token)

        flash(
            "if a account with that email exists, a reset link has been sent",
            "info",
        )
        return redirect(url_for("login"))
    
    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        token = request.args.get("token", "")
        if not token:
            flash("Invalid password reset link", "danger")
            return redirect(url_for("forgot_password"))
        
        reset_record = get_password_reset_by_token(token)
        if not reset_record:
            flash("Invalid or expired password reset link", "danger")
            return redirect(url_for("forgot_password"))
        
        if reset_record["used"]:
            flash("This password reset link has already been used", "danger")
            return redirect(url_for("forgot_password"))
        
        return render_template("reset_password.html", token=token)

    #user provide new password
    if request.method == "POST":
        token = request.form.get("token","")
        password = request.form.get("password","")
        confirm_password = request.form.get("confirm_password","")

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return render_template("reset_password.html", token = token)
        
        reset_record = get_password_reset_by_token(token)
        if not reset_record or reset_record["used"] or reset_record["expires_at"]:
            flash("Invalid or expires password reset link", "danger")
            return redirect(url_for("forgot_password"))
        
        #check password strength
        ok,msg = check_password_strength(password)
        if not ok:
            flash(msg, "danger")
            return render_template("reset_password.html", token = token)
        
        #update user's password
        new_hash = hash_password(password)
        update_user_password(reset_record["user_id"],new_hash)
        mark_password_reset_used(reset_record["id"])

        flash("Your password has been reset.Please log in with yout new password", "success")
        return redirect(url_for("login"))

@app.route("/request-eval", methods = ["GET","POST"])
@login_required
def request_eval():
    user_id = session.get("user_id")

    if request.method == "POST":
        comment = request.form.get("comment","").strip()
        preferred_contact = request.form.get("preferred_contact", "email")

        #check contact chance
        if preferred_contact not in ("email", "phone"):
            flash("Invalid contact method","danger")
            return render_template("request_eval.html",request=get_evaluation_requests_by_user(user_id))
        
        if not comment:
            flash("Comment is required", "danger")
            return render_template("request_eval.html", request=get_evaluation_requests_by_user(user_id))
        
        #deal with file and upload file
        file = request.files.get("photo", None)
        if file is None or file.filename == "":
            flash("Please upload an image of item","danger")
            return render_template("request_eval.html", requests=get_evaluation_requests_by_user(user_id))
        
        if not allowed_image_file(file.filename):
            flash("Invalid file type.Please upload JPG,PNG,GIF","danger")
            return render_template("request_eval.html",requests=get_evaluation_requests_by_user(user_id))
        
        try:
            safe_name = generate_safe_image_filename(file.filename)
        except ValueError:
            flash("Unsupported file type","danger")
            return render_template("request_eval.html",requests=get_evaluation_requests_by_user(user_id))
        
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        file.save(save_path)

        #write in database
        create_evaluation_request(
            user_id=user_id,
            comment=comment,
            preferred_contact=preferred_contact,
            image_filename=safe_name,
        )

        flash("Your evaluation request has been submitted","success")
        return redirect(url_for("request_eval"))
    
    #GET: show list anb user's requests
    user_requests = get_evaluation_requests_by_user(user_id)
    return render_template("request_eval.html",requests=user_requests)

@app.route("/admin/requests")
@admin_required
def admin_requests():
    all_requests = get_all_evaluation_requests_with_user()
    return render_template("admin_requests.html", requests=all_requests)


@app.before_request
def csrf_protect():
    validate_csrf()

@app.context_processor
def inject_csrf():
    return dict(csrf_token=generate_csrf_token)






if __name__ == "__main__":
    app.run(debug=True)