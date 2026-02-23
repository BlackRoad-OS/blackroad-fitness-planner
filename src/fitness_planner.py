#!/usr/bin/env python3
"""BlackRoad Fitness Planner — workout planning and progress tracking."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import List, Optional

# ── ANSI Colors ───────────────────────────────────────────────────────────────
GREEN   = "\033[0;32m"
RED     = "\033[0;31m"
YELLOW  = "\033[1;33m"
CYAN    = "\033[0;36m"
BLUE    = "\033[0;34m"
MAGENTA = "\033[0;35m"
BOLD    = "\033[1m"
NC      = "\033[0m"

DB_PATH = Path.home() / ".blackroad" / "fitness-planner.db"


class MuscleGroup(str, Enum):
    CHEST     = "chest"
    BACK      = "back"
    SHOULDERS = "shoulders"
    ARMS      = "arms"
    CORE      = "core"
    LEGS      = "legs"
    CARDIO    = "cardio"
    FULL_BODY = "full_body"


class Difficulty(str, Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"


class WorkoutStatus(str, Enum):
    PLANNED   = "planned"
    COMPLETED = "completed"
    SKIPPED   = "skipped"


@dataclass
class Exercise:
    """A named exercise with default parameters."""

    name:          str
    muscle_group:  MuscleGroup = MuscleGroup.FULL_BODY
    difficulty:    Difficulty  = Difficulty.INTERMEDIATE
    default_sets:  int         = 3
    default_reps:  int         = 10
    rest_seconds:  int         = 60
    calories_per_set: float    = 20.0
    notes:         str         = ""
    created_at:    str         = field(default_factory=lambda: datetime.now().isoformat())
    id:            Optional[int] = None

    def muscle_color(self) -> str:
        return {MuscleGroup.CHEST: CYAN, MuscleGroup.BACK: BLUE,
                MuscleGroup.SHOULDERS: YELLOW, MuscleGroup.ARMS: GREEN,
                MuscleGroup.CORE: MAGENTA, MuscleGroup.LEGS: RED,
                MuscleGroup.CARDIO: YELLOW, MuscleGroup.FULL_BODY: CYAN}.get(self.muscle_group, NC)


@dataclass
class WorkoutSet:
    """Actual performance data for one exercise within a session."""

    exercise_id:  int
    exercise_name: str = ""
    sets_done:    int   = 0
    reps_done:    int   = 0
    weight_kg:    float = 0.0
    duration_min: float = 0.0


@dataclass
class WorkoutSession:
    """A logged workout session."""

    session_date:    str            = field(default_factory=lambda: date.today().isoformat())
    status:          WorkoutStatus  = WorkoutStatus.PLANNED
    exercises:       List[dict]     = field(default_factory=list)   # serialized WorkoutSets
    total_duration:  float          = 0.0
    total_calories:  float          = 0.0
    mood:            int            = 5    # 1-10 scale
    notes:           str            = ""
    created_at:      str            = field(default_factory=lambda: datetime.now().isoformat())
    updated_at:      str            = field(default_factory=lambda: datetime.now().isoformat())
    id:              Optional[int]  = None

    def status_color(self) -> str:
        return {WorkoutStatus.COMPLETED: GREEN,
                WorkoutStatus.SKIPPED:   RED,
                WorkoutStatus.PLANNED:   YELLOW}.get(self.status, NC)


class FitnessPlanner:
    """SQLite-backed fitness planning and tracking engine."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    name              TEXT    UNIQUE NOT NULL,
                    muscle_group      TEXT    DEFAULT 'full_body',
                    difficulty        TEXT    DEFAULT 'intermediate',
                    default_sets      INTEGER DEFAULT 3,
                    default_reps      INTEGER DEFAULT 10,
                    rest_seconds      INTEGER DEFAULT 60,
                    calories_per_set  REAL    DEFAULT 20.0,
                    notes             TEXT    DEFAULT '',
                    created_at        TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workout_sessions (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date     TEXT    NOT NULL,
                    status           TEXT    DEFAULT 'planned',
                    exercises        TEXT    DEFAULT '[]',
                    total_duration   REAL    DEFAULT 0.0,
                    total_calories   REAL    DEFAULT 0.0,
                    mood             INTEGER DEFAULT 5,
                    notes            TEXT    DEFAULT '',
                    created_at       TEXT    NOT NULL,
                    updated_at       TEXT    NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_date ON workout_sessions(session_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ex_muscle    ON exercises(muscle_group)")
            conn.commit()

    def _row_to_exercise(self, row: sqlite3.Row) -> Exercise:
        return Exercise(id=row["id"], name=row["name"],
                        muscle_group=MuscleGroup(row["muscle_group"]),
                        difficulty=Difficulty(row["difficulty"]),
                        default_sets=row["default_sets"], default_reps=row["default_reps"],
                        rest_seconds=row["rest_seconds"], calories_per_set=row["calories_per_set"],
                        notes=row["notes"] or "", created_at=row["created_at"])

    def _row_to_session(self, row: sqlite3.Row) -> WorkoutSession:
        return WorkoutSession(id=row["id"], session_date=row["session_date"],
                              status=WorkoutStatus(row["status"]),
                              exercises=json.loads(row["exercises"] or "[]"),
                              total_duration=row["total_duration"],
                              total_calories=row["total_calories"],
                              mood=row["mood"], notes=row["notes"] or "",
                              created_at=row["created_at"], updated_at=row["updated_at"])

    def add_exercise(self, name: str, muscle_group: str = "full_body",
                     difficulty: str = "intermediate", default_sets: int = 3,
                     default_reps: int = 10, rest_seconds: int = 60,
                     calories_per_set: float = 20.0, notes: str = "") -> Exercise:
        """Register a new exercise in the library."""
        ex = Exercise(name=name, muscle_group=MuscleGroup(muscle_group),
                      difficulty=Difficulty(difficulty), default_sets=default_sets,
                      default_reps=default_reps, rest_seconds=rest_seconds,
                      calories_per_set=calories_per_set, notes=notes)
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO exercises (name,muscle_group,difficulty,default_sets,default_reps,"
                "rest_seconds,calories_per_set,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (ex.name, ex.muscle_group.value, ex.difficulty.value, ex.default_sets,
                 ex.default_reps, ex.rest_seconds, ex.calories_per_set, ex.notes, ex.created_at),
            )
            conn.commit()
            ex.id = cur.lastrowid
        return ex

    def list_exercises(self, muscle_group: Optional[str] = None) -> List[Exercise]:
        sql = "SELECT * FROM exercises WHERE 1=1"
        params: list = []
        if muscle_group:
            sql += " AND muscle_group=?"; params.append(muscle_group)
        sql += " ORDER BY name"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_exercise(r) for r in rows]

    def log_workout(self, session_date: Optional[str] = None, exercise_ids: Optional[List[int]] = None,
                    total_duration: float = 0.0, mood: int = 5, notes: str = "") -> WorkoutSession:
        """Log a completed workout session."""
        session_date = session_date or date.today().isoformat()
        exercise_ids = exercise_ids or []
        exercises_data: list = []
        total_calories = 0.0
        if exercise_ids:
            with self._conn() as conn:
                for eid in exercise_ids:
                    row = conn.execute("SELECT * FROM exercises WHERE id=?", (eid,)).fetchone()
                    if row:
                        ex = self._row_to_exercise(row)
                        cal = ex.calories_per_set * ex.default_sets
                        total_calories += cal
                        exercises_data.append({"id": ex.id, "name": ex.name,
                                               "sets": ex.default_sets, "reps": ex.default_reps,
                                               "calories": cal})
        now = datetime.now().isoformat()
        session = WorkoutSession(session_date=session_date, status=WorkoutStatus.COMPLETED,
                                 exercises=exercises_data, total_duration=total_duration,
                                 total_calories=total_calories, mood=mood, notes=notes,
                                 created_at=now, updated_at=now)
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO workout_sessions (session_date,status,exercises,total_duration,"
                "total_calories,mood,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (session.session_date, session.status.value, json.dumps(session.exercises),
                 session.total_duration, session.total_calories, session.mood,
                 session.notes, session.created_at, session.updated_at),
            )
            conn.commit()
            session.id = cur.lastrowid
        return session

    def list_sessions(self, limit: int = 20) -> List[WorkoutSession]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workout_sessions ORDER BY session_date DESC LIMIT ?",
                (limit,)).fetchall()
        return [self._row_to_session(r) for r in rows]

    def export_json(self, path: str) -> int:
        sessions = self.list_sessions(limit=10_000)
        records  = [asdict(s) | {"status": s.status.value} for s in sessions]
        with open(path, "w") as fh:
            json.dump(records, fh, indent=2, default=str)
        return len(records)

    def stats(self) -> dict:
        sessions   = self.list_sessions(limit=10_000)
        completed  = [s for s in sessions if s.status == WorkoutStatus.COMPLETED]
        avg_mood   = sum(s.mood for s in completed) / len(completed) if completed else 0.0
        total_cal  = sum(s.total_calories for s in completed)
        total_dur  = sum(s.total_duration for s in completed)
        exercises  = self.list_exercises()
        return {"total_sessions": len(sessions), "completed": len(completed),
                "total_calories_burned": round(total_cal, 1),
                "total_duration_min": round(total_dur, 1),
                "avg_mood": round(avg_mood, 1), "exercises_in_library": len(exercises)}


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace, planner: FitnessPlanner) -> None:
    if args.target == "exercises":
        items = planner.list_exercises(muscle_group=args.muscle_group)
        if not items:
            print(f"{YELLOW}No exercises found.{NC}"); return
        print(f"\n{BOLD}{BLUE}── Exercise Library ({len(items)}) {'─'*35}{NC}")
        for ex in items:
            mc = ex.muscle_color()
            print(f"  {BOLD}#{ex.id:<4}{NC} {mc}{ex.muscle_group.value:<12}{NC} "
                  f"{CYAN}{ex.difficulty.value:<14}{NC} {ex.name}")
            print(f"            {ex.default_sets}x{ex.default_reps}  "
                  f"rest:{ex.rest_seconds}s  ~{ex.calories_per_set:.0f}cal/set")
    else:
        sessions = planner.list_sessions(limit=args.limit)
        if not sessions:
            print(f"{YELLOW}No workout sessions found.{NC}"); return
        print(f"\n{BOLD}{BLUE}── Workout Sessions ({len(sessions)}) {'─'*34}{NC}")
        for s in sessions:
            sc = s.status_color()
            ex_names = ", ".join(e["name"] for e in s.exercises[:3])
            if len(s.exercises) > 3:
                ex_names += f" +{len(s.exercises)-3} more"
            print(f"  {BOLD}{s.session_date}{NC}  {sc}{s.status.value:<12}{NC} "
                  f"mood:{s.mood}/10  {s.total_calories:.0f}cal  {s.total_duration:.0f}min")
            if ex_names:
                print(f"            {ex_names}")
    print()


def cmd_add(args: argparse.Namespace, planner: FitnessPlanner) -> None:
    ex = planner.add_exercise(args.name, muscle_group=args.muscle_group,
                              difficulty=args.difficulty, default_sets=args.sets,
                              default_reps=args.reps, rest_seconds=args.rest,
                              calories_per_set=args.calories, notes=args.notes)
    print(f"{GREEN}✓ Exercise added: #{ex.id} {ex.name} ({ex.muscle_group.value}){NC}")


def cmd_log(args: argparse.Namespace, planner: FitnessPlanner) -> None:
    ids = [int(x.strip()) for x in args.exercises.split(",")] if args.exercises else []
    s   = planner.log_workout(session_date=args.date, exercise_ids=ids,
                               total_duration=args.duration, mood=args.mood, notes=args.notes)
    print(f"{GREEN}✓ Workout logged: session #{s.id} on {s.session_date}{NC}")
    print(f"  Exercises: {len(s.exercises)}  Calories: {s.total_calories:.0f}  "
          f"Duration: {s.total_duration:.0f}min  Mood: {s.mood}/10")


def cmd_status(args: argparse.Namespace, planner: FitnessPlanner) -> None:
    s = planner.stats()
    print(f"\n{BOLD}{BLUE}── Fitness Planner Status {'─'*35}{NC}")
    print(f"  Sessions logged  : {BOLD}{s['total_sessions']}{NC}  "
          f"(completed: {GREEN}{s['completed']}{NC})")
    print(f"  Total calories   : {BOLD}{s['total_calories_burned']:.1f} kcal{NC}")
    print(f"  Total duration   : {BOLD}{s['total_duration_min']:.1f} min{NC}")
    print(f"  Average mood     : {BOLD}{s['avg_mood']:.1f}/10{NC}")
    print(f"  Exercise library : {BOLD}{s['exercises_in_library']}{NC} exercises")
    print()


def cmd_export(args: argparse.Namespace, planner: FitnessPlanner) -> None:
    n = planner.export_json(args.output)
    print(f"{GREEN}✓ Exported {n} sessions → {args.output}{NC}")


def build_parser() -> argparse.ArgumentParser:
    p   = argparse.ArgumentParser(description="BlackRoad Fitness Planner")
    sub = p.add_subparsers(dest="command", required=True)

    ls = sub.add_parser("list", help="List exercises or sessions")
    ls.add_argument("target", choices=["exercises", "sessions"], default="sessions", nargs="?")
    ls.add_argument("--muscle-group", dest="muscle_group", metavar="GROUP")
    ls.add_argument("--limit", type=int, default=20)

    add = sub.add_parser("add", help="Add an exercise to the library")
    add.add_argument("name")
    add.add_argument("--muscle-group", dest="muscle_group", default="full_body",
                     choices=[x.value for x in MuscleGroup])
    add.add_argument("--difficulty", default="intermediate",
                     choices=[x.value for x in Difficulty])
    add.add_argument("--sets",     type=int,   default=3)
    add.add_argument("--reps",     type=int,   default=10)
    add.add_argument("--rest",     type=int,   default=60, metavar="SECONDS")
    add.add_argument("--calories", type=float, default=20.0, metavar="PER_SET")
    add.add_argument("--notes",    default="")

    lg = sub.add_parser("log", help="Log a completed workout")
    lg.add_argument("--date",      default=None, metavar="YYYY-MM-DD")
    lg.add_argument("--exercises", metavar="IDS",  help="Comma-separated exercise IDs")
    lg.add_argument("--duration",  type=float, default=0.0, metavar="MINUTES")
    lg.add_argument("--mood",      type=int,   default=5, choices=range(1, 11), metavar="1-10")
    lg.add_argument("--notes",     default="")

    sub.add_parser("status", help="Show progress statistics")

    ex = sub.add_parser("export", help="Export sessions to JSON")
    ex.add_argument("--output", "-o", default="fitness_export.json")

    return p


def main() -> None:
    parser  = build_parser()
    args    = parser.parse_args()
    planner = FitnessPlanner()
    {"list": cmd_list, "add": cmd_add, "log": cmd_log,
     "status": cmd_status, "export": cmd_export}[args.command](args, planner)


if __name__ == "__main__":
    main()
