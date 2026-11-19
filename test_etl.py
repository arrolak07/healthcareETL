import pandas as pd
import numpy as np
from etl_pipeline import calculate_duration, remove_duplicates


def test_visit_duration_computation():
    start = pd.to_datetime(pd.Series(["2026-05-01 09:00:00", "2026-05-01 14:15:00"]))
    end = pd.to_datetime(pd.Series(["2026-05-01 09:45:00", "2026-05-01 15:15:00"]))
    durations = calculate_duration(start, end)
    assert list(durations) == [45.0, 60.0]


def test_patient_duplicates_detection():
    df = pd.DataFrame({
        "patient_id": [101, 101, 102, 103, 103],
        "patient_name": ["John Doe", "John Doe", "Jane Smith", "Bob Lee", "Bob Lee"]
    })
    deduped = remove_duplicates(df, "patient_id")
    assert len(deduped) == 3
    assert list(deduped["patient_id"]) == [101, 102, 103]


def test_treatment_cost_aggregation():
    df = pd.DataFrame({
        "patient_id": [1, 1, 2],
        "cost": [250.50, 149.50, 500.00]
    })
    totals = df.groupby("patient_id")["cost"].sum().to_dict()
    assert totals[1] == 400.00
    assert totals[2] == 500.00