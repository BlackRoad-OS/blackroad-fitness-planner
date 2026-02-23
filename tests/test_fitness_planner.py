"""Tests for BlackRoad Health & Fitness Monitor."""
import os, tempfile, pytest
os.environ["HOME"] = tempfile.mkdtemp()  # isolate DB

from fitness_planner import (
    log_metric, get_metrics, upsert_profile, get_profile,
    calculate_bmi, get_summary, detect_anomaly, correlate,
    export_report, MetricType,
)

def test_log_and_retrieve():
    m = log_metric("test_user", MetricType.HEART_RATE, 75, "bpm")
    assert m.id > 0
    assert m.type == MetricType.HEART_RATE
    assert m.value == 75

def test_upsert_and_get_profile():
    p = upsert_profile("test_user", age=30, height_cm=175, weight_kg=70)
    assert p.user_id == "test_user"
    assert p.bmi == pytest.approx(22.86, abs=0.1)
    assert p.bmi_category == "Normal"

def test_calculate_bmi():
    upsert_profile("bmi_user", age=25, height_cm=170, weight_kg=80)
    result = calculate_bmi("bmi_user")
    assert "bmi" in result
    assert result["bmi"] > 0

def test_summary_empty():
    s = get_summary("nobody", days=1)
    assert s["metrics"] == {}

def test_summary_with_data():
    for v in [60, 70, 80, 90]:
        log_metric("s_user", MetricType.STEPS, v * 100)
    s = get_summary("s_user", days=1)
    assert "steps" in s["metrics"]
    assert s["metrics"]["steps"]["count"] >= 4

def test_detect_anomaly_no_data():
    r = detect_anomaly("nobody", MetricType.GLUCOSE)
    assert r["count"] == 0

def test_detect_anomaly_with_outlier():
    for v in [70, 72, 71, 73, 70, 69, 71]:
        log_metric("anom_user", MetricType.GLUCOSE, v)
    log_metric("anom_user", MetricType.GLUCOSE, 400)  # outlier
    r = detect_anomaly("anom_user", MetricType.GLUCOSE, days=1)
    assert r["count"] >= 1

def test_export_report_json():
    upsert_profile("rep_user", age=40, height_cm=180, weight_kg=85)
    log_metric("rep_user", MetricType.HEART_RATE, 72)
    report = export_report("rep_user", "json", days=1)
    import json
    data = json.loads(report)
    assert data["user_id"] == "rep_user"

def test_export_report_csv():
    log_metric("csv_user", MetricType.STEPS, 8000)
    report = export_report("csv_user", "csv", days=1)
    assert "metric" in report

def test_correlate_insufficient_data():
    r = correlate("nobody", MetricType.STEPS, MetricType.HEART_RATE, days=7)
    assert r["interpretation"] == "insufficient_data"

def test_metric_types_valid():
    for mt in MetricType:
        m = log_metric("mt_user", mt.value, 42.0)
        assert m.type == mt.value
