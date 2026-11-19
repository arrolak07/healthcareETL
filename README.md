# Healthcare ETL 

An end-to-end Extract, Transform, Load (ETL) pipeline, data quality auditing framework, and dimensional data warehouse built with **Python (Pandas, NumPy, SQLAlchemy)** and **PostgreSQL**. This project structures raw patient visit and treatment records into a partitioned Star Schema optimized for healthcare business intelligence reporting.

---

## 1. System Architecture & Data Flow

```text
+-------------------+     +-----------------------+     +----------------------------------+
|   Raw CSV Data    |     |  Python ETL Pipeline  |     |  PostgreSQL Data Warehouse       |
|-------------------|     |   (etl_pipeline.py)   |     |   (healthcare_db @ localhost)    |
| - patients.csv    | --> | 1. Extract & Schema   | --> | - dim_patient                    |
| - appointments.csv|     | 2. Validate & Flag    |     | - dim_doctor                     |
| - treatments.csv  |     | 3. Transform & NumPy  |     | - dim_appointment                |
+-------------------+     | 4. Enrich & DQ Report |     | - fact_treatment (Partitioned)   |
                          | 5. Upsert & Audit Log |     | - etl_audit_log                  |
                          +-----------------------+     +----------------------------------+
                                      |                                   |
                                      v                                   v
                          +-----------------------+     +----------------------------------+
                          |   Local Audit Files   |     |     SQL Validation & BI          |
                          | - healthcare_etl.log  |     | - validate_post_load.sql         |
                          | - data_quality_report |     | - bi_queries.sql (10 Core KPIs)  |
                          | - etl_audit_log.csv   |     +----------------------------------+
                          +-----------------------+
```

### Star Schema / ERD
```text
+-------------------+       +------------------------+       +--------------------+
|   dim_patient     |       |    dim_appointment     |       |   fact_treatment   |
+-------------------+       +------------------------+       +--------------------+
| PK patient_id     |<------| PK appointment_id      |<------| PK treatment_id    |
|    patient_name   |       | FK patient_id          |       | PK visit_date      |
|    dob            |       | FK doctor_id           |       | FK appointment_id  |
|    gender         |       |    start_time          |       |    treatment_type  |
+-------------------+       |    end_time            |       |    duration_minutes|
                            |    visit_duration_mins |       |    cost            |
+-------------------+       +------------------------+       +--------------------+
|    dim_doctor     |                  ^
+-------------------+                  |
| PK doctor_id      |------------------+
+-------------------+
```

---

## 2. Project Directory Structure

```text
healthcareETL/
├── sql/
│   ├── analytics/
│   │   └── bi_queries.sql              # 10 core Business Intelligence queries
│   ├── ddl/
│   │   └── schema.sql                  # Star schema DDL, monthly partitions & indexes
│   ├── transforms/
│   │   ├── 01_upsert_dim_patient.sql   # Idempotent upsert for patients
│   │   ├── 02_upsert_dim_doctor.sql    # Idempotent upsert for doctors
│   │   ├── 03_upsert_dim_appointment.sql # Idempotent upsert for appointments
│   │   └── 04_upsert_fact_treatment.sql  # Idempotent upsert for partitioned treatments
│   └── validation/
│       └── validate_post_load.sql      # Post-load integrity checks (orphans, dupes, durations)
├── generate_data.py                    # Synthetic healthcare data generator (Faker + NumPy)
├── etl_pipeline.py                     # Main OOP + Functional ETL pipeline
├── test_etl.py                         # Pytest unit test suite
├── patients.csv                        # Raw patient extract (1,100 rows)
├── appointments.csv                    # Raw appointment extract (5,500 rows)
├── treatments.csv                      # Raw treatment extract (7,500 rows)
├── cleaned_patients.csv                # Cleansed patient dataset
├── cleaned_appointments.csv            # Cleansed appointment dataset
├── cleaned_treatments.csv              # Cleansed treatment dataset with outlier flags
├── data_quality_report.csv             # Granular data anomaly breakdown
├── etl_audit_log.csv                   # Pipeline execution audit metrics
├── healthcare_etl.log                  # Timestamped execution & NumPy stats log
└── README.md                           # Architecture & project documentation
```

---

## 3. Pipeline Execution Metrics & Data Quality Summary

Based on the latest production execution (`healthcare_etl.log`):

| Pipeline Metric | Value | Notes |
| :--- | :---: | :--- |
| **Patients Extracted** | `1,100` | Validated against required schema columns |
| **Appointments Extracted** | `5,500` | Includes orphan and malformed timestamp test cases |
| **Treatments Extracted** | `7,500` | Includes orphan appointment references and null costs |
| **Invalid / Orphan Records Flagged** | `1,134` | `809` orphan appointments + `325` orphan treatments |
| **Duplicate Records Removed** | `395` | Deduplicated across `patient_id`, `appointment_id`, `treatment_id` |
| **Total Warehouse Rows Loaded** | `11,708` | Loaded across `dim_patient`, `dim_doctor`, `dim_appointment`, `fact_treatment` |
| **Mean Treatment Cost (NumPy)** | `$2,533.18` | Computed via `np.nanmean` and used for null cost imputation |
| **Top 1% Cost Outlier Threshold** | `$4,949.13` | Computed via `np.percentile(..., 99)` |

---

## 4. Performance & Optimization Engineering

### Python Optimizations (`etl_pipeline.py`)
* **Memory Optimization:** Low-cardinality columns (`doctor_id` and `treatment_type`) are explicitly cast to Pandas `category` dtype during transformation to minimize RAM usage.
* **Vectorized Computations:** All visit durations (`calculate_duration`) and statistical aggregations (`np.nanmean`, `np.percentile`) use contiguous **NumPy** arrays (`np.timedelta64(1, "m")`) rather than row-wise Python loops.

### PostgreSQL Optimizations (`sql/ddl/schema.sql`)
* **Range Partitioning:** `fact_treatment` is partitioned by `visit_date` (`PARTITION BY RANGE (visit_date)`) to accelerate monthly and historical range scans.
* **Indexing:** B-Tree indexes are created on all foreign key and high-selectivity columns (`patient_id`, `doctor_id`, `appointment_id`, `start_time`, and `treatment_type`).
* **Idempotent Upserts:** All dimension and fact loads utilize `INSERT ... ON CONFLICT DO UPDATE/NOTHING` to prevent duplicate entries across reruns.

---

## 5. Key Architectural Assumptions

1. **Referential Integrity Enforcement:** Orphan appointments (missing `patient_id`) and orphan treatments (missing `appointment_id`) are quarantined and excluded prior to warehouse load so foreign key constraints remain strictly enforced.
2. **Missing Value Strategy:**
   * Missing `patient_name` values are standardized to `"Unknown"` and title-cased.
   * Missing treatment `cost` values are imputed with the dataset's vectorized mean (`$2,533.18`).
   * Corrupt `end_time` timestamps or non-positive durations (`<= 0` minutes) are coerced to `NULL` (`NaN`) rather than dropping valid appointment check-ins.
3. **Cohort Analysis Proxy:** Because raw patient records do not include a CRM registration timestamp, a patient's first recorded visit month (`MIN(start_time)`) is used as their signup cohort month in `bi_queries.sql`.
4. **Frequent Visit Threshold:** Query #7 in `bi_queries.sql` flags high-utilization patients exceeding `> 2` appointments within a single calendar month.

---

## 6. Setup & Execution Guide

### Prerequisites
* Python 3.12+ (`pandas`, `numpy`, `sqlalchemy`, `psycopg2-binary`, `faker`, `pytest`)
* PostgreSQL running locally on port `5433` with database `healthcare_db`

### Step-by-Step Execution
1. **Generate Synthetic Raw Datasets:**
   ```bash
   python generate_data.py
   ```
2. **Run the ETL Pipeline & Post-Load Validation:**
   ```bash
   python etl_pipeline.py
   ```
   *Creates the Star Schema, partitions, and indexes; cleans and upserts all records; writes audit metrics to the `etl_audit_log` SQL table; and executes `validate_post_load.sql`.*
3. **Run Unit Tests:**
   ```bash
   pytest test_etl.py
   ```
4. **Execute Business Intelligence Queries:**
   Open `sql/analytics/bi_queries.sql` in PyCharm's Database console connected to `healthcare_db@localhost` (PostgreSQL dialect) and run all 10 analytical queries.