
import sqlite3

conn = sqlite3.connect("irrigation.db")
cursor = conn.cursor()

print("DATABASE TABLES:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    print("-", table[0])

print("\nLATEST EXPERIMENT:")
cursor.execute("""
    SELECT run_id, messages_sent, messages_received,
           packet_delivery_ratio, average_latency_ms,
           throughput_msg_sec, fixed_water, threshold_water,
           water_saved_percent
    FROM experiment_summary
    ORDER BY id DESC
    LIMIT 1
""")

row = cursor.fetchone()
if row:
    labels = [
        "Run ID", "Messages sent", "Messages received",
        "Packet delivery ratio (%)", "Average latency (ms)",
        "Throughput (messages/second)", "Fixed water",
        "Threshold water", "Water saved (%)"
    ]
    for label, value in zip(labels, row):
        print(f"{label}: {value}")
else:
    print("No experiment results found.")

conn.close()
