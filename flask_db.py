import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import threading
import logging
import mysql.connector


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "BILLING"),
    "autocommit": False
}


