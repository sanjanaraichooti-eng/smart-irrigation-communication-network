import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from database import DB_PATH
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

def generate_graphs():
    if not DB_PATH.exists():
        print("No database yet. Run python run_simulation.py first.")
        return
    conn = sqlite3.connect(DB_PATH)
    summary = pd.read_sql_query(
        "SELECT * FROM experiment_summary ORDER BY id DESC LIMIT 1", conn
    )
    results = pd.read_sql_query(
        "SELECT * FROM controller_results WHERE run_id=? ORDER BY cycle, node_id",
        conn, params=(summary.iloc[0]["run_id"],)
    ) if not summary.empty else pd.DataFrame()
    conn.close()

    if summary.empty or results.empty:
        print("No experiment results found. Run the simulation first.")
        return

    s = summary.iloc[0]
    labels = ["Fixed schedule", "Threshold-based"]
    water = [s["fixed_water"], s["threshold_water"]]
    plt.figure(figsize=(7, 4))
    plt.bar(labels, water)
    plt.ylabel("Simulated water units")
    plt.title("Water-use comparison")
    plt.tight_layout()
    plt.savefig(RESULTS / "water_comparison.png", dpi=150)
    plt.close()

    avg = results.groupby("cycle")["moisture"].mean()
    plt.figure(figsize=(8, 4))
    plt.plot(avg.index, avg.values, marker="o", markersize=3)
    plt.axhline(30, linestyle="--", label="Moisture threshold (30%)")
    plt.xlabel("Simulation cycle")
    plt.ylabel("Average soil moisture (%)")
    plt.title("Average simulated soil moisture")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS / "moisture_trend.png", dpi=150)
    plt.close()

    metrics = ["packet_delivery_ratio", "average_latency_ms", "throughput_msg_sec"]
    metric_labels = ["Packet delivery ratio (%)", "Average latency (ms)", "Throughput (msg/s)"]
    vals = [s[m] for m in metrics]
    plt.figure(figsize=(8, 4))
    plt.bar(metric_labels, vals)
    plt.title("Network performance metrics (different units)")
    plt.xticks(rotation=12, ha="right")
    plt.tight_layout()
    plt.savefig(RESULTS / "network_metrics.png", dpi=150)
    plt.close()

    results.to_csv(RESULTS / "controller_results.csv", index=False)
    summary.to_csv(RESULTS / "experiment_summary.csv", index=False)
    print("Graphs and CSV files saved in the results folder.")

if __name__ == "__main__":
    generate_graphs()
