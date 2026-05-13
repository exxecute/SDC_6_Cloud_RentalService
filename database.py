import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("ODBC_CONNECTION_STRING")


def get_connection():
    return pyodbc.connect(connection_string)
