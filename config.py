import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    DB_HOST =os.getenv("DB_HOST","127.0.0.1")
    DB_PORT =int(os.getenv("DB_PORT",3306))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    SECRET_KEY = os.getenv("SECRET_KEY","dev_key_change_me")

    UPLOAD_FOLDER = os.path.join(BASE_DIR,"static","uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024