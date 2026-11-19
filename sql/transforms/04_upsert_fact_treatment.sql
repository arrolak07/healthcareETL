INSERT INTO fact_treatment (treatment_id, appointment_id, treatment_type, duration_minutes, cost, visit_date)
VALUES (:treatment_id, :appointment_id, :treatment_type, :duration_minutes, :cost, :visit_date)
ON CONFLICT (treatment_id, visit_date)
DO UPDATE SET
    treatment_type = EXCLUDED.treatment_type,
    duration_minutes = EXCLUDED.duration_minutes,
    cost = EXCLUDED.cost;