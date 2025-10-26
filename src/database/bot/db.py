import os
import sqlite3
from typing import Optional

from config import SOURCE_DIR

folder_path = SOURCE_DIR / "data"
os.makedirs(folder_path, exist_ok=True)

file = os.path.join(folder_path, "users.db")
connection = sqlite3.connect(file)
connection.row_factory = sqlite3.Row


def _execute_fetch(query: str, params: list, one: bool):
    """Execute a read-only query and return one row or all rows."""
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()


def fetch(query: str, params: Optional[list] = []):
    """Fetch all rows from a read-only query."""
    return _execute_fetch(query, params, one=False)


def fetch_one(query: str, params: Optional[list] = []):
    """Fetch a single row from a read-only query."""
    return _execute_fetch(query, params, one=True)


def run(query: str, params: Optional[list] = []):
    """Execute a write query (INSERT, UPDATE, DELETE) with commit."""
    cursor = connection.cursor()

    try:
        cursor.execute(query, params)
        connection.commit()
    finally:
        cursor.close()
