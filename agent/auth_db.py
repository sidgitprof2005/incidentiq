"""
SQLite database helper for managing registered users in IncidentIQ.
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = "users.db"


def init_user_db() -> None:
    """
    Initializes the SQLite database schema if not already present.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT,
                picture TEXT,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Successfully initialized users database.")
    except Exception as e:
        logger.error(f"Error initializing user DB: {e}")


def register_user(email: str, name: str, picture: str = "") -> None:
    """
    Inserts a user record or updates their last active login time.
    """
    if not email:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (email, name, picture, last_login)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                name=excluded.name,
                picture=excluded.picture,
                last_login=CURRENT_TIMESTAMP
        """, (email, name, picture))
        conn.commit()
        conn.close()
        logger.info(f"Registered/updated user session: {email}")
    except Exception as e:
        logger.error(f"Error registering user {email}: {e}")


def get_registered_users() -> list:
    """
    Fetches all registered users ordered by their latest activity.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, picture, last_login FROM users ORDER BY last_login DESC")
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error fetching registered users: {e}")
        return []
