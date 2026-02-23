# BlackRoad Fitness Planner

[![CI](https://github.com/BlackRoad-OS/blackroad-fitness-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-OS/blackroad-fitness-planner/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)](LICENSE)
[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-black.svg)](https://blackroad.io)

> Health metrics monitoring: BMI, anomaly detection, Pearson correlation, export

Part of the **BlackRoad OS** health & science platform — production-grade implementations with SQLite persistence, pytest coverage, and CI/CD.

## Features

- **HealthMetric** dataclass: heart rate, blood pressure, steps, sleep, calories, weight, glucose, O₂ sat, temperature, HRV
- **HealthProfile** with BMI (Mifflin-St Jeor BMR), categorization, and goals
- `log_metric(user_id, type, value)` — persist a reading to SQLite
- `get_summary(user_id, days=7)` — per-metric mean/min/max/stddev
- `calculate_bmi(user_id)` — BMI, category, BMR, ideal weight
- `detect_anomaly(user_id, type)` — normal-range flags + 2σ statistical outliers
- `correlate(user_id, m1, m2, days=30)` — Pearson r with interpretation
- `export_report(user_id, format)` — JSON or CSV health report

## Quick Start

```bash
python src/fitness_planner.py profile --user alice --age 30 --height 170 --weight 68
python src/fitness_planner.py log --user alice --type heart_rate --value 72 --unit bpm
python src/fitness_planner.py summary --user alice --days 7
python src/fitness_planner.py bmi --user alice
python src/fitness_planner.py anomaly --user alice --type glucose --days 30
python src/fitness_planner.py correlate --user alice --m1 steps --m2 heart_rate
python src/fitness_planner.py report --user alice --format json
```

## Metric Types

| Metric | Unit | Normal Range |
|--------|------|-------------|
| heart_rate | bpm | 60–100 |
| blood_pressure | mmHg | systolic 90–140 |
| steps | steps | 5,000–15,000/day |
| sleep | hours | 7–9 |
| calories | kcal | 1,500–3,000 |
| weight | kg | varies |
| glucose | mg/dL | 70–140 |
| oxygen_sat | % | 95–100 |

## Installation

```bash
# No dependencies required — pure Python stdlib + sqlite3
python src/fitness_planner.py --help
```

## Testing

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=src
```

## Data Storage

All data is stored locally in `~/.blackroad/fitness-planner.db` (SQLite). Zero external dependencies.

## License

Proprietary — © BlackRoad OS, Inc. All rights reserved.
