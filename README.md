This repository sets up a data ingestion pipeline for the McCoy building weather station. The logger sends data via HTTP POST every 10 seconds. The VM receives these posts, parses the data using key value pairs, and inserts it into a PostgreSQL database with http_listener.py.

### Contents
- `http_listener.py` The main Flask server that listens for HTTP POSTs from the logger and inserts data into PostgreSQL. Nohup continues to run this script in the background.
- `requirements.txt` – Python dependencies for the project.
- `get_bom_charts.py` - Python script to download mslp and RGB Himawari satellite images from the BoM website, stored in the bom_images folder. coming soon:*A cron job running this script every 6 hours to download the most recent images*

### Prerequisites
- Python 3.12+
- Install dependencies with:
```bash
pip install -r requirements.txt
```

### Setup
A `.env` file in the repository root contains the following information:
```.env
PGHOST=<hostname> 
PGDATABASE=<database name> 
PGUSER=<PostgreSQL username>
PGPASSWORD=<PostgreSQL password>
PGPORT=5432
```

### Running the server
Navigate to the repository and activate the virtual environment:
```bash
cd Public/src/weather-data-acquisition
source venv/bin/activate
```
- Run the Flask http listener on port 80 (requires sudo):\
`sudo python ./http_listener.py`

### Running in the Background (nohup)
To keep the server running after logging out:
```bash
sudo nohup python ./http_listener.py > listener.log 2>&1 &
```
Check the server:\
`ps aux | grep http_listener.py`\
View logs live:\
`tail -f listener.log`

### Log Management with Cron
The Flask log file (`listener.log`) can grow over time. It is automatically truncated using a cron job. Setup:
- Open your user crontab:
```bash
crontab -e
```
- Add a line to truncate the log daily at midnight:
```bash
0 0 * * * > /home/username/Public/src/weather-data-acquisition/listener.log
```

"""
### Daily Aggregation (weather_daily)

We store raw 10-second observations in `weather_10sec`. `weather_daily` is a persistent table with one row per day,
containing daily summary metrics (means/max/min, counts above/below thresholds, wind direction mean, precipitation
totals and max 10-min intensity, etc.). This table is populated by SQL scripts in `daily_conversion/`.

#### One-time setup / backfill
From `daily_conversion/`, run in order:

psql -h localhost -U weather_stats -d weather -f 01_creat_weather_daily_table.sql
psql -h localhost -U weather_stats -d weather -f 02_backfill_from_weather_regular.sql
psql -h localhost -U weather_stats -d weather -f 03_backfill_from_weather_10sec_existing.sql

#### Daily cron job (yesterday only)
This runs once per day shortly after midnight and appends yesterday’s daily row from `weather_10sec`
into `weather_daily`. It is safe to rerun because `ON CONFLICT (date) DO NOTHING` prevents duplicates.

Install cron:

crontab -e

Add (runs daily at 00:05):

5 0 * * * psql -h localhost -U weather_stats -d weather -f /FULL/PATH/TO/daily_conversion/04_daily_cron_yesterday_weather_10sec.sql

Confirm cron is installed:

crontab -l
"""


### Testing
To test that http_listener.py is working, on VM terminal (not in venv) test:
```
wget --method=POST   --header="Content-Type: application/json"   --body-data='{"message":"test"}'   http://172.23.71.167:80/post   -O -
```

### Archive
- `archive/ingest.py` is not used for our datapipeline, but is maintained in case we want to try a different method in future.