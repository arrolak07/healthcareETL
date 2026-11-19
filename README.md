# Healthcare ETL Pipeline & Dimensional Data Warehouse

An end-to-end **Extract, Transform, Load (ETL)** pipeline, data quality auditing framework and partitioned **PostgreSQL star-schema warehouse**, built with **Python (Pandas, NumPy, SQLAlchemy)**. It turns raw, messy patient, appointment and treatment records into trusted, analytics-ready data for healthcare business intelligence reporting.

---

## 1. Business Problem

A healthcare provider exports patient, appointment and treatment data that contains duplicates, missing values, corrupt timestamps and records that reference non-existent patients or appointments. The business needs this data **cleaned, validated, audited and modelled** so analysts can answer questions such as:

* Which treatments are most common, and what do they cost?
* How often do patients visit, and how do monthly volumes trend?
* Which doctors carry the highest workload?
* Which patients are high-utilisation, and which costs are outliers?
* How do patient cohorts behave over time?

---

## 2. System Architecture & Data Flow

```text
+-------------------+     +---------------------------+     +-----------------------------------+
|   SOURCE LAYER    |     |   PROCESSING LAYER        |     |   STORAGE LAYER (PostgreSQL)      |
|-------------------|     |   etl_pipeline.py         |     |   healthcare_db @ localhost:5433  |
| generate_data.py  |     |                           |     |                                   |
|   |               |     | 1. Extract  - schema &    |     | - dim_patient                     |
|   v               | --> |    data-type validation   | --> | - dim_doctor                      |
| - patients.csv    |     | 2. Validate - DQ profiling|     | - dim_appointment                 |
| - appointments.csv|     |    & orphan detection     |     | - fact_treatment                  |
| - treatments.csv  |     | 3. Transform - clean,     |     |   (36 monthly partitions + default)|
+-------------------+     |    dedupe, NumPy stats    |     | - etl_audit_log (run history)     |
                          | 4. Enrich - merges &      |     +-----------------+-----------------+
                          |    business summaries     |                       |
                          | 5. Load - DDL, upserts,   |                       v
                          |    audit, SQL validation  |     +-----------------------------------+
                          +-------------+-------------+     |   CONSUMPTION LAYER               |
                                        |                   | - validate_post_load.sql          |
                                        v                   | - bi_queries.sql (10 KPIs)        |
                          +---------------------------+     | - plot_bi.py  -> charts/*.png     |
                          |   FILE OUTPUTS            |     | - tableau.py  -> tableau_data/*.csv|
                          | - cleaned_*.csv           |     +-----------------------------------+
                          | - data_quality_report.csv |
                          | - etl_audit_log.csv       |
                          | - reports/*.csv           |
                          | - healthcare_etl.log      |
                          +---------------------------+
```

### Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| Data generation | Faker, random | Synthetic source data with injected defects |
| Processing | Pandas | Cleaning, deduplication, joins |
| Computation | NumPy | Vectorized durations, mean, median, std, percentiles |
| Database access | SQLAlchemy + psycopg2 | Connection engine and PostgreSQL driver |
| Warehouse | PostgreSQL | Star schema, partitions, constraints, indexes |
| Testing | pytest | Unit tests for pipeline functions and domain classes |
| Observability | `logging` + `etl_audit_log` | Run logs and per-run metrics |
| BI | PyCharm DB console, matplotlib, Tableau | Querying and visualization |
| Environment | uv | Reproducible dependency management |

---

## 3. Star Schema / ERD

```text
+-------------------+       +------------------------+       +----------------------+
|   dim_patient     |       |    dim_appointment     |       |   fact_treatment     |
+-------------------+       +------------------------+       |   (partitioned by    |
| PK patient_id     |<------| PK appointment_id      |<------|    visit_date)       |
|    patient_name   |       | FK patient_id          |       +----------------------+
|    dob            |       | FK doctor_id           |       | PK treatment_id      |
|    gender         |       |    start_time          |       | PK visit_date        |
+-------------------+       |    end_time            |       | FK appointment_id    |
                            |    visit_duration_mins |       |    treatment_type    |
+-------------------+       +------------------------+       |    duration_minutes  |
|    dim_doctor     |                  ^                     |    cost              |
+-------------------+                  |                     |    is_cost_outlier   |
| PK doctor_id      |------------------+                     +----------------------+
+-------------------+

+-----------------------------+
|       etl_audit_log         |
+-----------------------------+
| PK audit_id (SERIAL)        |
|    run_timestamp            |
|    extracted_rows_patients  |
|    extracted_rows_appts     |
|    extracted_rows_treatments|
|    transformed_rows         |
|    invalid_records_count    |
|    duplicate_records_removed|
|    rows_loaded              |
+-----------------------------+
```

**Constraints:** primary keys on every table; foreign keys `dim_appointment → dim_patient, dim_doctor` and `fact_treatment → dim_appointment`; `NOT NULL` on `patient_name`, `patient_id`, `doctor_id`, `start_time`, `treatment_type` and `visit_date`. The fact table's primary key includes `visit_date` because PostgreSQL requires the partition key to be part of every unique key on a partitioned table.

---

## 4. Project Directory Structure

```text
healthcareETL/
├── sql/
│   ├── analytics/
│   │   └── bi_queries.sql                # 10 core Business Intelligence queries
│   ├── ddl/
│   │   └── schema.sql                    # Star schema DDL, monthly partitions, indexes, audit table
│   ├── transforms/
│   │   ├── 01_upsert_dim_patient.sql     # Idempotent upsert for patients
│   │   ├── 02_upsert_dim_doctor.sql      # Idempotent upsert for doctors
│   │   ├── 03_upsert_dim_appointment.sql # Idempotent upsert for appointments
│   │   └── 04_upsert_fact_treatment.sql  # Idempotent upsert for partitioned treatments
│   └── validations/
│       └── validate_post_load.sql        # Post-load integrity checks (orphans, duplicates, durations)
├── reports/                              # Business summaries written by the pipeline
│   ├── cost_per_patient.csv
│   ├── cost_per_visit.csv
│   ├── monthly_summary.csv
│   ├── frequent_visitors.csv
│   ├── overlapping_appointments.csv
│   └── statistical_summary.csv
├── generate_data.py                      # Synthetic healthcare data generator (Faker)
├── etl_pipeline.py                       # Main OOP + functional ETL pipeline
├── db_config.py                          # Builds the DB URL from environment variables (no hardcoded password)
├── plot_bi.py                            # Matplotlib charts for the BI queries
├── tableau.py                            # Exports query results as CSVs for Tableau
├── test_etl.py                           # Pytest unit test suite (12 tests)
├── patients.csv                          # Raw patient extract (1,100 rows)
├── appointments.csv                      # Raw appointment extract (5,500 rows)
├── treatments.csv                        # Raw treatment extract (7,500 rows)
├── cleaned_patients.csv                  # Cleansed patient dataset
├── cleaned_appointments.csv              # Cleansed appointment dataset with visit durations
├── cleaned_treatments.csv                # Cleansed treatment dataset with outlier flags
├── data_quality_report.csv               # Data anomaly breakdown
├── etl_audit_log.csv                     # Latest run's audit metrics
├── healthcare_etl.log                    # Timestamped execution log
├── ER.png                                # Entity-relationship diagram
├── pyproject.toml / uv.lock              # Dependencies
└── README.md
```

---

## 5. Pipeline Stages

### Stage 1 — Extract (`extract()`)
* Reads the three CSVs with Pandas (`on_bad_lines="skip"` skips malformed rows instead of crashing).
* `validate_schema()` fails fast if any required column is missing.
* `validate_dtypes()` counts values that cannot be converted to their expected type (IDs, dates, numbers) and records them in the data quality report.

### Stage 2 — Validate (`validate()`)
Profiles the raw data **before** any change: missing names, duplicate IDs, null patient IDs, null costs, and **orphan records** (appointments whose patient does not exist; treatments whose appointment does not exist).

### Stage 3 — Transform (`transform()`)
* **Patients:** deduplicate, fill missing names with `"Unknown"`, trim whitespace, standardize casing, parse dates of birth (invalid → `NULL`).
* **Appointments:** remove orphans, deduplicate, parse timestamps, compute `visit_duration_minutes` with vectorized NumPy; corrupt end times and non-positive durations become `NULL`.
* **Treatments:** keep only treatments linked to a valid appointment, deduplicate, impute missing costs with the NumPy mean, flag the top 1% of costs as outliers.
* **NumPy statistics:** mean treatment cost, median visit duration, standard deviation of treatment duration, 99th percentile cost threshold.
* **Memory:** `doctor_id` and `treatment_type` are cast to the `category` dtype.

### Stage 4 — Enrich (`enrich()`)
* Merges Appointments → Patients and Treatments → Appointments with `validate="many_to_one"` (pandas raises an error if a lookup key is duplicated).
* Calculates business summaries: cost per patient and per visit, monthly appointment and treatment totals, frequent visitors (more than 2 appointments in a calendar month) and overlapping appointments.
* Writes the cleaned CSVs, `data_quality_report.csv` and the `reports/` folder.

### Stage 5 — Load (`load()`)
1. Runs `schema.sql` to rebuild dimensions, the partitioned fact table and indexes. The audit table is created once and never dropped.
2. Upserts the tables in foreign-key order: patients → doctors → appointments → treatments.
3. Counts warehouse rows and appends the run's metrics to `etl_audit_log` (and `etl_audit_log.csv`).
4. Runs `validate_post_load.sql` and logs an error if any check finds violations.

---

## 6. Database Connectivity

| Client | Connection | Used for |
| :--- | :--- | :--- |
| `etl_pipeline.py` | SQLAlchemy engine → psycopg2 | DDL, upserts, audit log, post-load validation |
| PyCharm Database tool | JDBC `jdbc:postgresql://localhost:5433/healthcare_db` | Running `bi_queries.sql`, ERD generation |
| `plot_bi.py`, `tableau.py` | SQLAlchemy engine → psycopg2 | Query results for charts and Tableau extracts |

The connection URL is built by `db_config.py` from environment variables:

```text
postgresql+psycopg2://<PGUSER>:<PGPASSWORD>@<PGHOST>:<PGPORT>/<PGDATABASE>
                       postgres    (env)     localhost  5433   healthcare_db
```

* SQL files use `:named` placeholders, so values are sent as **bound parameters**, which protects against SQL injection.
* Pandas `NaN`/`NaT` values are converted to Python `None`, which PostgreSQL stores as `NULL`.
* Each table is loaded in **one batched transaction**: it loads completely or not at all.

---

## 7. Pipeline Execution Metrics & Data Quality Summary

| Pipeline Metric | Value | Notes |
| :--- | :---: | :--- |
| **Patients Extracted** | `1,100` | Validated against required columns and data types |
| **Appointments Extracted** | `5,500` | Includes orphan and malformed timestamp test cases |
| **Treatments Extracted** | `7,500` | Includes orphan appointment references and null costs |
| **Invalid / Orphan Records Flagged** | `1,134` | `809` orphan appointments + `325` orphan treatments |
| **Duplicate Records Removed** | `288` | `33` patients + `108` appointments + `147` treatments |
| **Rows After Transformation** | `11,608` | Cleaned patients + appointments + treatments (doctors are derived at load) |
| **Total Warehouse Rows Loaded** | `11,708` | `1,067` patients + `100` doctors + `4,583` appointments + `5,958` treatments |
| **Mean Treatment Cost (NumPy)** | `$2,533.18` | `np.nanmean`; also used to impute missing costs |
| **Median Visit Duration (NumPy)** | `66.0 min` | `np.nanmedian` |
| **Std of Treatment Duration (NumPy)** | `50.83 min` | `np.nanstd` |
| **Top 1% Cost Outlier Threshold** | `$4,949.13` | `np.percentile(..., 99)`; `60` treatments flagged and stored in `fact_treatment.is_cost_outlier` |
| **Frequent-Visitor Patient-Months** | `87` | More than 2 appointments in one calendar month |
| **Overlapping Appointments** | `1` | Same patient, overlapping time ranges |
| **Post-Load SQL Validation** | `0 / 0 / 0` | Orphan treatments / duplicate appointment IDs / invalid durations |

### Data Lineage

```text
PATIENTS       1,100 ── −33 duplicates ──────────────────────────────────► 1,067  dim_patient
APPOINTMENTS   5,500 ── −809 orphans ── 4,691 ── −108 duplicates ────────► 4,583  dim_appointment
TREATMENTS     7,500 ── −1,395 orphan/unlinked ── 6,105 ── −147 dups ────► 5,958  fact_treatment
DOCTORS        derived from appointments ────────────────────────────────►   100  dim_doctor
                                                                           ──────
                                                                           11,708 rows loaded
```

`1,395` treatments are excluded in total: the `325` that reference appointments that never existed, plus those whose appointment was itself removed as an orphan or duplicate.

### Data Quality Report (`data_quality_report.csv`)

| Check | Count |
| :--- | :---: |
| Invalid date-of-birth values (type check) | 55 |
| Invalid end-time values (type check) | 269 |
| Missing patient names | 47 |
| Duplicate patients / appointments / treatments (raw) | 33 / 159 / 203 |
| Null patient IDs in appointments | 233 |
| Null treatment costs | 358 |
| Orphan appointments / treatments | 809 / 325 |
| Invalid DOBs after cleaning | 50 |
| Invalid end timestamps after cleaning | 229 |
| Cost outliers flagged | 60 |
| Frequent-visitor patient-months | 87 |
| Overlapping appointments | 1 |

---

## 8. Business Intelligence Queries (`sql/analytics/bi_queries.sql`)

| # | Business Question | SQL Technique |
| :---: | :--- | :--- |
| 1 | Most common treatments | `GROUP BY`, `ORDER BY` |
| 2 | Average visits per patient | `LEFT JOIN`, ratio of counts |
| 3 | Monthly appointment trends | `TO_CHAR(start_time, 'YYYY-MM')` |
| 4 | Total treatment cost per patient | 3-table join, `COALESCE` |
| 5 | Average duration by treatment type | `AVG` excluding `NULL`s |
| 6 | Overlapping appointments | Self-join with interval overlap |
| 7 | Frequent visits (> 2 per month) | `GROUP BY` + `HAVING` |
| 8 | Treatments per doctor | Dimension-to-fact `LEFT JOIN` chain |
| 9 | High-cost outliers (top 1%) | `PERCENTILE_CONT(0.99)` subquery |
| 10 | Patient cohort analysis | First-visit month as cohort |

---

## 9. Performance & Optimization

### Python (`etl_pipeline.py`)
* **Vectorized NumPy:** visit durations and all statistics run on whole arrays instead of row-by-row Python loops.
* **Category dtype:** low-cardinality columns (`doctor_id`, `treatment_type`) use less memory.
* **Batched loads:** each table is sent to PostgreSQL in one `executemany` call inside a single transaction.

### PostgreSQL (`sql/ddl/schema.sql`)
* **Monthly range partitioning:** `fact_treatment` has one partition per month (`fact_treatment_2025_01` … `fact_treatment_2027_12`, created by a `DO` loop) plus a `DEFAULT` partition. A query for one month scans only that month's partition (**partition pruning**).
* **Indexes:** B-tree indexes on `patient_id`, `doctor_id`, `start_time`, `appointment_id` and `treatment_type`, plus the indexes created by every primary key.
* **Idempotent upserts:** `INSERT ... ON CONFLICT DO UPDATE / DO NOTHING`, so reruns never create duplicates.
* **Persistent audit history:** `etl_audit_log` uses `CREATE TABLE IF NOT EXISTS` and is never dropped, so every run appends one row.

---

## 10. Key Assumptions

1. **Referential integrity:** orphan appointments and orphan treatments are excluded before the load so foreign keys always hold.
2. **Missing values:**
   * Missing `patient_name` → `"Unknown"`.
   * Missing treatment `cost` → mean cost (`$2,533.18`).
   * Corrupt `end_time` or non-positive duration → `NULL`; the appointment itself is kept.
3. **Duplicates:** the first occurrence of each ID is kept.
4. **Cohort proxy:** without a registration date, a patient's first visit month is used as their cohort.
5. **Frequent visitor:** more than 2 appointments in one calendar month.
6. **Cost outlier:** cost at or above the 99th percentile.
7. **Doctors:** there is no doctors source file, so `dim_doctor` is built from the distinct doctor IDs in appointments.

---

## 11. Testing

`test_etl.py` contains 12 pytest tests covering:

* visit duration calculation, including invalid end times;
* cost aggregation per patient and per visit;
* duplicate removal;
* schema and data-type validation;
* missing-value handling;
* outlier, frequent-visitor and overlap detection;
* the `Patient` and `Appointment` domain classes, which are cross-checked against the vectorized functions.

---

## 12. Setup & Execution Guide

### Prerequisites
* Python 3.12+
* PostgreSQL running locally on port `5433` with a database named `healthcare_db`
* Install dependencies:
  ```bash
  uv sync
  ```
* Set the database password as an environment variable (it is never stored in code):
  * macOS / Linux: `export PGPASSWORD=your_password`
  * Windows PowerShell: `$env:PGPASSWORD = "your_password"`
  * PyCharm: *Run → Edit Configurations → Environment variables* → `PGPASSWORD=your_password`
  * Optional overrides: `PGUSER`, `PGHOST`, `PGPORT`, `PGDATABASE`, or a full `HEALTHCARE_DB_URL`

### Step-by-Step Execution

1. **Generate synthetic raw datasets**
   ```bash
   python generate_data.py
   ```

2. **Run the ETL pipeline and post-load validation**
   ```bash
   python etl_pipeline.py
   ```
   Creates the schema, partitions and indexes; cleans and upserts all records; writes the reports and audit metrics; and runs `validate_post_load.sql`. The log ends with `Post-load validation passed` when all checks return 0 violations.

3. **Run the unit tests**
   ```bash
   pytest test_etl.py
   ```

4. **Run the business intelligence queries**
   Open `sql/analytics/bi_queries.sql` in PyCharm's Database console, connected to `healthcare_db@localhost` (PostgreSQL dialect), and run the 10 queries.

5. **Generate charts and Tableau extracts**
   ```bash
   python plot_bi.py      # writes charts/*.png
   python tableau.py      # writes tableau_data/*.csv
   ```

> **Note:** `ER.png` was generated before monthly partitions and the `is_cost_outlier` column were added. Regenerate it in PyCharm (*right-click the schema → Diagrams → Show Diagram*) after the next pipeline run.
