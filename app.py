
import csv
import sqlite3
from pathlib import Path
from flask import Flask, render_template, jsonify
from database import DB_PATH, init_db

app = Flask(__name__)
init_db()

ROOT = Path(__file__).parent


def read_csv(filename):
    path = ROOT / filename
    if not path.exists():
        path = ROOT / "results" / filename

    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def to_number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (ValueError, AttributeError):
        return value


def get_dashboard_data():
    summary = None
    readings = []
    controllers = []
    experiments = []

    # First, try the deployed SQLite database.
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            summary_row = conn.execute(
                "SELECT * FROM experiment_summary ORDER BY id DESC LIMIT 1"
            ).fetchone()

            if summary_row:
                summary = dict(summary_row)
                run_id = summary["run_id"]

                readings = [
                    dict(row) for row in conn.execute(
                        """
                        SELECT cycle, node_id, zone_id, moisture, latency_ms,
                               sequence_no, checksum_valid, retry_count
                        FROM readings
                        WHERE run_id=?
                        ORDER BY cycle, node_id
                        """,
                        (run_id,),
                    ).fetchall()
                ]

                controllers = [
                    dict(row) for row in conn.execute(
                        """
                        SELECT cycle, node_id, zone_id, moisture, fixed_pump,
                               threshold_pump, fixed_water, threshold_water
                        FROM controller_results
                        WHERE run_id=?
                        ORDER BY cycle, node_id
                        """,
                        (run_id,),
                    ).fetchall()
                ]

                experiments = [
                    dict(row) for row in conn.execute(
                        """
                        SELECT experiment_type, parameter_value,
                               packet_delivery_ratio, average_latency_ms,
                               throughput_msg_sec, transmissions_per_packet,
                               crop_stress_percent
                        FROM network_experiments
                        WHERE run_id=?
                        ORDER BY experiment_type, parameter_value
                        """,
                        (run_id,),
                    ).fetchall()
                ]

    # Use exported CSV data when the deployed database has no usable data.
    if not summary:
        summaries = read_csv("experiment_summary.csv")
        if summaries:
            summary = {
                key: to_number(value)
                for key, value in summaries[-1].items()
            }

    if not readings:
        readings = [
            {key: to_number(value) for key, value in row.items()}
            for row in read_csv("readings.csv")
        ]

    if not controllers:
        controllers = [
            {key: to_number(value) for key, value in row.items()}
            for row in read_csv("controller_results.csv")
        ]

    if not experiments:
        experiment_rows = read_csv("network_experiments.csv")
        if experiment_rows:
            latest_run_id = experiment_rows[-1].get("run_id")
            selected_rows = [
                row for row in experiment_rows
                if row.get("run_id") == latest_run_id
            ]

            experiments = [
                {
                    key: to_number(value)
                    for key, value in row.items()
                    if key != "run_id"
                }
                for row in selected_rows
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
    app.run(host="127.0.0.1", port=5000, debug=False)
