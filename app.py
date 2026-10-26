
import csv
import sqlite3
from pathlib import Path
from flask import Flask, render_template, jsonify
from database import DB_PATH, init_db

app = Flask(__name__)
init_db()

ROOT = Path(__file__).parent


def read_csv(filename):
    """Read a CSV from the repository root or results folder."""
    paths = [
        ROOT / filename,
        ROOT / "results" / filename,
    ]

    for path in paths:
        if path.exists():
            try:
                with path.open("r", newline="", encoding="utf-8-sig") as file:
                    return list(csv.DictReader(file))
            except (OSError, csv.Error):
                continue

    return []


def to_number(value):
    """Convert numeric CSV values while preserving text."""
    if value is None or value == "":
        return None

    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (ValueError, TypeError, AttributeError):
        return value


def convert_rows(rows):
    """Convert CSV dictionaries into dashboard-ready values."""
    return [
        {key: to_number(value) for key, value in row.items()}
        for row in rows
    ]


def get_dashboard_data():
    summary = None
    readings = []
    controllers = []
    experiments = []

    # Load the latest database run first.
    if DB_PATH.exists():
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row

                summary_row = conn.execute(
                    """
                    SELECT *
                    FROM experiment_summary
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()

                if summary_row:
                    summary = dict(summary_row)
                    run_id = summary.get("run_id")

                    readings = [
                        dict(row)
                        for row in conn.execute(
                            """
                            SELECT cycle, node_id, zone_id, moisture,
                                   latency_ms, sequence_no,
                                   checksum_valid, retry_count
                            FROM readings
                            WHERE run_id=?
                            ORDER BY cycle, node_id
                            """,
                            (run_id,),
                        ).fetchall()
                    ]

                    controllers = [
                        dict(row)
                        for row in conn.execute(
                            """
                            SELECT cycle, node_id, zone_id, moisture,
                                   fixed_pump, threshold_pump,
                                   fixed_water, threshold_water
                            FROM controller_results
                            WHERE run_id=?
                            ORDER BY cycle, node_id
                            """,
                            (run_id,),
                        ).fetchall()
                    ]

                    experiments = [
                        dict(row)
                        for row in conn.execute(
                            """
                            SELECT experiment_type, parameter_value,
                                   packet_delivery_ratio,
                                   average_latency_ms,
                                   throughput_msg_sec,
                                   transmissions_per_packet,
                                   crop_stress_percent
                            FROM network_experiments
                            WHERE run_id=?
                            ORDER BY experiment_type, parameter_value
                            """,
                            (run_id,),
                        ).fetchall()
                    ]

        except sqlite3.Error as error:
            print("Database read error:", error)

    # Prefer the latest exported summary over an older database summary.
    summary_rows = read_csv("experiment_summary.csv")

    if summary_rows:
        latest = summary_rows[-1]
        latest_run_id = latest.get("run_id")

        summary = {
            key: to_number(value)
            for key, value in latest.items()
        }

        # Load rows belonging to the same run when run_id is available.
        def load_run_csv(filename):
            rows = read_csv(filename)

            if not rows:
                return []

            if latest_run_id and "run_id" in rows[0]:
                rows = [
                    row for row in rows
                    if row.get("run_id") == latest_run_id
                ]

            return convert_rows(rows)

        csv_readings = load_run_csv("readings.csv")
        csv_controllers = load_run_csv("controller_results.csv")

        # Use CSV data if it exists; otherwise retain database data.
        if csv_readings:
            readings = csv_readings

        if csv_controllers:
            controllers = csv_controllers

        # Load matching network experiment records.
        experiment_rows = read_csv("network_experiments.csv")

        if experiment_rows:
            if latest_run_id and "run_id" in experiment_rows[0]:
                matching_experiments = [
                    row for row in experiment_rows
                    if row.get("run_id") == latest_run_id
                ]
            else:
                matching_experiments = experiment_rows

            if matching_experiments:
                experiments = [
                    {
                        key: to_number(value)
                        for key, value in row.items()
                        if key != "run_id"
                    }
                    for row in matching_experiments
                ]

    # If the summary CSV is unavailable, try CSV fallbacks for other data.
    if not readings:
        readings = convert_rows(read_csv("readings.csv"))

    if not controllers:
        controllers = convert_rows(read_csv("controller_results.csv"))

    if not experiments:
        experiment_rows = read_csv("network_experiments.csv")

        if experiment_rows:
            latest_run_id = experiment_rows[-1].get("run_id")

            if latest_run_id:
                experiment_rows = [
                    row for row in experiment_rows
                    if row.get("run_id") == latest_run_id
                ]

            experiments = [
                {
                    key: to_number(value)
                    for key, value in row.items()
                    if key != "run_id"
                }
                for row in experiment_rows
            ]

    return {
        "summary": summary,
        "readings": readings,
        "controllers": controllers,
        "experiments": experiments,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify(get_dashboard_data())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
