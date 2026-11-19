INSERT INTO dim_doctor (doctor_id)
VALUES (:doctor_id)
ON CONFLICT (doctor_id)
DO NOTHING;