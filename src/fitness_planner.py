#!/usr/bin/env python3
"""
BlackRoad Health & Fitness Monitor
Production-grade health metrics tracking with anomaly detection and reporting.

Usage:
    python fitness_planner.py log --user alice --type heart_rate --value 72 --unit bpm
    python fitness_planner.py summary --user alice --days 7
    python fitness_planner.py bmi --user alice
    python fitness_planner.py anomaly --user alice --type heart_rate
    python fitness_planner.py correlate --user alice --m1 steps --m2 heart_rate
    python fitness_planner.py report --user alice --format json
    python fitness_planner.py profile --user alice --age 30 --height 170 --weight 70
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH = Path.home() / ".blackroad" / "fitness_planner.db"


# ── Enums ──────────────────────────────────────────────────────────────────────

class MetricType(str, Enum):
    HEART_RATE     = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    STEPS          = "steps"
    SLEEP          = "sleep"
    CALORIES       = "calories"
    WEIGHT         = "weight"
    GLUCOSE        = "glucose"
    OXYGEN_SAT     = "oxygen_sat"
    TEMPERATURE    = "temperature"
    HRV            = "hrv"


# Normal ranges: (low_warn, low_normal, high_normal, high_warn)
NORMAL_RANGES: Dict[str, Tuple[float, float, float, float]] = {
    MetricType.HEART_RATE:     (40,  60,   100,  150),
    MetricType.STEPS:          (0,   5000, 15000, 30000),
    MetricType.SLEEP:          (4,   7,    9,    12),
    MetricType.CALORIES:       (800, 1500, 3000, 5000),
    MetricType.WEIGHT:         (30,  50,   120,  250),
    MetricType.GLUCOSE:        (50,  70,   140,  300),
    MetricType.OXYGEN_SAT:     (85,  95,   100,  100),
    MetricType.TEMPERATURE:    (35.0, 36.1, 37.2, 40.0),
    MetricType.HRV:            (10,  20,   80,   120),
}

UNITS: Dict[str, str] = {
    MetricType.HEART_RATE:     "bpm",
    MetricType.BLOOD_PRESSURE: "mmHg",
    MetricType.STEPS:          "steps",
    MetricType.SLEEP:          "hours",
    MetricType.CALORIES:       "kcal",
    MetricType.WEIGHT:         "kg",
    MetricType.GLUCOSE:        "mg/dL",
    MetricType.OXYGEN_SAT:     "%",
    MetricType.TEMPERATURE:    "°C",
    MetricType.HRV:            "ms",
}

RDA_DAILY: Dict[str, float] = {
    "steps":    10000,
    "sleep":    8.0,
    "calories": 2000,
}


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class HealthMetric:
    id:        int
    user_id:   str
    type:      str
    value:     float
    unit:      str
    timestamp: str
    device:    str
    notes:     str

    @property
    def dt(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HealthProfile:
    user_id:    str
    age:        int
    height_cm:  float
    weight_kg:  float
    conditions: List[str] = field(default_factory=list)
    goal_steps: int   = 10000
    goal_sleep: float = 8.0
    goal_cal:   int   = 2000
    created_at: str   = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str   = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def bmi(self) -> float:
        if self.height_cm <= 0:
            return 0.0
        h_m = self.height_cm / 100
        return round(self.weight_kg / (h_m ** 2), 2)

    @property
    def bmi_category(self) -> str:
        b = self.bmi
        if b < 18.5: return "Underweight"
        if b < 25.0: return "Normal"
        if b < 30.0: return "Overweight"
        return "Obese"

    @property
    def bmr(self) -> float:
        """Mifflin-St Jeor BMR (assumes male; use +/- 5% for sex adjustment)."""
        return round(10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bmi"] = self.bmi
        d["bmi_category"] = self.bmi_category
        d["bmr"] = self.bmr
        return d


# ── Database ───────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS health_metrics (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT    NOT NULL,
            type      TEXT    NOT NULL,
            value     REAL    NOT NULL,
            unit      TEXT    NOT NULL,
            timestamp TEXT    NOT NULL DEFAULT (datetime('now')),
            device    TEXT    NOT NULL DEFAULT 'manual',
            notes     TEXT    NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_hm_user_type ON health_metrics(user_id, type);
        CREATE INDEX IF NOT EXISTS idx_hm_ts        ON health_metrics(timestamp);

        CREATE TABLE IF NOT EXISTS health_profiles (
            user_id    TEXT PRIMARY KEY,
            age        INTEGER NOT NULL DEFAULT 0,
            height_cm  REAL    NOT NULL DEFAULT 0,
            weight_kg  REAL    NOT NULL DEFAULT 0,
            conditions TEXT    NOT NULL DEFAULT '[]',
            goal_steps INTEGER NOT NULL DEFAULT 10000,
            goal_sleep REAL    NOT NULL DEFAULT 8.0,
            goal_cal   INTEGER NOT NULL DEFAULT 2000,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


# ── Core API ───────────────────────────────────────────────────────────────────

def log_metric(
    user_id: str,
    metric_type: str,
    value: float,
    unit: str = "",
    device: str = "manual",
    notes: str = "",
) -> HealthMetric:
    """Persist a single health metric reading."""
    if not unit:
        unit = UNITS.get(metric_type, "")
    ts = datetime.now().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO health_metrics(user_id,type,value,unit,timestamp,device,notes)"
            " VALUES(?,?,?,?,?,?,?)",
            (user_id, metric_type, value, unit, ts, device, notes),
        )
        conn.commit()
        row_id = cur.lastrowid
    return HealthMetric(row_id, user_id, metric_type, value, unit, ts, device, notes)


def get_metrics(
    user_id: str,
    metric_type: Optional[str] = None,
    days: int = 7,
) -> List[HealthMetric]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        if metric_type:
            rows = conn.execute(
                "SELECT * FROM health_metrics WHERE user_id=? AND type=?"
                " AND timestamp>=? ORDER BY timestamp",
                (user_id, metric_type, since),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_metrics WHERE user_id=?"
                " AND timestamp>=? ORDER BY timestamp",
                (user_id, since),
            ).fetchall()
    return [HealthMetric(**dict(r)) for r in rows]


def upsert_profile(
    user_id: str,
    age: int = 0,
    height_cm: float = 0.0,
    weight_kg: float = 0.0,
    conditions: Optional[List[str]] = None,
    goal_steps: int = 10000,
    goal_sleep: float = 8.0,
    goal_cal: int = 2000,
) -> HealthProfile:
    conds_json = json.dumps(conditions or [])
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO health_profiles
              (user_id,age,height_cm,weight_kg,conditions,goal_steps,goal_sleep,goal_cal,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
              age=excluded.age, height_cm=excluded.height_cm,
              weight_kg=excluded.weight_kg, conditions=excluded.conditions,
              goal_steps=excluded.goal_steps, goal_sleep=excluded.goal_sleep,
              goal_cal=excluded.goal_cal, updated_at=excluded.updated_at
        """, (user_id, age, height_cm, weight_kg, conds_json, goal_steps, goal_sleep, goal_cal, now, now))
        conn.commit()
    return get_profile(user_id)


def get_profile(user_id: str) -> Optional[HealthProfile]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM health_profiles WHERE user_id=?", (user_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["conditions"] = json.loads(d["conditions"])
    return HealthProfile(**d)


def get_summary(user_id: str, days: int = 7) -> dict:
    """Per-metric stats (mean, min, max, stddev, count) for the past N days."""
    metrics = get_metrics(user_id, days=days)
    by_type: Dict[str, List[float]] = {}
    for m in metrics:
        by_type.setdefault(m.type, []).append(m.value)

    summary: Dict[str, dict] = {}
    for mtype, vals in by_type.items():
        summary[mtype] = {
            "count":  len(vals),
            "mean":   round(statistics.mean(vals), 2),
            "min":    min(vals),
            "max":    max(vals),
            "stddev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "unit":   UNITS.get(mtype, ""),
            "latest": vals[-1],
        }
    return {"user_id": user_id, "days": days, "metrics": summary}


def calculate_bmi(user_id: str) -> dict:
    """Return BMI info from the stored profile; update weight from latest log."""
    profile = get_profile(user_id)
    if not profile:
        return {"error": f"No profile found for '{user_id}'. Run: profile --user {user_id}"}

    # Try to refresh weight from latest metric log
    w_metrics = get_metrics(user_id, MetricType.WEIGHT, days=365)
    if w_metrics:
        latest_w = w_metrics[-1].value
        profile.weight_kg = latest_w

    return {
        "user_id":      user_id,
        "weight_kg":    profile.weight_kg,
        "height_cm":    profile.height_cm,
        "age":          profile.age,
        "bmi":          profile.bmi,
        "category":     profile.bmi_category,
        "bmr_kcal":     profile.bmr,
        "ideal_weight_kg": round(22.5 * (profile.height_cm / 100) ** 2, 1),
    }


def detect_anomaly(user_id: str, metric_type: str, days: int = 30) -> dict:
    """
    Flag readings outside the normal range AND statistical outliers (> 2σ).
    Returns a list of anomalous readings with reason codes.
    """
    metrics = get_metrics(user_id, metric_type, days=days)
    if not metrics:
        return {"user_id": user_id, "type": metric_type, "anomalies": [], "count": 0}

    values = [m.value for m in metrics]
    mean   = statistics.mean(values)
    stddev = statistics.stdev(values) if len(values) > 1 else 0.0
    bounds = NORMAL_RANGES.get(metric_type)

    anomalies = []
    for m in metrics:
        reasons = []
        if bounds:
            low_warn, low_norm, high_norm, high_warn = bounds
            if m.value < low_warn:
                reasons.append("critically_low")
            elif m.value < low_norm:
                reasons.append("below_normal")
            elif m.value > high_warn:
                reasons.append("critically_high")
            elif m.value > high_norm:
                reasons.append("above_normal")
        if stddev > 0 and abs(m.value - mean) > 2 * stddev:
            reasons.append("statistical_outlier_2σ")
        if reasons:
            anomalies.append({
                "id":        m.id,
                "timestamp": m.timestamp,
                "value":     m.value,
                "unit":      m.unit,
                "reasons":   reasons,
                "z_score":   round((m.value - mean) / stddev, 2) if stddev else None,
            })

    return {
        "user_id":  user_id,
        "type":     metric_type,
        "days":     days,
        "n_total":  len(metrics),
        "mean":     round(mean, 2),
        "stddev":   round(stddev, 2),
        "anomalies": anomalies,
        "count":    len(anomalies),
    }


def correlate(
    user_id: str,
    metric1: str,
    metric2: str,
    days: int = 30,
) -> dict:
    """
    Pearson correlation between two metrics sampled over the same day buckets.
    Returns r, r², interpretation, and per-day data.
    """
    since = datetime.now() - timedelta(days=days)

    def daily_avg(mtype: str) -> Dict[str, float]:
        metrics = get_metrics(user_id, mtype, days=days)
        buckets: Dict[str, List[float]] = {}
        for m in metrics:
            day = m.timestamp[:10]
            buckets.setdefault(day, []).append(m.value)
        return {d: statistics.mean(vs) for d, vs in buckets.items()}

    avgs1 = daily_avg(metric1)
    avgs2 = daily_avg(metric2)
    common_days = sorted(set(avgs1) & set(avgs2))

    if len(common_days) < 3:
        return {
            "user_id": user_id, "metric1": metric1, "metric2": metric2,
            "r": None, "r2": None,
            "interpretation": "insufficient_data",
            "common_days": len(common_days),
        }

    x = [avgs1[d] for d in common_days]
    y = [avgs2[d] for d in common_days]
    n  = len(x)
    mx, my = statistics.mean(x), statistics.mean(y)
    sx, sy = statistics.stdev(x), statistics.stdev(y)

    if sx == 0 or sy == 0:
        r = 0.0
    else:
        r = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / ((n - 1) * sx * sy)

    r = max(-1.0, min(1.0, r))
    ar = abs(r)
    if ar >= 0.7:   interp = "strong"
    elif ar >= 0.4: interp = "moderate"
    elif ar >= 0.2: interp = "weak"
    else:           interp = "negligible"
    direction = "positive" if r > 0 else "negative"

    return {
        "user_id":        user_id,
        "metric1":        metric1,
        "metric2":        metric2,
        "days":           days,
        "common_days":    len(common_days),
        "pearson_r":      round(r, 4),
        "r_squared":      round(r ** 2, 4),
        "interpretation": f"{interp} {direction} correlation",
        "data":           [{"date": d, metric1: avgs1[d], metric2: avgs2[d]} for d in common_days],
    }


def export_report(user_id: str, fmt: str = "json", days: int = 30) -> str:
    """Generate a health report in JSON or CSV format."""
    profile = get_profile(user_id)
    summary = get_summary(user_id, days=days)
    bmi_info = calculate_bmi(user_id) if profile else {}
    anomalies = {
        mt: detect_anomaly(user_id, mt, days=days)
        for mt in [MetricType.HEART_RATE, MetricType.GLUCOSE, MetricType.OXYGEN_SAT]
    }

    report = {
        "generated_at":  datetime.now().isoformat(),
        "user_id":       user_id,
        "period_days":   days,
        "profile":       profile.to_dict() if profile else None,
        "bmi":           bmi_info,
        "summary":       summary["metrics"],
        "anomaly_flags": {k: v["count"] for k, v in anomalies.items()},
        "anomaly_detail": anomalies,
    }

    if fmt == "csv":
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(["metric", "count", "mean", "min", "max", "stddev", "unit", "latest"])
        for mtype, stats in summary["metrics"].items():
            writer.writerow([
                mtype, stats["count"], stats["mean"], stats["min"],
                stats["max"], stats["stddev"], stats["unit"], stats["latest"],
            ])
        return out.getvalue()

    return json.dumps(report, indent=2)


# ── CLI ────────────────────────────────────────────────────────────────────────

def _print(obj):
    if isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="BlackRoad Health & Fitness Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # log
    p = sub.add_parser("log", help="Record a health metric")
    p.add_argument("--user",   required=True)
    p.add_argument("--type",   required=True, choices=[m.value for m in MetricType])
    p.add_argument("--value",  type=float, required=True)
    p.add_argument("--unit",   default="")
    p.add_argument("--device", default="manual")
    p.add_argument("--notes",  default="")

    # summary
    p = sub.add_parser("summary", help="7-day summary stats")
    p.add_argument("--user", required=True)
    p.add_argument("--days", type=int, default=7)

    # bmi
    p = sub.add_parser("bmi", help="Calculate BMI from profile")
    p.add_argument("--user", required=True)

    # anomaly
    p = sub.add_parser("anomaly", help="Detect anomalous readings")
    p.add_argument("--user", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--days", type=int, default=30)

    # correlate
    p = sub.add_parser("correlate", help="Pearson correlation between two metrics")
    p.add_argument("--user", required=True)
    p.add_argument("--m1",   required=True, dest="metric1")
    p.add_argument("--m2",   required=True, dest="metric2")
    p.add_argument("--days", type=int, default=30)

    # report
    p = sub.add_parser("report", help="Full health report export")
    p.add_argument("--user",   required=True)
    p.add_argument("--format", choices=["json", "csv"], default="json", dest="fmt")
    p.add_argument("--days",   type=int, default=30)

    # profile
    p = sub.add_parser("profile", help="Set user health profile")
    p.add_argument("--user",       required=True)
    p.add_argument("--age",        type=int,   default=0)
    p.add_argument("--height",     type=float, default=0.0)
    p.add_argument("--weight",     type=float, default=0.0)
    p.add_argument("--conditions", nargs="*",  default=[])
    p.add_argument("--goal-steps", type=int,   default=10000, dest="goal_steps")
    p.add_argument("--goal-sleep", type=float, default=8.0,   dest="goal_sleep")
    p.add_argument("--goal-cal",   type=int,   default=2000,  dest="goal_cal")

    args = parser.parse_args()

    if args.cmd == "log":
        m = log_metric(args.user, args.type, args.value, args.unit, args.device, args.notes)
        _print({"status": "logged", "id": m.id, "type": m.type, "value": m.value, "unit": m.unit})

    elif args.cmd == "summary":
        _print(get_summary(args.user, args.days))

    elif args.cmd == "bmi":
        _print(calculate_bmi(args.user))

    elif args.cmd == "anomaly":
        _print(detect_anomaly(args.user, args.type, args.days))

    elif args.cmd == "correlate":
        _print(correlate(args.user, args.metric1, args.metric2, args.days))

    elif args.cmd == "report":
        print(export_report(args.user, args.fmt, args.days))

    elif args.cmd == "profile":
        p = upsert_profile(
            args.user, args.age, args.height, args.weight,
            args.conditions, args.goal_steps, args.goal_sleep, args.goal_cal,
        )
        _print(p.to_dict())


if __name__ == "__main__":
    main()
