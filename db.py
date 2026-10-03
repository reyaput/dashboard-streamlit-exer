"""MySQL connection helpers for the customer dashboard."""

import os
from pathlib import Path
from typing import Any

import mysql.connector
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_connection() -> Any:
    """Create a MySQL connection from environment variables."""
    config: dict[str, Any] = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("DB_NAME", "customer_dashboard"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
    }

    if os.getenv("DB_SSL_DISABLED", "true").lower() != "true":
        ca_path = Path(os.getenv("DB_SSL_CA", "ca.pem"))
        if not ca_path.is_absolute():
            ca_path = BASE_DIR / ca_path
        config["ssl_ca"] = str(ca_path)
        config["ssl_verify_cert"] = True

    return mysql.connector.connect(**config)


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a read-only query and return rows as dictionaries."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return list(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()
