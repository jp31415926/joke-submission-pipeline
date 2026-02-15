# db.py
"""
A lightweight MySQL connector module for the joke duplicate-detection suite.

Provides a single public function :func:`fetch_jokes` that retrieves
all jokes from the ``archives`` table.

Author: Your Name
"""

from __future__ import annotations

import logging
from typing import List, Tuple
from db_config import DB_CONFIG

import mysql.connector
from mysql.connector import MySQLConnection, Error as MySQLError

# Custom exception to expose connection problems to callers.
class DBConnectionError(RuntimeError):
    """Raised when a database connection cannot be established."""

# Logger instance – you can configure it in your application entry point.
logger = logging.getLogger(__name__)


def _get_connection() -> MySQLConnection:
    """
    Create a new MySQL connection using ``DB_CONFIG``.

    Returns
    -------
    mysql.connector.MySQLConnection
        An open database connection.

    Raises
    ------
    DBConnectionError
        If the connection could not be established.
    """
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except MySQLError as exc:
        logger.error("Failed to connect to MySQL: %s", exc)
        raise DBConnectionError(f"Could not connect to the database: {exc}") from exc


def fetch_jokes() -> List[Tuple[int, str, str]]:
    """
    Retrieve all jokes from the ``archives`` table.

    The function is idempotent – calling it repeatedly will always
    return the current contents of the table. It never modifies the
    database.

    Returns
    -------
    List[Tuple[int, str, str]]
        A list of ``(id, title, funny)`` tuples.

    Raises
    ------
    DBConnectionError
        If the database connection cannot be established.
    """
    query = "SELECT id, title, funny FROM archives"

    # Acquire a fresh connection each time. This keeps the function
    # stateless and safe to call concurrently.
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        # Convert to list of tuples of the desired types.
        return [(int(r[0]), str(r[1]), str(r[2])) for r in rows]
    except MySQLError as exc:
        logger.error("Query failed: %s", exc)
        raise
    finally:
        # Clean up resources
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        jokes = fetch_jokes()
        print(f"Fetched {len(jokes)} joke(s).")
    except DBConnectionError as exc:
        print(f"Error: {exc}")