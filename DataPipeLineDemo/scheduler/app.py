import os
import time
import random
from datetime import datetime
import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text
from deltalake.writer import write_deltalake
from apscheduler.schedulers.background import BackgroundScheduler
import s3fs

# Env vars
POSTGRES_URL = os.getenv('POSTGRES_URL')
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_BUCKET = os.getenv('MINIO_BUCKET')
DELTA_PATH = os.getenv('DELTA_PATH')
NUM_RECORDS = int(os.getenv('NUM_RECORDS', 1000))
EXPORT_INTERVAL = int(os.getenv('EXPORT_INTERVAL', 300))  # Default 5 min

# Storage options for MinIO (non-SSL local)
storage_options = {
    'AWS_ENDPOINT': f'http://{MINIO_ENDPOINT}',
    'AWS_ACCESS_KEY_ID': MINIO_ACCESS_KEY,
    'AWS_SECRET_ACCESS_KEY': MINIO_SECRET_KEY,
    'AWS_ALLOW_HTTP': 'true',
    'AWS_S3_ALLOW_UNSAFE_RENAME': 'true'
}

# Create MinIO bucket if not exists
fs = s3fs.S3FileSystem(
    endpoint_url=f'http://{MINIO_ENDPOINT}',
    key=MINIO_ACCESS_KEY,
    secret=MINIO_SECRET_KEY
)
if not fs.exists(MINIO_BUCKET):
    fs.mkdir(MINIO_BUCKET)

# Seed mock telemetry data
def seed_data(randomize=False):
    sample_size = NUM_RECORDS
    if randomize:
        sample_size = random.randint(1, NUM_RECORDS)
    engine = create_engine(POSTGRES_URL)
    fake = Faker()
    data = []
    for _ in range(sample_size):
        data.append({
            'device_id': fake.uuid4(),
            'timestamp': fake.date_time_this_year(),
            'temperature': fake.random_number(digits=2),
            'humidity': fake.random_number(digits=2)
        })
    df = pd.DataFrame(data)
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS telemetry (device_id VARCHAR, timestamp TIMESTAMP, temperature INT, humidity INT)"))
        df.to_sql('telemetry', conn, if_exists='append', index=False)
        conn.commit()
    with open('/tmp/table_seeding_done', 'a') as f:
        f.write(f"Seeded: {datetime.now().strftime('%H:%M:%S.%f')}, Record(s): {sample_size}\n")
    print(f"Seeded {sample_size} records.")

# Export to Delta Lake in MinIO
def export_data():
    engine = create_engine(POSTGRES_URL)
    df = pd.read_sql('SELECT * FROM telemetry', engine)
    write_deltalake(DELTA_PATH, df, mode='overwrite', schema_mode='merge', storage_options=storage_options)
    with open('/tmp/export_data_done', 'a') as f:
        f.write(f"Exported: {datetime.now().strftime('%H:%M:%S.%f')}, Record(s): {len(df)}\n")
    print("Exported data to Delta Lake.")

if __name__ == '__main__':
    # Seed once on start
    seed_data()
    
    scheduler = BackgroundScheduler()
    # Schedule periodic data seeding, to mimic real-life behaviour
    scheduler.add_job(seed_data, 'interval', seconds=30, args=[True])
    # Schedule periodic export
    scheduler.add_job(export_data, 'interval', seconds=EXPORT_INTERVAL)
    scheduler.start()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()