import requests
from time import sleep
from pprint import pprint
from dotenv import load_dotenv
import os

# ------------------------------------------------------------------
# Load environment variables from .env
# ------------------------------------------------------------------
# Expects:
#   CAMPBELL_USER
#   CAMPBELL_PASSWORD
load_dotenv()

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

# Campbell internal REST API endpoint
# - DataQuery        → query table data
# - most-recent      → always return the newest record
# - format=json      → machine-readable output
# - uri=dl:ClimaVue_10Sec → 10-second ClimaVue table
# - p1=1             → return exactly one record
URL = (
    "http://10.100.17.162/csapi/"
    "?command=DataQuery"
    "&mode=most-recent"
    "&format=json"
    "&uri=dl:ClimaVue_10Sec"
    "&p1=1"
)

# HTTP basic authentication for the logger
AUTH = (
    os.getenv("CAMPBELL_USER"),
    os.getenv("CAMPBELL_PASSWORD"),
)

# How often to poll the logger (seconds)
POLL_INTERVAL = 10

# ------------------------------------------------------------------
# Main polling loop
# ------------------------------------------------------------------
# The logger cannot POST to us, so we continuously PULL the latest data
while True:
    # Send request to the logger
    r = requests.get(URL, auth=AUTH, timeout=10)

    # Parse JSON response
    j = r.json()

    # Extract the most recent record
    record = j["data"][0]

    # Extract ordered list of field names from metadata
    fields = [f["name"] for f in j["head"]["fields"]]

    # Build clean, DB-ready structure
    formatted = {
        "timestamp": record["time"],   # ISO timestamp from logger
        "no": record["no"],             # Record sequence number
        "data": dict(zip(fields, record["vals"]))  # name → value mapping
    }

    # Output (replace with DB insert / API forward later)
    pprint(formatted)

    # Wait before next poll
    sleep(POLL_INTERVAL)
 