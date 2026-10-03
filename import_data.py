"""Import the customer CSV into MySQL."""

from pathlib import Path

import pandas as pd

from db import get_connection


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "customer_master.csv"
TABLE_NAME = "customer_master"


def import_data() -> int:
    """Replace the MySQL table with the current CSV contents."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV tidak ditemukan: {CSV_PATH}")

    frame = pd.read_csv(CSV_PATH)
    frame["customer_postal_code"] = frame["customer_postal_code"].astype(str)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        cursor.execute(
            """CREATE TABLE customer_master (
                customer_id VARCHAR(32) PRIMARY KEY,
                customer_name VARCHAR(150) NOT NULL,
                customer_age SMALLINT NOT NULL,
                gender VARCHAR(30) NOT NULL,
                customer_segment VARCHAR(50) NOT NULL,
                customer_city VARCHAR(150) NOT NULL,
                customer_state VARCHAR(150) NOT NULL,
                customer_country VARCHAR(100) NOT NULL,
                region VARCHAR(50) NOT NULL,
                customer_postal_code VARCHAR(20) NOT NULL,
                customer_acquisition_cost DECIMAL(10, 2) NOT NULL
            )
            """
        )
        rows = [tuple(row) for row in frame.itertuples(index=False, name=None)]
        cursor.executemany(
            """INSERT INTO customer_master
            (customer_id, customer_name, customer_age, gender, customer_segment,
             customer_city, customer_state, customer_country, region,
             customer_postal_code, customer_acquisition_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return len(frame)


if __name__ == "__main__":
    print(f"Imported {import_data():,} customer rows.")
