import json
import random
import time
import uuid
from datetime import datetime

import paho.mqtt.client as mqtt

from config import (
    BROKER_HOST, BROKER_PORT, MQTT_TOPIC, NUM_NODES, NUM_CYCLES,
    MOISTURE_THRESHOLD, FIXED_SCHEDULE_EVERY, WATER_PER_EVENT,
    SIMULATED_PACKET_LOSS
)
from database import init_db, connect

received_packets = []
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(MQTT_TOPIC, qos=1)
    else:
        print("MQTT connection failed:", reason_code)

def on_message(client, userdata, msg):
    received_at = time.time()
    try:
        packet = json.loads(msg.payload.decode("utf-8"))
        packet["timestamp_received"] = received_at
        received_packets.append(packet)
    except (ValueError, UnicodeDecodeError):
        print("Ignored invalid MQTT packet.")

def main():
    init_db()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:5]
    received_packets.clear()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="smart-irrigation-" + uuid.uuid4().hex[:6],
        protocol=mqtt.MQTTv311
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
        client.loop_start()
        time.sleep(1.0)  # allow subscriber connection to complete
    except Exception as exc:
        print("\nCould not connect to Mosquitto.")
        print("Make sure the Mosquitto broker is running on 127.0.0.1:1883.")
        print("Details:", exc)
        return

    rng = random.Random(2026)  # repeatable experiment
    moisture = [48.0, 57.0, 42.0]
    sent = 0
    payload_bytes = 0
    started = time.perf_counter()

    # Each generated reading is evaluated by both controllers using the same moisture value.
    for cycle in range(1, NUM_CYCLES + 1):
        for node_index in range(NUM_NODES):
            moisture[node_index] = max(
                10.0, min(90.0, moisture[node_index] - rng.uniform(1.0, 5.0))
            )
            value = round(moisture[node_index], 2)
            sent += 1
            timestamp_sent = time.time()
            packet = {
                "run_id": run_id,
                "cycle": cycle,
                "node_id": node_index + 1,
                "moisture": value,
                "timestamp_sent": timestamp_sent
            }
            encoded = json.dumps(packet, separators=(",", ":")).encode("utf-8")
            payload_bytes += len(encoded)

            # Intentionally omit a small percentage of generated packets to model loss.
            if rng.random() >= SIMULATED_PACKET_LOSS:
                info = client.publish(MQTT_TOPIC, encoded, qos=1)
                info.wait_for_publish(timeout=3)

            # Same reading, same cycle: compare fixed schedule and threshold controller.
            fixed_on = (cycle % FIXED_SCHEDULE_EVERY == 0)
            threshold_on = (value < MOISTURE_THRESHOLD)
            fixed_water = WATER_PER_EVENT if fixed_on else 0.0
            threshold_water = WATER_PER_EVENT if threshold_on else 0.0

            with connect() as conn:
                conn.execute("""
                    INSERT INTO controller_results
                    (run_id, cycle, node_id, moisture, fixed_pump, threshold_pump,
                     fixed_water, threshold_water)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, cycle, node_index + 1, value,
                    "ON" if fixed_on else "OFF",
                    "ON" if threshold_on else "OFF",
                    fixed_water, threshold_water
                ))
        time.sleep(0.02)

    time.sleep(1.0)  # allow queued MQTT messages to arrive
    elapsed = max(time.perf_counter() - started, 0.001)
    client.loop_stop()
    client.disconnect()

    # Keep only packets received for this run; deduplicate by cycle/node.
    run_packets = [p for p in received_packets if p.get("run_id") == run_id]
    seen = set()
    unique_packets = []
    for packet in run_packets:
        key = (packet["cycle"], packet["node_id"])
        if key not in seen:
            seen.add(key)
            unique_packets.append(packet)

    with connect() as conn:
        for packet in unique_packets:
            latency = max(0.0, (packet["timestamp_received"] - packet["timestamp_sent"]) * 1000)
            conn.execute("""
                INSERT INTO readings
                (run_id, cycle, node_id, moisture, timestamp_sent,
                 timestamp_received, latency_ms, payload_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, packet["cycle"], packet["node_id"], packet["moisture"],
                packet["timestamp_sent"], packet["timestamp_received"],
                latency, len(json.dumps(packet, separators=(",", ":")).encode("utf-8"))
            ))

        with connect() as unused:
            pass

        fixed_total = conn.execute(
            "SELECT COALESCE(SUM(fixed_water), 0) FROM controller_results WHERE run_id=?",
            (run_id,)
        ).fetchone()[0]
        threshold_total = conn.execute(
            "SELECT COALESCE(SUM(threshold_water), 0) FROM controller_results WHERE run_id=?",
            (run_id,)
        ).fetchone()[0]

        received = len(unique_packets)
        pdr = (received / sent * 100.0) if sent else 0.0
        avg_latency = (
            sum(max(0.0, (p["timestamp_received"] - p["timestamp_sent"]) * 1000)
                for p in unique_packets) / received
        ) if received else 0.0
        throughput = received / elapsed
        water_saved = ((fixed_total - threshold_total) / fixed_total * 100.0) if fixed_total else 0.0

        conn.execute("""
            INSERT INTO experiment_summary
            (run_id, created_at, nodes, cycles, messages_sent, messages_received,
             packet_delivery_ratio, average_latency_ms, throughput_msg_sec,
             total_payload_bytes, fixed_water, threshold_water, water_saved_percent, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, datetime.now().isoformat(timespec="seconds"),
            NUM_NODES, NUM_CYCLES, sent, received, pdr, avg_latency,
            throughput, payload_bytes, fixed_total, threshold_total, water_saved,
            "Local Mosquitto MQTT; 5% application-level packet omission; water is in simulated units."
        ))

    print("\nExperiment complete!")
    print("Run ID:", run_id)
    print(f"Generated messages: {sent}")
    print(f"Messages received by gateway: {received}")
    print(f"Packet delivery ratio: {pdr:.2f}%")
    print(f"Average MQTT end-to-end latency: {avg_latency:.3f} ms")
    print(f"Throughput: {throughput:.2f} messages/second")
    print(f"Payload bytes generated: {payload_bytes}")
    print(f"Fixed-schedule water units: {fixed_total:.1f}")
    print(f"Threshold-based water units: {threshold_total:.1f}")
    print(f"Estimated water saved: {water_saved:.2f}%")
    print("\nOpen the dashboard at http://127.0.0.1:5000")
    print("Run the dashboard separately with: python app.py")

if __name__ == "__main__":
    main()
