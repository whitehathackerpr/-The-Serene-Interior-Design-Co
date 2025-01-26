import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'your-secret-key-here'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '752002'
    MYSQL_DB = 'serene_interior'
    SQLALCHEMY_DATABASE_URI = f'mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
