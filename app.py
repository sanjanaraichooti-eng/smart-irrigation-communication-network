
import csv
from pathlib import Path
import sqlite3
from flask import Flask, render_template, jsonify
from database import DB_PATH, init_db

app = Flask(__name__)
init_db()


def get_dashboard_data():
    if not DB_PATH.exists():
        return {
            "summary": None,
            "readings": [],
            "controllers": [],
            "experiments": [],
        }

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        summary_row = conn.execute(
            "SELECT * FROM experiment_summary ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not summary_row:
            return {
                "summary": None,
                "readings": [],
                "controllers": [],
                "experiments": [],
            }

        summary = dict(summary_row)
        run_id = summary["run_id"]

        readings = [
            dict(row)
            for row in conn.execute(
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
            dict(row)
            for row in conn.execute(
                """
                SELECT cycle, node_id, moisture, fixed_pump,
                       threshold_pump, fixed_water, threshold_water
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

    # ADDED: Load experiment results from CSV if the database has none.
    if not experiments:
        csv_path = Path(__file__).parent / "results" / "network_experiments.csv"

        if csv_path.exists():
            with csv_path.open("r", newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

            if rows:
                latest_run_id = rows[-1]["run_id"]
                experiments = [
                    {
                        "experiment_type": row["experiment_type"],
                        "parameter_value": float(row["parameter_value"]),
                        "packet_delivery_ratio": float(row["packet_delivery_ratio"]),
                        "average_latency_ms": float(row["average_latency_ms"]),
                        "throughput_msg_sec": float(row["throughput_msg_sec"]),
                        "transmissions_per_packet": float(row["transmissions_per_packet"]),
                        "crop_stress_percent": float(row["crop_stress_percent"]),
                    }
                    for row in rows
                    if row["run_id"] == latest_run_id
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
