import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("irrigation.db")

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            cycle INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            moisture REAL NOT NULL,
            timestamp_sent REAL NOT NULL,
            timestamp_received REAL NOT NULL,
            latency_ms REAL NOT NULL,
            payload_bytes INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS controller_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            cycle INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            moisture REAL NOT NULL,
            fixed_pump TEXT NOT NULL,
            threshold_pump TEXT NOT NULL,
            fixed_water REAL NOT NULL,
            threshold_water REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            nodes INTEGER NOT NULL,
            cycles INTEGER NOT NULL,
            messages_sent INTEGER NOT NULL,
            messages_received INTEGER NOT NULL,
            packet_delivery_ratio REAL NOT NULL,
            average_latency_ms REAL NOT NULL,
            throughput_msg_sec REAL NOT NULL,
            total_payload_bytes INTEGER NOT NULL,
            fixed_water REAL NOT NULL,
            threshold_water REAL NOT NULL,
            water_saved_percent REAL NOT NULL,
            notes TEXT NOT NULL
        );
        """)
