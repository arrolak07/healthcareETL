# USING TABLEAU

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://postgres:12345@localhost:5433/healthcare_db")

EXPORT_DIR = Path("tableau_data")
EXPORT_DIR.mkdir(exist_ok=True)

df_treatments = pd.read_sql(
    """
    SELECT treatment_type, COUNT(*) AS total_treatments
    FROM fact_treatment
    GROUP BY treatment_type
    ORDER BY total_treatments DESC;
    """,
    engine,
)
df_treatments.to_csv(EXPORT_DIR / "tableau_treatments.csv", index=False)

df_monthly = pd.read_sql(
    """
    SELECT TO_CHAR(start_time, 'YYYY-MM') AS month, COUNT(*) AS total_appointments
    FROM dim_appointment
    GROUP BY TO_CHAR(start_time, 'YYYY-MM')
    ORDER BY month;
    """,
    engine,
)
df_monthly.to_csv(EXPORT_DIR / "tableau_monthly_appointments.csv", index=False)

print(f"Exported CSVs to '{EXPORT_DIR}/'!")