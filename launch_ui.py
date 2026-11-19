from pathlib import Path
import webbrowser
import pandas as pd
from sqlalchemy import create_engine

import plot_bi

engine = create_engine("postgresql+psycopg2://postgres:12345@localhost:5433/healthcare_db")


def get_kpis():
    df = pd.read_sql(
        """
        SELECT
            COUNT(DISTINCT p.patient_id) AS total_patients,
            COUNT(a.appointment_id) AS total_appointments,
            COUNT(t.treatment_id) AS total_treatments,
            COALESCE(COUNT(a.appointment_id) * 1.0 / NULLIF(COUNT(DISTINCT p.patient_id), 0), 0) AS avg_visits
        FROM dim_patient p
        LEFT JOIN dim_appointment a ON p.patient_id = a.patient_id
        LEFT JOIN fact_treatment t ON a.appointment_id = t.appointment_id;
        """,
        engine,
    )
    return df.iloc[0]


def build_html():
    kpis = get_kpis()

    cards = [
        ("1. Most Common Treatments", "charts/chart1_treatments.png"),
        ("2. Top 15 Patients by Visit Count", "charts/chart2_visits_per_patient.png"),
        ("3. Monthly Appointment Trends", "charts/chart3_monthly_appointments.png"),
        ("4. Total Cost Per Patient (Top 15)", "charts/chart4_patient_cost.png"),
        ("5. Average Treatment Duration (Mins)", "charts/chart5_avg_duration.png"),
        ("6. Overlapping Appointments", "charts/chart6_overlapping_appts.png"),
        ("7. Frequent Visits (> 2 Per Month)", "charts/chart7_frequent_visits.png"),
        ("8. Treatments Per Doctor (Top 15)", "charts/chart8_doctor_treatments.png"),
        ("9. Treatment Cost Outliers (Top 1%)", "charts/chart9_cost_outliers.png"),
        ("10. Cohort Analysis: Signup Month", "charts/chart10_cohort_analysis.png"),
    ]

    cards_html = "\n".join(
        f"""
        <div class="card">
            <h3>{title}</h3>
            <img src="{img_path}" alt="{title}">
        </div>
        """
        for title, img_path in cards
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Healthcare ETL — BI Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f4f6f9;
            margin: 0;
            padding: 24px 32px;
            color: #1e293b;
        }}
        h1 {{
            margin: 0 0 6px 0;
            font-size: 26px;
        }}
        .subtitle {{
            color: #64748b;
            margin-bottom: 24px;
            font-size: 14px;
        }}
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi {{
            background: #ffffff;
            padding: 16px 20px;
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        }}
        .kpi-label {{
            font-size: 13px;
            color: #64748b;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        .card {{
            background: #ffffff;
            padding: 16px;
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        }}
        .card h3 {{
            margin: 0 0 12px 0;
            font-size: 15px;
            color: #1e293b;
        }}
        .card img {{
            width: 100%;
            height: auto;
            border-radius: 6px;
            display: block;
        }}
    </style>
</head>
<body>
    <h1>Healthcare ETL — Business Intelligence Dashboard</h1>
    <div class="subtitle">PostgreSQL Data Warehouse (healthcare_db) • All 10 Analytical Queries</div>

    <div class="kpi-row">
        <div class="kpi">
            <div class="kpi-label">Total Patients</div>
            <div class="kpi-value">{int(kpis['total_patients']):,}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Total Appointments</div>
            <div class="kpi-value">{int(kpis['total_appointments']):,}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Total Treatments</div>
            <div class="kpi-value">{int(kpis['total_treatments']):,}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Avg Visits / Patient</div>
            <div class="kpi-value">{float(kpis['avg_visits']):.2f}</div>
        </div>
    </div>

    <div class="grid">
        {cards_html}
    </div>
</body>
</html>
"""
    output_file = Path("dashboard.html").resolve()
    output_file.write_text(html, encoding="utf-8")
    print(f"Opening UI dashboard: {output_file}")
    webbrowser.open(output_file.as_uri())


if __name__ == "__main__":
    build_html()