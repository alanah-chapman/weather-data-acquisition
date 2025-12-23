#!/usr/bin/env python3
import requests
from time import sleep
from pprint import pprint
from dotenv import load_dotenv
import os

# ------------------------------------------------------------------
# Load environment variables from .env
# ------------------------------------------------------------------
load_dotenv()
CAMPBELL_USER = "admin"
CAMPBELL_PASSWORD = "12345"

if not CAMPBELL_USER or not CAMPBELL_PASSWORD:
    raise ValueError("CAMPBELL_USER or CAMPBELL_PASSWORD not set in .env")

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
LOGGER_IP = "10.100.17.162"
LOGGER_PORT = 80       # Update if logger uses a different port
LOGGER_ENDPOINT = "/csapi/"
POLL_INTERVAL = 10      # seconds
MAX_RETRIES = 5         # retries per request
RETRY_DELAY = 5         # seconds between retries

URL = (
    f"http://{LOGGER_IP}:{LOGGER_PORT}{LOGGER_ENDPOINT}"
    "?command=DataQuery"
    "&mode=most-recent"
    "&format=json"
    "&uri=dl:ClimaVue_10Sec"
    "&p1=1"
)

AUTH = (CAMPBELL_USER, CAMPBELL_PASSWORD)

# ------------------------------------------------------------------
# Polling loop
# ------------------------------------------------------------------
print(f"Starting logger polling every {POLL_INTERVAL} seconds...")

while True:
    success = False
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(URL, auth=AUTH, timeout=10)
            r.raise_for_status()
            j = r.json()

            # Extract the most recent record
            record = j["data"][0]
            fields = [f["name"] for f in j["head"]["fields"]]

            formatted = {
                "timestamp": record["time"],
                "no": record["no"],
                "data": dict(zip(fields, record["vals"]))
            }

            pprint(formatted)
            success = True
            break  # exit retry loop if successful

        except requests.exceptions.RequestException as e:
            print(f"[Attempt {attempt}/{MAX_RETRIES}] Network or HTTP error: {e}")
            sleep(RETRY_DELAY)

        except (KeyError, IndexError, ValueError) as e:
            print(f"[Attempt {attempt}/{MAX_RETRIES}] Unexpected response format: {e}")
            pprint(r.text if 'r' in locals() else "No response")
            sleep(RETRY_DELAY)

    if not success:
            print("Max retries reached. Will try again in next poll.")

