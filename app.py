
import csv
import sqlite3
from pathlib import Path

from flask import Flask, render_template, jsonify
from database import DB_PATH, init_db

app = Flask(__name__)
init_db()

ROOT = Path(__file__).parent

SUMMARY_FIELDS = [
    "id",
    "run_id",
    "created_at",
    "nodes",
    "cycles",
    "messages_sent",
    "messages_received",
    "packet_delivery_ratio",
    "average_latency_ms",
    "throughput_msg_sec",
    "total_payload_bytes",
    "fixed_water",
    "threshold_water",
    "water_saved_percent",
    "notes",
    "zones",
    "retries",
    "corrupt_packets",
    "duplicate_packets",
    "crop_stress_percent",
    "channel_loss_percent",
]


def read_csv(filename):
    """Read a CSV file from the repository root or results folder."""
    for path in (ROOT / filename, ROOT / "results" / filename):
        if not path.exists():
            continue

        try:
            with path.open(
                "r", newline="", encoding="utf-8-sig"
            ) as file:
                reader = csv.DictReader(file, skipinitialspace=True)
                rows = list(reader)

            # Recover rows if the header was parsed as one column.
            if reader.fieldnames and len(reader.fieldnames) == 1:
                header = reader.fieldnames[0]

                if "," in header:
                    headers = next(csv.reader([header]))
                    recovered = []

                    for row in rows:
                        raw_values = row.get(None, [])

                        if not raw_values:
                            continue

                        values = []
                        first_value = row.get(header)

                        if first_value is not None:
                            values.append(first_value)

                        values.extend(raw_values)
                        recovered.append(dict(zip(headers, values)))

                    return recovered

            return rows

        except (OSError, csv.Error) as error:
            print(f"Could not read {path}: {error}")

    return []


def to_number(value):
    """Convert numeric strings to numbers, preserving other values."""
    if value is None or value == "":
        return None

    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (ValueError, TypeError, AttributeError):
        return value


def convert_rows(rows):
    """Convert values in CSV records for JSON output."""
    return [
        {key: to_number(value) for key, value in row.items()}
        for row in rows
    ]


def get_dashboard_data():
    summary = None
    readings = []
    controllers = []
    experiments = []

    # Read the most recent database run as a fallback.
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
                    db_run_id = summary.get("run_id")

                    readings = [
                        dict(row)
                        for row in conn.execute(
                            """
                            SELECT cycle, node_id, zone_id, moisture,
                                   latency_ms, sequence_no,
                                   checksum_valid, retry_count
                            FROM readings
                            WHERE run_id = ?
                            ORDER BY cycle, node_id
                            """,
                            (db_run_id,),
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
                            WHERE run_id = ?
                            ORDER BY cycle, node_id
                            """,
                            (db_run_id,),
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
                            WHERE run_id = ?
                            ORDER BY experiment_type, parameter_value
                            """,
                            (db_run_id,),
                        ).fetchall()
                    ]

        except sqlite3.Error as error:
            print("Database read error:", error)

    # Prefer the latest exported simulation summary over the DB summary.
    summary_rows = read_csv("experiment_summary.csv")

    if summary_rows:
        latest = summary_rows[-1]

        # Handle any row that still contains an unnamed list of values.
        if None in latest and isinstance(latest[None], list):
            values = latest[None]
            latest = dict(zip(SUMMARY_FIELDS, values))

        # Also handle a CSV row containing a single combined field.
        if len(latest) == 1:
            only_value = next(iter(latest.values()))

            if isinstance(only_value, str) and "," in only_value:
                values = next(csv.reader([only_value]))
                latest = dict(zip(SUMMARY_FIELDS, values))

        summary = {
            key: to_number(value)
            for key, value in latest.items()
        }

        latest_run_id = summary.get("run_id")

        def load_run_csv(filename):
            rows = read_csv(filename)

            if latest_run_id and rows and "run_id" in rows[0]:
                rows = [
                    row for row in rows
                    if row.get("run_id") == latest_run_id
                ]

            return convert_rows(rows)

        csv_readings = load_run_csv("readings.csv")
        csv_controllers = load_run_csv("controller_results.csv")

        if csv_readings:
            readings = csv_readings

        if csv_controllers:
            controllers = csv_controllers

        # Load experiments for the same simulation run.
        experiment_rows = read_csv("network_experiments.csv")

        if latest_run_id and experiment_rows:
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

    # Fallbacks if an exported file is missing or empty.
    if not readings:
        readings = convert_rows(read_csv("readings.csv"))

    if not controllers:
        controllers = convert_rows(
            read_csv("controller_results.csv")
        )

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
        debug=False,
    )
