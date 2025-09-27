import os
import sqlite3
from typing import Optional

import aiosqlite

folder_path = os.path.join(os.path.dirname(__file__), "..", "..", "data")
os.makedirs(folder_path, exist_ok=True)

file = "./data/typegg.db"

reader = sqlite3.connect(file)
reader.row_factory = sqlite3.Row
reader.execute("PRAGMA foreign_keys = ON")
reader.execute("PRAGMA journal_mode = WAL")
reader.execute("PRAGMA cache_size = -100000")

writer = sqlite3.connect(file)
writer.row_factory = sqlite3.Row
writer.execute("PRAGMA foreign_keys = ON")
writer.execute("PRAGMA journal_mode = WAL")
writer.execute("PRAGMA cache_size = -100000")


def _execute_fetch(query: str, params: list, one: bool):
    """Execute a read-only query and return one row or all rows."""
    cursor = reader.cursor()
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


async def fetch_async(query, params=[]):
    """Asynchronously fetch all rows from a read-only query."""
    async with aiosqlite.connect(file) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


def run(query: str, params: Optional[list] = []):
    """Execute a write query (INSERT, UPDATE, DELETE) with commit."""
    cursor = writer.cursor()

    try:
        cursor.execute(query, params)
        writer.commit()
    finally:
        cursor.close()


def run_many(query, data):
    """Execute a write query on multiple sets of parameters with commit."""
    cursor = writer.cursor()
    try:
        cursor.executemany(query, data)
        writer.commit()
    finally:
        cursor.close()
