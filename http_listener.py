#!/bin/env python3
# Example to listen to port  for a post(e.g., data from a data logger!)

from flask import Flask, request
from dotenv import load_dotenv
import os
import psycopg2
import numpy as np
from datetime import datetime, timezone

# Load .env variables
load_dotenv()
PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGPORT = int(os.getenv("PGPORT", 5432))
TABLE = "weather_10sec" # target table in PG database 

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
# Map raw data to DB column names
# --------------------------------------------------

# Cambell Scientific variables: https://help.campbellsci.com/aspen10/aspen/recipes/climavue.htm?tocpath=Recipes%7C_____2
column_map = {
    'BattV': 'batt_v',
    'PTemp_C': 'logger_temp',
    'SlrFD_W': 'solar_flux_density_wm2',
    'Rain_mm': 'precipitation',          # raw 'Rain_mm' → table column 'precipitation'
    'Strikes': 'strikes',
    'Dist_km': 'dist',
    'WS_ms': 'wind_speed',
    'WindDir': 'wind_direction',
    'MaxWS_ms': 'windspdmax', # wind speed max - 10 sec gust
    'AirT_C': 'temperature',
    'VP_mbar': 'vp', # vapor pressure in mbar
    'BP_mbar': 'atmospheric_pressure',
    'RH': 'humidity',
    'RHT_C': 'rhtemp', # internal climavue sensor temp
    'TiltNS_deg': 'tiltns', # climavue tilt north(+)/south(-) (deg)
    'TiltWE_deg': 'tiltwe', # climavue tilt west(+)/east(-) (deg)
    'PrecDropCt': 'precipdrop', 
    'PrecTipCt': 'preciptip', # rain gauge tip count total
    'PrecEC': 'precipec', # rain gauge electrical conductivity
    'SingOrientation': 'tiltxy', # climavue single axis orientation
    'TMin': 'airtempmin', # deg C
    'TMax': 'airtempmax', # deg C
    'SlrTF_MJ': 'cs320_total_energy_mj', # total solar energy in MJ/m2
    'SlrW': 'cs320_irradiance', # irradiance in W/m2
    'Raw_mV': 'cs320_vout', # raw output in mV from pyranometer
    'CS320_Temp': 'cs320_temp', # internal CS320 temperature
    'CS320_Angle': 'cs320_tilt', # tilt angle of CS320 pyranometer
    'SlrMJ': 'cs320_energy_mj' # solar energy in MJ/m2 from CS320
}

def insert_payload(payload):
    fields = payload.split(",")
    data = {}

    for f in fields:
        k, v = f.split("=")
        if k in column_map:
            db_col = column_map[k]
            data[db_col] = float(v)

    # Calculate dewpoint_temperature if vapor_pressure_mbar exists
    if 'vp' in data:
        vp = data['vp']
        val = np.log(vp / 6.112)
        dewpoint = 243.5 * val / (17.67 - val)  # deg C
        data['dewpoint_temp'] = float(dewpoint)
    # Add utc timestamp
    time_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print('utc',time_now)
    data['timestamp_utc'] = time_now


    # Build SQL dynamically
    cols = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    values = tuple(data.values())
    query = f"INSERT INTO {TABLE} ({cols}) VALUES ({placeholders})"

    # Insert into database
    conn = psycopg2.connect(
        host=PGHOST,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        port=PGPORT
    )
    cur = conn.cursor()
    cur.execute(query, values)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/post", methods=["POST"])
def receive_post():
    raw = request.data.decode("utf-8").strip()
    print("Received POST:", raw)
    try:
        insert_payload(raw)
        return {"status": "ok"}, 200
    except Exception as e:
        print("ERROR:", e)
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    print(f"Starting Flask listener on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)

