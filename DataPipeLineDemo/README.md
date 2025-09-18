# Problem Statement

Establish a data pipeline with PostgreSQL as the source, and MinIO as the desitnation, with the ability to query the MinIO data using standard SQL.

1. Should be a docker based set-up
2. The querying of the MinIO data should not be impacted by any possible change to the underlying schema


## High Level Approach
1. Use off-the-shelf docker images for `postgres` and `minio`
2. Create a python-based container called the `scheduler` that
   - can seed the initial data on the postgres
   - can also create additional postgres data on a periodic basis to simulate real-life scenarios
   - can export the data from postgres at a pre-defined/configurable interval and write it to the minio bucket as *__Delta Lake__* table using datalake writer
3. Create another fastapi-based container called the `query-engine` that
   - can create a view based on the *__Delta Lake__* table, to abosrb any future change to the table
   - expose a simple REST end point to perform querying on this view


## Setup
1. In the Docker Compose file, update the secrets marked as *__#ChangeME__* to desired values.
2. Alternately, copy `.env.example` to `.env` and set vars (e.g., NUM_RECORDS=5000 for more data).
3. Run: `docker-compose up --build`
   - For MinIO: ```localhost:9001``` from browser, and verify a bukcet called `telemetry` is created, with `delta_table` inside
   - For Scheduler, 
      - run ```docker exec -it <container id> cat /tmp/table_seeding_done``` from terminal, and confirm that data is being seeded regularly
      - run ```docker exec -it <container id> cat /tmp/export_data_done``` from terminal, and confirm that data is being exported regularly
   - For API: ```localhost:8000/docs``` (Swagger for testing queries), and run query with the payload ```{"sql": "SELECT COUNT(*) FROM telemetry_view"}```


## How It Works
- Scheduler seeds mock telemetry data on start as well as at a certain interval (configurable volume/sample size).
- Exports to MinIO as Delta Lake (Parquet with metadata) every EXPORT_INTERVAL seconds.
- Query-engine API allows SQL queries via DuckDB (e.g., POST /query with {"sql": "SELECT * FROM telemetry_view"}).


## Schema Change Demo
1. Export runs at least once (wait 5 min or restart scheduler).
2. Query via API: `curl -X POST "http://localhost:8000/query" -H "Content-Type: application/json" -d '{"sql": "SELECT COUNT(*) FROM telemetry_view"}'`
3. Simulate schema change:
   - exec into Postgres: `docker exec -it <postgres_container> psql -U user -d telemetry_db`
   - alter: `ALTER TABLE telemetry ADD COLUMN pressure INT;`
   - insert new data: `INSERT INTO telemetry (device_id, timestamp, temperature, humidity, pressure) VALUES ('test', NOW(), 25, 60, 1013);`
   - wait for next export.
   - re-query the same SQL: It still works (view ignores new 'pressure' column). Delta merges schemas compatibly.
   - to see new column: Query `SELECT * FROM delta_scan('s3://telemetry/delta_table')` directly (but use view for stable contract).
4. In order to safely decouple underlying schema changes from the existing API contract,
   - any schema change should ideally be *__additive__* by nature, so as not to break the *__backward compatibility__*
   - consider *__versioning__* the API as well as the underlying view


## References
1. [Duck Explore](https://github.com/minio/blog-assets/blob/main/duckdb_modern_data_stack/duck_explore.py)
2. [DuckDB Native Delta Lake Support](https://duckdb.org/2024/06/10/delta.html)
3. [MinIO Blog](https://blog.min.io/duckdb-and-minio-for-a-modern-data-stack/)
4. [DuckDB Issue](https://github.com/duckdb/duckdb/issues/13164)
