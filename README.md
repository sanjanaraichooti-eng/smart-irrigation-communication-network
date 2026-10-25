# Smart Irrigation Communication Network (software-only)

## What this prototype includes
- Three simulated soil-moisture sensor nodes.
- Local MQTT messaging through Eclipse Mosquitto.
- Gateway subscriber and packet/latency logging.
- SQLite storage.
- Fixed-schedule vs moisture-threshold controller comparison using the same generated readings.
- Packet delivery ratio, end-to-end MQTT latency, throughput, payload-byte count, and estimated water-use comparison.
- Flask + Chart.js dashboard.
- Pandas CSV exports and Matplotlib graphs.

All sensor readings and water units are simulated. The experiment intentionally omits a configurable fraction of packets before publishing to demonstrate packet loss. Latency is measured from publish timestamp to local gateway receipt and includes local software/broker effects; it is not a wide-area network measurement.

## 1. Install Python and VS Code
Install Python 3.11 or 3.12 and VS Code with the Python extension.

## 2. Open this folder in VS Code
Open Terminal > New Terminal. Run:
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If `python` is not recognized, try `py` in the first command and check your Python installation.

## 3. Install and start Mosquitto
Install Eclipse Mosquitto from https://mosquitto.org/download/.
The default broker port is 1883. Start the Mosquitto service from Windows Services if the installer registered it. Otherwise, open a separate terminal and run (path may differ):
```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -v
```
Keep that terminal open while running the simulation. If Mosquitto is installed elsewhere, use its actual path.

## 4. Run the experiment
In the VS Code terminal, with `.venv` activated:
```powershell
python run_simulation.py
```
You should see messages sent/received, packet delivery ratio, average MQTT latency, throughput, water units and estimated water savings. It creates `irrigation.db`.

## 5. Start the dashboard
Open another VS Code terminal, activate the environment again, and run:
```powershell
.venv\Scripts\activate
python app.py
```
Open http://127.0.0.1:5000 in your browser. The dashboard refreshes every 5 seconds.

## 6. Generate plots and CSV files
Stop neither the broker nor the dashboard. In another terminal:
```powershell
.venv\Scripts\activate
python evaluation.py
```
Open the `results` folder for PNG graphs and CSV files.

## 7. Useful adjustments
Edit `config.py`:
- `NUM_NODES`: number of simulated nodes.
- `NUM_CYCLES`: simulation cycles.
- `MOISTURE_THRESHOLD`: threshold for pump activation.
- `FIXED_SCHEDULE_EVERY`: fixed schedule interval.
- `SIMULATED_PACKET_LOSS`: application-level packet omission rate.

Run the simulation again after changing settings. The dashboard shows the latest run.

## Notes
- SQLite database records are retained between runs.
- This is a classroom/research simulation, not a real pump controller.
- The fixed-schedule and threshold controllers use the same moisture reading per node/cycle. The simple water model counts a fixed amount per pump-on event; replace it with calibrated flow and duration if you later have real hardware.
- Throughput is received messages divided by experiment elapsed time, including a short wait for MQTT messages.
- Payload bytes count generated JSON payloads, not MQTT protocol headers or total wire traffic.
