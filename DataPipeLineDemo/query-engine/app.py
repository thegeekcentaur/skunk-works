import os
import duckdb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

app = FastAPI()

# Env vars
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
MINIO_BUCKET = os.getenv('MINIO_BUCKET')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
DELTA_PATH = os.getenv('DELTA_PATH')

# Disable AWS metadata fetch explicitly
os.environ['AWS_EC2_METADATA_DISABLED'] = 'true'

# DuckDB connection setup (on startup)
con = duckdb.connect(database=':memory:', read_only=False)
con.execute("INSTALL delta;")
con.execute("LOAD delta;")
con.execute(f"""
    CREATE SECRET delta_s1 (
        TYPE s3,
        KEY_ID '{MINIO_ACCESS_KEY}',
        SECRET '{MINIO_SECRET_KEY}',
        REGION 'us-east-1',
        SCOPE 's3://{MINIO_BUCKET}',
        USE_SSL 'false',
        ENDPOINT '{MINIO_ENDPOINT}',
        URL_STYLE 'path'
    );
""")

# For initial validation/testing
curr_query = f"SELECT device_id, timestamp, temperature, humidity FROM delta_scan('{DELTA_PATH}');"
curr_result = con.execute(curr_query).fetchdf().to_dict(orient='records')
print(f"Found {len(curr_result)} records")

con.execute(f"""
    CREATE OR REPLACE VIEW telemetry_view AS
    SELECT device_id, timestamp, temperature, humidity
    FROM delta_scan('{DELTA_PATH}');
""")
print(f"Created view telemetry_view based on {DELTA_PATH}")


class Query(BaseModel):
    sql: str

@app.post("/query")
def run_query(query: Query):
    try:
        # Execute user SQL (e.g., against the view for stability)
        result = con.execute(query.sql).fetchdf().to_dict(orient='records')
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))