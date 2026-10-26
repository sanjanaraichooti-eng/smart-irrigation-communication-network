
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
            zone_id INTEGER NOT NULL DEFAULT 1,
            moisture REAL NOT NULL,
            timestamp_sent REAL NOT NULL,
            timestamp_received REAL NOT NULL,
            latency_ms REAL NOT NULL,
            payload_bytes INTEGER NOT NULL,
            sequence_no INTEGER DEFAULT 0,
            checksum_valid INTEGER DEFAULT 1,
            retry_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS controller_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            cycle INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            zone_id INTEGER NOT NULL DEFAULT 1,
            moisture REAL NOT NULL,
            fixed_pump TEXT NOT NULL,
            threshold_pump TEXT NOT NULL,
            fixed_water REAL NOT NULL,
            threshold_water REAL NOT NULL,
            crop_stress INTEGER DEFAULT 0
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
            notes TEXT NOT NULL,
            zones INTEGER DEFAULT 2,
            retries INTEGER DEFAULT 0,
            corrupt_packets INTEGER DEFAULT 0,
            duplicate_packets INTEGER DEFAULT 0,
            crop_stress_percent REAL DEFAULT 0,
            channel_loss_percent REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS network_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            experiment_type TEXT NOT NULL,
            parameter_value REAL NOT NULL,
            packet_delivery_ratio REAL NOT NULL,
            average_latency_ms REAL NOT NULL,
            throughput_msg_sec REAL NOT NULL,
            transmissions_per_packet REAL NOT NULL,
            crop_stress_percent REAL DEFAULT 0
        );
        """)

        # Add new columns when upgrading an existing database.
        migrations = {
            "readings": {
                "zone_id": "INTEGER NOT NULL DEFAULT 1",
                "sequence_no": "INTEGER DEFAULT 0",
                "checksum_valid": "INTEGER DEFAULT 1",
                "retry_count": "INTEGER DEFAULT 0",
            },
            "controller_results": {
                "zone_id": "INTEGER NOT NULL DEFAULT 1",
                "crop_stress": "INTEGER DEFAULT 0",
            },
            "experiment_summary": {
                "zones": "INTEGER DEFAULT 2",
                "retries": "INTEGER DEFAULT 0",
                "corrupt_packets": "INTEGER DEFAULT 0",
                "duplicate_packets": "INTEGER DEFAULT 0",
                "crop_stress_percent": "REAL DEFAULT 0",
                "channel_loss_percent": "REAL DEFAULT 0",
            },
        }

        for table, columns in migrations.items():
            existing = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})")
            }
            for column, definition in columns.items():
                if column not in existing:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )
