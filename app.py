import sqlite3
from flask import Flask, render_template, jsonify
from database import DB_PATH, init_db

app = Flask(__name__)
init_db()

def get_dashboard_data():
    if not DB_PATH.exists():
        return {"summary": None, "readings": [], "controllers": []}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    summary_row = conn.execute(
        "SELECT * FROM experiment_summary ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not summary_row:
        conn.close()
        return {"summary": None, "readings": [], "controllers": []}
    summary = dict(summary_row)
    run_id = summary["run_id"]
    readings = [dict(r) for r in conn.execute("""
        SELECT cycle, node_id, moisture, latency_ms
        FROM readings WHERE run_id=? ORDER BY cycle, node_id
    """, (run_id,)).fetchall()]
    controllers = [dict(r) for r in conn.execute("""
        SELECT cycle, node_id, moisture, fixed_pump, threshold_pump,
               fixed_water, threshold_water
        FROM controller_results WHERE run_id=? ORDER BY cycle, node_id
    """, (run_id,)).fetchall()]
    conn.close()
    return {"summary": summary, "readings": readings, "controllers": controllers}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    return jsonify(get_dashboard_data())

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
