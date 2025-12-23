### weather-data-acquisition
This repository sets up a data ingestion pipeline for the McCoy building weather station. The logger sends data via HTTP POST every 10 seconds. The VM receives these posts, parses the data using key value pairs, and inserts it into a PostgreSQL database with http_listener.py.

### Repository Contents
http_listener.py – The main Flask server that listens for HTTP POSTs from the logger and inserts data into PostgreSQL.
requirements.txt – Python dependencies for the project.

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
- Run the Flask http listener on port 80 (requires sudo):
`sudo python ./http_listener.py`

### Running in the Background (nohup)
To keep the server running after logging out:
```bash
sudo nohup python ./http_listener.py > listener.log 2>&1 &
```
Check the server:
`ps aux | grep http_listener.py`
View logs live:
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

### Testing
To test that http_listener.py is working, on VM terminal (not in venv) test:
```
wget --method=POST   --header="Content-Type: application/json"   --body-data='{"message":"test"}'   http://172.23.71.167:80/post   -O -
```

### Archive
- `archive/ingest.py` is not used for our datapipeline, but is maintained in case we want to try a different method in future.