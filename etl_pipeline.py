import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent
DDL_DIR = BASE_DIR / "sql" / "ddl"
TRANSFORM_DIR = BASE_DIR / "sql" / "transforms"
VALIDATION_SCRIPT = BASE_DIR / "sql" / "validation" / "validate_post_load.sql"

UPSERT_SCRIPTS = [
    ("01_upsert_dim_patient.sql", ["patient_id", "patient_name", "dob", "gender"]),
    ("02_upsert_dim_doctor.sql", ["doctor_id"]),
    ("03_upsert_dim_appointment.sql",
     ["appointment_id", "patient_id", "doctor_id", "start_time", "end_time", "visit_duration_minutes"]),
    ("04_upsert_fact_treatment.sql",
     ["treatment_id", "appointment_id", "treatment_type", "duration_minutes", "cost", "visit_date"]),
]

# LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("healthcare_etl.log"),
        logging.StreamHandler()
    ]
)


# REUSABLE FUNCTIONAL PROGRAMMING UTILITIES
def validate_schema(df, required_columns, file_name):
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"{file_name}: Missing required columns: {missing_columns}")
    logging.info(f"{file_name}: Schema validated successfully.")


def handle_missing(df, column, value):
    df[column] = df[column].fillna(value)
    return df


def remove_duplicates(df, column):
    return df.drop_duplicates(subset=[column])


def calculate_duration(start, end):
    return (end.to_numpy() - start.to_numpy()) / np.timedelta64(1, "m")


def parse_timestamp(series):
    return pd.to_datetime(series, errors="coerce")


# OBJECT-ORIENTED DOMAIN CLASSES
class Patient:
    def __init__(self, patient_id, name, dob, gender):
        self.patient_id = patient_id
        self.name = name
        self.dob = dob
        self.gender = gender


class Appointment:
    def __init__(self, appointment_id, patient_id, start_time, end_time, doctor_id):
        self.appointment_id = appointment_id
        self.patient_id = patient_id
        self.start_time = start_time
        self.end_time = end_time
        self.doctor_id = doctor_id


class DatabaseConnection:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)

    def run_sql_dir(self, directory_path):
        """Executes all .sql DDL files in a folder to create tables/indexes."""
        with self.engine.connect() as conn:
            for sql_file in sorted(Path(directory_path).glob("*.sql")):
                sql_text = sql_file.read_text()
                conn.exec_driver_sql(sql_text)
                conn.commit()
        logging.info("DDL schema, partitions, and indexes created successfully.")

    def upsert_dataframe(self, df, script_path):
        """Takes a dataframe and runs its rows through an SQL upsert script."""
        sql_template = Path(script_path).read_text()
        stmt = text(sql_template)

        df_clean = df.astype(object).where(pd.notnull(df), None)
        records = []
        for row in df_clean.to_dict(orient="records"):
            clean_row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
            records.append(clean_row)

        with self.engine.connect() as conn:
            for row in records:
                conn.execute(stmt, row)
            conn.commit()

    def read_sql_file(self, script_path):
        """Reads and executes a validation or query SQL file."""
        sql_text = Path(script_path).read_text()
        with self.engine.connect() as conn:
            return pd.read_sql(sql_text, conn)


class HealthcareETL:
    def __init__(self, patients_file, appointments_file, treatments_file):
        self.patients_file = patients_file
        self.appointments_file = appointments_file
        self.treatments_file = treatments_file

        self.metrics = {
            "extracted_rows_patients": 0,
            "extracted_rows_appointments": 0,
            "extracted_rows_treatments": 0,
            "invalid_records_count": 0,
            "duplicate_records_removed": 0,
            "rows_loaded": 0
        }
        self.quality_stats = {}

    def extract(self):
        logging.info("--- EXTRACT PHASE STARTED ---")
        try:
            self.patients = pd.read_csv(self.patients_file, on_bad_lines="skip")
            self.appointments = pd.read_csv(self.appointments_file, on_bad_lines="skip")
            self.treatments = pd.read_csv(self.treatments_file, on_bad_lines="skip")

            validate_schema(self.patients, ["patient_id", "patient_name", "dob", "gender"], "patients.csv")
            validate_schema(self.appointments, ["appointment_id", "patient_id", "doctor_id", "start_time", "end_time"], "appointments.csv")
            validate_schema(self.treatments, ["treatment_id", "appointment_id", "treatment_type", "duration_minutes", "cost"], "treatments.csv")

            self.metrics["extracted_rows_patients"] = len(self.patients)
            self.metrics["extracted_rows_appointments"] = len(self.appointments)
            self.metrics["extracted_rows_treatments"] = len(self.treatments)
            logging.info("Extraction and schema validation completed successfully.")
        except FileNotFoundError as e:
            logging.error(f"Critical Error: Missing file - {e}")
            raise

    def validate(self):
        logging.info("--- VALIDATE PHASE STARTED ---")
        # Capture raw quality stats before cleaning
        self.quality_stats["missing_patient_names"] = int(self.patients["patient_name"].isna().sum())
        self.quality_stats["duplicate_patients"] = int(self.patients.duplicated(subset=["patient_id"]).sum())
        self.quality_stats["duplicate_appointments"] = int(self.appointments.duplicated(subset=["appointment_id"]).sum())
        self.quality_stats["duplicate_treatments"] = int(self.treatments.duplicated(subset=["treatment_id"]).sum())
        self.quality_stats["null_patient_ids_in_appts"] = int(self.appointments["patient_id"].isna().sum())
        self.quality_stats["null_treatment_costs"] = int(self.treatments["cost"].isna().sum())

        self.orphan_appointments = ~self.appointments["patient_id"].isin(self.patients["patient_id"])
        self.orphan_treatments = ~self.treatments["appointment_id"].isin(self.appointments["appointment_id"])

        self.quality_stats["orphan_appointments"] = int(self.orphan_appointments.sum())
        self.quality_stats["orphan_treatments"] = int(self.orphan_treatments.sum())

        self.metrics["invalid_records_count"] = int(self.orphan_appointments.sum() + self.orphan_treatments.sum())
        logging.info(f"Invalid/Orphan records flagged: {self.metrics['invalid_records_count']}")

    def transform(self):
        logging.info("--- TRANSFORM & BUSINESS LOGIC PHASE STARTED ---")

        # 1. Clean Patients
        raw_p_len = len(self.patients)
        self.patients = remove_duplicates(self.patients, "patient_id")
        self.metrics["duplicate_records_removed"] += (raw_p_len - len(self.patients))
        self.patients = handle_missing(self.patients, "patient_name", "Unknown")
        self.patients["patient_name"] = self.patients["patient_name"].str.strip().str.title()
        self.patients["dob"] = parse_timestamp(self.patients["dob"]).dt.date
        self.quality_stats["invalid_dob_dates"] = int(pd.isna(self.patients["dob"]).sum())

        # 2. Clean Appointments
        valid_appts = self.appointments[~self.orphan_appointments].copy()
        raw_a_len = len(valid_appts)
        valid_appts = remove_duplicates(valid_appts, "appointment_id")
        self.metrics["duplicate_records_removed"] += (raw_a_len - len(valid_appts))

        valid_appts["patient_id"] = valid_appts["patient_id"].astype(int)
        valid_appts["doctor_id"] = valid_appts["doctor_id"].astype("category")  # Memory optimization
        valid_appts["start_time"] = parse_timestamp(valid_appts["start_time"])
        valid_appts["end_time"] = parse_timestamp(valid_appts["end_time"])

        # Drop rows with invalid start_time
        valid_appts = valid_appts.dropna(subset=["start_time"]).copy()
        self.quality_stats["invalid_end_timestamps"] = int(valid_appts["end_time"].isna().sum())

        # Vectorized duration computation
        valid_appts["visit_duration_minutes"] = calculate_duration(
            valid_appts["start_time"], valid_appts["end_time"]
        )
        # Nullify negative/invalid durations
        valid_appts.loc[valid_appts["visit_duration_minutes"] <= 0, "visit_duration_minutes"] = np.nan
        self.appointments = valid_appts

        # 3. Clean Treatments

        valid_treatments = self.treatments[self.treatments["appointment_id"].isin(self.appointments["appointment_id"])].copy()
        raw_t_len = len(valid_treatments)
        valid_treatments = remove_duplicates(valid_treatments, "treatment_id")
        self.metrics["duplicate_records_removed"] += (raw_t_len - len(valid_treatments))

        valid_treatments["cost"] = pd.to_numeric(valid_treatments["cost"], errors="coerce")
        mean_cost = float(np.nanmean(valid_treatments["cost"].to_numpy()))
        valid_treatments = handle_missing(valid_treatments, "cost", round(mean_cost, 2))
        valid_treatments["treatment_type"] = valid_treatments["treatment_type"].astype("category")  # Memory optimization

        # NumPy Statistical Summaries & Outlier Flagging (Top 1% / 99th percentile)
        cost_arr = valid_treatments["cost"].to_numpy()
        p99_threshold = np.percentile(cost_arr, 99)
        valid_treatments["is_cost_outlier"] = cost_arr >= p99_threshold

        logging.info(f"NumPy Stats -> Mean Cost: ${mean_cost:.2f} | 99th Percentile Outlier Threshold: ${p99_threshold:.2f}")
        self.treatments = valid_treatments

    def enrich(self):
        logging.info("--- ENRICH & DATA QUALITY REPORT PHASE STARTED ---")
        self.enriched_appointments = self.appointments.merge(
            self.patients, on="patient_id", how="left", validate="many_to_one"
        )
        self.enriched_treatments = self.treatments.merge(
            self.appointments[["appointment_id", "patient_id", "doctor_id", "start_time"]],
            on="appointment_id", how="left", validate="many_to_one"
        )

        # Save cleaned CSVs
        self.patients.to_csv("cleaned_patients.csv", index=False)
        self.appointments.to_csv("cleaned_appointments.csv", index=False)
        self.treatments.to_csv("cleaned_treatments.csv", index=False)

        # Generate Data Quality Report CSV
        dq_df = pd.DataFrame(list(self.quality_stats.items()), columns=["Data_Quality_Check", "Issue_Count"])
        dq_df.to_csv("data_quality_report.csv", index=False)
        logging.info("Saved cleaned CSVs and data_quality_report.csv.")

    def load(self, db_conn_input):
        logging.info("--- LOAD PHASE STARTED ---")
        db_connection = DatabaseConnection(db_conn_input) if isinstance(db_conn_input, str) else db_conn_input

        # Recreate schema, partitions, and indexes cleanly
        db_connection.run_sql_dir(DDL_DIR)

        # Prepare fact_treatment with valid visit_date from enriched_treatments
        facts = self.enriched_treatments.copy()
        facts["visit_date"] = facts["start_time"].dt.date
        facts = facts.dropna(subset=["visit_date"]).copy()

        # Prepare dim_doctor (convert category back to int for SQL insert)
        doctors_df = pd.DataFrame({"doctor_id": self.appointments["doctor_id"].astype(int).unique()})
        appts_for_sql = self.appointments.copy()
        appts_for_sql["doctor_id"] = appts_for_sql["doctor_id"].astype(int)

        frames = {
            "01_upsert_dim_patient.sql": self.patients,
            "02_upsert_dim_doctor.sql": doctors_df,
            "03_upsert_dim_appointment.sql": appts_for_sql,
            "04_upsert_fact_treatment.sql": facts,
        }

        for script, columns in UPSERT_SCRIPTS:
            if script in frames:
                db_connection.upsert_dataframe(frames[script][columns], TRANSFORM_DIR / script)

        # Count loaded rows and save audit log to BOTH CSV and PostgreSQL table
        with db_connection.engine.connect() as conn:
            self.metrics["rows_loaded"] = int(
                pd.read_sql(
                    "SELECT (SELECT COUNT(*) FROM dim_patient) + "
                    "(SELECT COUNT(*) FROM dim_doctor) + "
                    "(SELECT COUNT(*) FROM dim_appointment) + "
                    "(SELECT COUNT(*) FROM fact_treatment) AS total",
                    conn
                )["total"].iloc[0]
            )

        audit_df = pd.DataFrame([self.metrics])
        audit_df.to_csv("etl_audit_log.csv", index=False)
        audit_df.to_sql("etl_audit_log", db_connection.engine, if_exists="append", index=False)
        logging.info(f"Audit metrics saved to SQL table etl_audit_log. Total rows loaded: {self.metrics['rows_loaded']}")

        # Run Post-Load SQL Validation
        if VALIDATION_SCRIPT.exists():
            val_results = db_connection.read_sql_file(VALIDATION_SCRIPT)
            logging.info(f"Post-Load SQL Validation Results:\n{val_results.to_string(index=False)}")

    def run(self, db_conn_str):
        logging.info("===== HEALTHCARE ETL PIPELINE STARTED =====")
        self.extract()
        self.validate()
        self.transform()
        self.enrich()
        self.load(db_conn_str)
        logging.info("===== HEALTHCARE ETL PIPELINE COMPLETED =====")


if __name__ == "__main__":
    db_conn_str = "postgresql+psycopg2://postgres:12345@localhost:5433/healthcare_db"
    pipeline = HealthcareETL("patients.csv", "appointments.csv", "treatments.csv")
    pipeline.run(db_conn_str)