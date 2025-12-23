### weather-data-acquisition
This repository sets up a data ingestion pipeline for the McCoy building weather station. The logger sends data via HTTP POST every 10 seconds. The VM receives these posts, parses the data using key value pairs, and inserts it into a PostgreSQL database with http_listener.py.

### Prerequisites
- Python 3.12+
- Install dependencies with:
```bash
pip install -r requirements.txt
```

### Setup
A `.env` file in the repository root contains the following information:
PGHOST=<hostname>
PGDATABASE=<database name>
PGUSER=<PostgreSQL username>
PGPASSWORD=<PostgreSQL password>
PGPORT=5432

### Running the server
Navigate to the repository and activate the virtual environment:
```bash
cd Public/src/weather-data-acquisition
source venv/bin/activate
```
- Run the Flask http listener on port 80 (requires sudo):
`sudo python ./http_listener.py`

### Testing
To test that http_listener.py is working, on VM terminal (not in venv) test:
```
wget --method=POST   --header="Content-Type: application/json"   --body-data='{"message":"test"}'   http://172.23.71.167:5000/post   -O -
```

### Archive
- `archive/ingest.py` is not used for our datapipeline, but is maintained in case we want to try a different method in future.