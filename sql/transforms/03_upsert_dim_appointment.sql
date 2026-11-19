INSERT INTO dim_appointment (appointment_id, patient_id, doctor_id, start_time, end_time, visit_duration_minutes)
VALUES (:appointment_id, :patient_id, :doctor_id, :start_time, :end_time, :visit_duration_minutes)
ON CONFLICT (appointment_id)
DO UPDATE SET
    patient_id = EXCLUDED.patient_id,
    doctor_id = EXCLUDED.doctor_id,
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    visit_duration_minutes = EXCLUDED.visit_duration_minutes;