INSERT INTO dim_patient (patient_id, patient_name, dob, gender)
VALUES (:patient_id, :patient_name, :dob, :gender)
ON CONFLICT (patient_id)
DO UPDATE SET
    patient_name = EXCLUDED.patient_name,
    dob = EXCLUDED.dob,
    gender = EXCLUDED.gender;