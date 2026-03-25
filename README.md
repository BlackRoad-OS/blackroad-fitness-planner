<!-- BlackRoad SEO Enhanced -->

# ulackroad fitness planner

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad OS](https://img.shields.io/badge/Org-BlackRoad-OS-2979ff?style=for-the-badge)](https://github.com/BlackRoad-OS)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**ulackroad fitness planner** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---


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
