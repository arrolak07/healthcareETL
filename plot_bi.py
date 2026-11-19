from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://postgres:12345@localhost:5433/healthcare_db")
Path("charts").mkdir(exist_ok=True)


def make_bar_chart(sql, x_col, y_col, title, filename):
    df = pd.read_sql(sql, engine)
    plt.figure(figsize=(8, 4))
    plt.bar(df[x_col].astype(str), df[y_col])
    plt.title(title)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(f"charts/{filename}", dpi=150)
    plt.close()
    print(f"Saved charts/{filename}")


# 1. Most common treatments
make_bar_chart(
    sql="""
        SELECT treatment_type, COUNT(*) AS total
        FROM fact_treatment
        GROUP BY treatment_type
        ORDER BY total DESC;
    """,
    x_col="treatment_type",
    y_col="total",
    title="Most Common Treatments",
    filename="chart1_treatments.png",
)

# 2. Visits per patient (Top 15 most-visited patients)
make_bar_chart(
    sql="""
        SELECT p.patient_name, COUNT(a.appointment_id) AS total_visits
        FROM dim_patient p
        LEFT JOIN dim_appointment a ON p.patient_id = a.patient_id
        GROUP BY p.patient_id, p.patient_name
        ORDER BY total_visits DESC
        LIMIT 15;
    """,
    x_col="patient_name",
    y_col="total_visits",
    title="Top 15 Patients by Visit Count",
    filename="chart2_visits_per_patient.png",
)

# 3. Monthly appointment trends
make_bar_chart(
    sql="""
        SELECT TO_CHAR(start_time, 'YYYY-MM') AS month, COUNT(*) AS appointments
        FROM dim_appointment
        GROUP BY TO_CHAR(start_time, 'YYYY-MM')
        ORDER BY month;
    """,
    x_col="month",
    y_col="appointments",
    title="Monthly Appointments",
    filename="chart3_monthly_appointments.png",
)

# 4. Total cost per patient (Top 15)
make_bar_chart(
    sql="""
        SELECT p.patient_name, COALESCE(SUM(t.cost), 0) AS total_cost
        FROM dim_patient p
        LEFT JOIN dim_appointment a ON p.patient_id = a.patient_id
        LEFT JOIN fact_treatment t ON a.appointment_id = t.appointment_id
        GROUP BY p.patient_id, p.patient_name
        ORDER BY total_cost DESC
        LIMIT 15;
    """,
    x_col="patient_name",
    y_col="total_cost",
    title="Top 15 Patients by Total Cost",
    filename="chart4_patient_cost.png",
)

# 5. Average treatment duration by type
make_bar_chart(
    sql="""
        SELECT treatment_type, AVG(duration_minutes) AS avg_duration
        FROM fact_treatment
        WHERE duration_minutes IS NOT NULL
        GROUP BY treatment_type
        ORDER BY avg_duration DESC;
    """,
    x_col="treatment_type",
    y_col="avg_duration",
    title="Average Treatment Duration (Minutes)",
    filename="chart5_avg_duration.png",
)

# 6. Overlapping appointments per patient (Top 15)
make_bar_chart(
    sql="""
        SELECT p.patient_name, COUNT(*) AS overlapping_pairs
        FROM dim_appointment a1
        JOIN dim_appointment a2
            ON a1.patient_id = a2.patient_id
            AND a1.appointment_id < a2.appointment_id
            AND a1.start_time < a2.end_time
            AND a1.end_time > a2.start_time
        JOIN dim_patient p ON a1.patient_id = p.patient_id
        GROUP BY p.patient_id, p.patient_name
        ORDER BY overlapping_pairs DESC
        LIMIT 15;
    """,
    x_col="patient_name",
    y_col="overlapping_pairs",
    title="Patients with Overlapping Appointments",
    filename="chart6_overlapping_appts.png",
)

# 7. Patients with frequent visits (> 2 per month, Top 15)
make_bar_chart(
    sql="""
        SELECT
            p.patient_name || ' (' || TO_CHAR(a.start_time, 'YYYY-MM') || ')' AS patient_month,
            COUNT(*) AS visits_in_month
        FROM dim_appointment a
        JOIN dim_patient p ON a.patient_id = p.patient_id
        GROUP BY p.patient_id, p.patient_name, TO_CHAR(a.start_time, 'YYYY-MM')
        HAVING COUNT(*) > 2
        ORDER BY visits_in_month DESC
        LIMIT 15;
    """,
    x_col="patient_month",
    y_col="visits_in_month",
    title="Frequent Visits (> 2 Per Month)",
    filename="chart7_frequent_visits.png",
)

# 8. Treatments per doctor (Top 15)
make_bar_chart(
    sql="""
        SELECT d.doctor_id, COUNT(t.treatment_id) AS treatments
        FROM dim_doctor d
        LEFT JOIN dim_appointment a ON d.doctor_id = a.doctor_id
        LEFT JOIN fact_treatment t ON a.appointment_id = t.appointment_id
        GROUP BY d.doctor_id
        ORDER BY treatments DESC
        LIMIT 15;
    """,
    x_col="doctor_id",
    y_col="treatments",
    title="Top 15 Doctors by Treatments",
    filename="chart8_doctor_treatments.png",
)

# 9. Top 1% cost outliers (Top 15)
make_bar_chart(
    sql="""
        SELECT treatment_id::TEXT AS treatment_label, cost
        FROM fact_treatment
        WHERE cost >= (
            SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY cost)
            FROM fact_treatment
            WHERE cost IS NOT NULL
        )
        ORDER BY cost DESC
        LIMIT 15;
    """,
    x_col="treatment_label",
    y_col="cost",
    title="Top 1% Cost Outliers",
    filename="chart9_cost_outliers.png",
)

# 10. Cohort analysis: average treatments per patient by signup month
make_bar_chart(
    sql="""
        SELECT
            first_visit.signup_month,
            COUNT(t.treatment_id) * 1.0 / COUNT(DISTINCT first_visit.patient_id) AS avg_treatments_per_patient
        FROM (
            SELECT
                patient_id,
                TO_CHAR(MIN(start_time), 'YYYY-MM') AS signup_month
            FROM dim_appointment
            GROUP BY patient_id
        ) first_visit
        LEFT JOIN dim_appointment a ON first_visit.patient_id = a.patient_id
        LEFT JOIN fact_treatment t ON a.appointment_id = t.appointment_id
        GROUP BY first_visit.signup_month
        ORDER BY first_visit.signup_month;
    """,
    x_col="signup_month",
    y_col="avg_treatments_per_patient",
    title="Avg Treatments Per Patient by Signup Month",
    filename="chart10_cohort_analysis.png",
)