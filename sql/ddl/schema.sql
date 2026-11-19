-- 1. Drop old tables cleanly
DROP TABLE IF EXISTS fact_treatment CASCADE;
DROP TABLE IF EXISTS dim_appointment CASCADE;
DROP TABLE IF EXISTS dim_doctor CASCADE;
DROP TABLE IF EXISTS dim_patient CASCADE;
DROP TABLE IF EXISTS etl_audit_log CASCADE;

-- 2. Dimension: Patient
CREATE TABLE dim_patient (
    patient_id INT PRIMARY KEY,
    patient_name VARCHAR(150) NOT NULL,
    dob DATE,
    gender VARCHAR(10)
);

-- 3. Dimension: Doctor
CREATE TABLE dim_doctor (
    doctor_id INT PRIMARY KEY
);

-- 4. Dimension: Appointment
CREATE TABLE dim_appointment (
    appointment_id INT PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES dim_patient(patient_id),
    doctor_id INT NOT NULL REFERENCES dim_doctor(doctor_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    visit_duration_minutes FLOAT
);

-- 5. Fact Table: Treatment (Partitioned by visit_date month)
CREATE TABLE fact_treatment (
    treatment_id INT NOT NULL,
    appointment_id INT NOT NULL REFERENCES dim_appointment(appointment_id),
    treatment_type VARCHAR(50) NOT NULL,
    duration_minutes FLOAT,
    cost FLOAT,
    visit_date DATE NOT NULL,
    PRIMARY KEY (treatment_id, visit_date)
) PARTITION BY RANGE (visit_date);

-- Create Monthly Partitions (Covering 2025–2027 + Default Partition)
CREATE TABLE fact_treatment_2025 PARTITION OF fact_treatment
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE fact_treatment_2026_h1 PARTITION OF fact_treatment
    FOR VALUES FROM ('2026-01-01') TO ('2026-07-01');

CREATE TABLE fact_treatment_2026_h2 PARTITION OF fact_treatment
    FOR VALUES FROM ('2026-07-01') TO ('2027-01-01');

CREATE TABLE fact_treatment_default PARTITION OF fact_treatment DEFAULT;

-- 6. Audit Log Table (Required for Python ETL Auditing)
CREATE TABLE etl_audit_log (
    audit_id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extracted_rows_patients INT,
    extracted_rows_appointments INT,
    extracted_rows_treatments INT,
    invalid_records_count INT,
    duplicate_records_removed INT,
    rows_loaded INT
);

-- 7. Performance Indexes on Dimension & Fact Keys
CREATE INDEX idx_appt_patient_id ON dim_appointment(patient_id);
CREATE INDEX idx_appt_doctor_id ON dim_appointment(doctor_id);
CREATE INDEX idx_appt_start_time ON dim_appointment(start_time);
CREATE INDEX idx_fact_appt_id ON fact_treatment(appointment_id);
CREATE INDEX idx_fact_treatment_type ON fact_treatment(treatment_type);