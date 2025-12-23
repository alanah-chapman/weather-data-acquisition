#!/bin/env python3
# Example to listen to port  for a post(e.g., data from a data logger!)

from flask import Flask, request
from dotenv import load_dotenv
import os
import psycopg2

# Load .env variables
load_dotenv()
PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGPORT = int(os.getenv("PGPORT", 5432))
TABLE = "setup_test" # target table in PG database 

# --------------------------------------------------
# Flask setup
# --------------------------------------------------
app = Flask(__name__)
PORT = 80   # matches CR1000Xe HTTPPost target (default is 80)

# --------------------------------------------------
# Get valid DB columns once at startup
# --------------------------------------------------
def get_table_columns():
    conn = psycopg2.connect(
        host=PGHOST,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        port=PGPORT
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
    """, (TABLE,))

    columns = {row[0] for row in cur.fetchall()}

    cur.close()
    conn.close()
    return columns

DB_COLUMNS = get_table_columns()
print("DB columns:", DB_COLUMNS)

# --------------------------------------------------
# Insert row dynamically
# --------------------------------------------------
def insert_row(data: dict):
    keys = list(data.keys())
    values = [data[k] for k in keys]

    columns_sql = ", ".join(keys)
    placeholders = ", ".join(["%s"] * len(values))

    sql = f"""
        INSERT INTO {TABLE} ({columns_sql})
        VALUES ({placeholders})
    """

    conn = psycopg2.connect(
        host=PGHOST,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        port=PGPORT
    )
    cur = conn.cursor()
    cur.execute(sql, values)
    conn.commit()
    cur.close()
    conn.close()

# --------------------------------------------------
# POST endpoint
# --------------------------------------------------
@app.route("/post", methods=["POST"])
def receive_post():
    print("\n--- POST received from logger ---")

    raw = request.data.decode("utf-8").strip()
    print("Raw payload:", raw)

    try:
        parsed = {}

        # Parse key=value pairs
        for pair in raw.split(","):
            key, val = pair.split("=")
            key = key.lower()           # match DB column names
            parsed[key] = float(val)

        # Only keep columns that exist in DB
        filtered = {
            k: v for k, v in parsed.items()
            if k in DB_COLUMNS
        }

        if not filtered:
            raise ValueError("No matching DB columns found")

        insert_row(filtered)

        print("Inserted columns:", filtered.keys())
        return {"status": "ok"}, 200

    except Exception as e:
        print("ERROR:", e)
        return {"status": "error", "message": str(e)}, 500

# --------------------------------------------------
# Run server
# --------------------------------------------------
if __name__ == "__main__":
    print(f"Listening on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)


