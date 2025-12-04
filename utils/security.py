import re
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets

def hash_password(password:str) -> str:
    # using PBKDF2 + Random hash(Werkzeug)
    return generate_password_hash(password)

def verify_password(password:str, password_hash:str) -> bool:
    #check password match
    return check_password_hash(password_hash,password)

def check_password_strength(password:str):
    #
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]",password):
        return False, "Password must contain at least 1 uppercase lerrer"
    if not re.search(r"[a-z]",password):
        return False, "Password must contain at least 1 lowercase letter"
    if not re.search(r"\d",password):
        return False, "Password must contain 1 digit"
    if not re.search(r"[^A-Za-z0-9]",password):
        return False, "Password must contain 1 special character"
    return True, ""

ALLOWED_IMAGE_EXTENSIONS = {".jpg",".jpeg",".png",".gif"}

def allowed_image_file(filename: str) -> bool:
    if not filename:
        return False
    _,ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_IMAGE_EXTENSIONS

def generate_safe_image_filename(original_name: str) -> str:
    _,ext = os.path.splitext(original_name)
    ext = ext.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported file type")
    random_part = secrets.token_hex(16)
    return random_part + ext