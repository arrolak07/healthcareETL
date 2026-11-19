-- ==========================================
-- HEALTHCARE BI ANALYTICAL QUERIES (1 - 10)
-- ==========================================

-- 1. Most common treatments
SELECT
    treatment_type,
    COUNT(*) AS total_treatments
FROM fact_treatment
GROUP BY treatment_type
ORDER BY total_treatments DESC;

-- 2. Average visits per patient
SELECT
    COUNT(a.appointment_id) * 1.0 / COUNT(DISTINCT p.patient_id) AS avg_visits
FROM dim_patient p
LEFT JOIN dim_appointment a
    ON p.patient_id = a.patient_id;

-- 3. Monthly appointment trends
SELECT
    TO_CHAR(start_time, 'YYYY-MM') AS month,
    COUNT(*) AS total_appointments
FROM dim_appointment
GROUP BY TO_CHAR(start_time, 'YYYY-MM')
ORDER BY month;

-- 4. Total cost per patient
SELECT
    p.patient_id,
    p.patient_name,
    COALESCE(SUM(t.cost), 0) AS total_cost
FROM dim_patient p
LEFT JOIN dim_appointment a
    ON p.patient_id = a.patient_id
LEFT JOIN fact_treatment t
    ON a.appointment_id = t.appointment_id
GROUP BY p.patient_id, p.patient_name
ORDER BY total_cost DESC;

-- 5. Average treatment duration by type
SELECT
    treatment_type,
    AVG(duration_minutes) AS avg_duration
FROM fact_treatment
WHERE duration_minutes IS NOT NULL
GROUP BY treatment_type
ORDER BY avg_duration DESC;

-- 6. Patients with overlapping appointments
SELECT
    p.patient_id,
    p.patient_name,
    a1.appointment_id AS appt_1,
    a1.start_time AS appt_1_start,
    a1.end_time AS appt_1_end,
    a2.appointment_id AS appt_2,
    a2.start_time AS appt_2_start,
    a2.end_time AS appt_2_end
FROM dim_appointment a1
JOIN dim_appointment a2
    ON a1.patient_id = a2.patient_id
    AND a1.appointment_id < a2.appointment_id
    AND a1.start_time < a2.end_time
    AND a1.end_time > a2.start_time
JOIN dim_patient p
    ON a1.patient_id = p.patient_id
ORDER BY p.patient_id;

-- 7. Patients with frequent visits (> 2 visits per month; adjust X as needed)
SELECT
    p.patient_id,
    p.patient_name,
    TO_CHAR(a.start_time, 'YYYY-MM') AS month,
    COUNT(*) AS visits_in_month
FROM dim_appointment a
JOIN dim_patient p
    ON a.patient_id = p.patient_id
GROUP BY p.patient_id, p.patient_name, TO_CHAR(a.start_time, 'YYYY-MM')
HAVING COUNT(*) > 2
ORDER BY visits_in_month DESC;

-- 8. Treatments per doctor
SELECT
    d.doctor_id,
    COUNT(t.treatment_id) AS total_treatments
FROM dim_doctor d
LEFT JOIN dim_appointment a
    ON d.doctor_id = a.doctor_id
LEFT JOIN fact_treatment t
    ON a.appointment_id = t.appointment_id
GROUP BY d.doctor_id
ORDER BY total_treatments DESC;

-- 9. Treatment cost outliers (Top 1%)
SELECT
    treatment_id,
    appointment_id,
    treatment_type,
    cost,
    visit_date
FROM fact_treatment
WHERE cost >= (
    SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY cost)
    FROM fact_treatment
    WHERE cost IS NOT NULL
)
ORDER BY cost DESC;

-- 10. Cohort analysis: patients by first visit (signup) month vs treatment frequency
SELECT
    first_visit.signup_month,
    COUNT(DISTINCT first_visit.patient_id) AS patients_count,
    COUNT(t.treatment_id) AS total_treatments,
    COUNT(t.treatment_id) * 1.0 / COUNT(DISTINCT first_visit.patient_id) AS avg_treatments_per_patient
FROM (
    SELECT
        patient_id,
        TO_CHAR(MIN(start_time), 'YYYY-MM') AS signup_month
    FROM dim_appointment
    GROUP BY patient_id
) first_visit
LEFT JOIN dim_appointment a
    ON first_visit.patient_id = a.patient_id
LEFT JOIN fact_treatment t
    ON a.appointment_id = t.appointment_id
GROUP BY first_visit.signup_month
ORDER BY first_visit.signup_month;