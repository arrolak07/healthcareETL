-- 1. Check for orphan treatments (Should return 0)
SELECT 'Orphan Treatments' AS check_name, COUNT(*) AS violation_count
FROM fact_treatment f
LEFT JOIN dim_appointment a ON f.appointment_id = a.appointment_id
WHERE a.appointment_id IS NULL

UNION ALL

-- 2. Check for duplicate appointment IDs (Should return 0)
SELECT 'Duplicate Appointment IDs' AS check_name, COUNT(*) AS violation_count
FROM (
    SELECT appointment_id
    FROM dim_appointment
    GROUP BY appointment_id
    HAVING COUNT(*) > 1
) dupes

UNION ALL

-- 3. Check for invalid negative or zero appointment durations (Should return 0)
SELECT 'Invalid Appointment Durations' AS check_name, COUNT(*) AS violation_count
FROM dim_appointment
WHERE visit_duration_minutes IS NOT NULL AND visit_duration_minutes <= 0;