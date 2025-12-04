import pymysql
from flask import g
from config import Config
from datetime import datetime, timedelta
from secrets import token_urlsafe

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host= Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
        )
    return g.db


def close_db(e = None):
    db = g.pop('db',None)
    if db is not None:
        db.close()


#user function
def get_user_by_email(email:str):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cur.fetchone()
    
def create_user(email: str, password_hash: str, name: str, phone: str, role: str = "user"):
    #if exception with email repeat, return new user_id
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            #INSERT INTO users(email, password_hash,name,phone,role)
            #values (&s,&s,&s,&s,&s)
            (email,password_hash,name,phone,role)
        )
        db.commit()
        return cur.lastrowid
    
MAX_FAILED_LOGINS = 3
LOCK_MINUTES = 10

def increment_failed_login(user_id: int):
    #failed for certain times will lock account for some time
    db = get_db()
    with db.cursor() as cur:
        #get the fail times
        cur.execute("SELECT failed_logins FROM users WHERE id = %s",(user_id,))
        row = cur.fetchone()
        current = row["failed_logins"] if row else 0
        new_failed = current + 1

        locked_util = None
        if new_failed >= MAX_FAILED_LOGINS:
            locked_util = datetime.utcnow() + timedelta(minutes= LOCK_MINUTES)
            cur.execute(
                (new_failed,locked_util,user_id)
            )
        else:
            cur.execute(
                (new_failed, user_id)
            )
        db.commit()

def reset_failed_logins(user_id: int):
    #reset the failed times and locked time
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (user_id)
        )
    db.commit()
    

RESET_TOKEN_EXP_HOURS = 1   

def create_password_reset_token(user_id:int) -> str:
    db = get_db()
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXP_HOURS)

    with db.cursor() as cur:
        cur.execute(
            (user_id, token, expires_at)
        )
        db.commit()
    
    return token

def get_password_reset_by_token(token:str):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (token,)
        )
        return cur.fetchone()
    
def mark_password_reset_used(reset_id: int):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (reset_id,)
        )
    db.commit()

def update_user_password(user_id: int, new_password_hash: str):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (new_password_hash,user_id)
        )
        db.commit()

def create_evaluation_request(user_id: int,comment: str, preferred_contact: str,image_filename: str | None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (user_id,comment,preferred_contact,image_filename)
        )
        db.commit()

def get_evaluation_requests_by_user(user_id: int):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            (user_id)
        )
        return cur.fetchall()