import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_connection():
    config = {
        'host': os.getenv("DB_HOST"),
        'port': os.getenv("DB_PORT"),
        'dbname': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD")
    }
    return psycopg2.connect(**config)
