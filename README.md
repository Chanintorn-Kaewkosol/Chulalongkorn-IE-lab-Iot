# 🌡️ Chulalongkorn IoT Lab - Sensor Data Dashboard

A Streamlit web application for collecting and visualizing sensor data from RP Pico W IoT devices.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chulalongkorn-lab-iot.streamlit.app/)

## Features

- ✅ Receive sensor data via GET requests from RP Pico W
- ✅ Store data in SQLite database (`iot_db.db`)
- ✅ Real-time data visualization dashboard
- ✅ Statistics and analytics
- ✅ Export data to CSV
- ✅ Support for multiple sensors with sensor IDs

## How to Send Data from RP Pico W

Send a GET request to:
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_SENSOR_VALUE>
```

With optional sensor ID:
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_SENSOR_VALUE>&sensor_id=<SENSOR_NAME>
```

### Example MicroPython Code

```python
import network
import urequests
import time

# WiFi setup
ssid = 'YOUR_WIFI_SSID'
password = 'YOUR_WIFI_PASSWORD'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    time.sleep(1)

print('Connected to WiFi')

# Send sensor data
sensor_value = 25.5  # Your sensor reading
url = f"https://chulalongkorn-lab-iot.streamlit.app/?value={sensor_value}&sensor_id=temperature"

try:
    response = urequests.get(url)
    print(f"Status: {response.status_code}")
    response.close()
except Exception as e:
    print(f"Error: {e}")
```

## How to Run Locally

1. Install the requirements

   ```bash
   pip install -r requirements.txt
   ```

2. Run the app

   ```bash
   streamlit run streamlit_app.py
   ```

3. Open your browser to `http://localhost:8501`

## Database Schema

The SQLite database (`iot_db.db`) contains a `sensor_data` table with:

- `id`: Auto-incrementing primary key
- `timestamp`: Automatic timestamp when data is received
- `value`: Sensor value (REAL)
- `sensor_id`: Optional sensor identifier (TEXT)

## Deployment

This app is deployed on Streamlit Cloud at: https://chulalongkorn-lab-iot.streamlit.app/

To deploy your own:
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy!
