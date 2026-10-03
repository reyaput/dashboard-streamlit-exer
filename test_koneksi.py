"""Verify the configured MySQL connection."""

from db import get_connection


if __name__ == "__main__":
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        print("Koneksi MySQL berhasil.")
    finally:
        cursor.close()
        connection.close()
