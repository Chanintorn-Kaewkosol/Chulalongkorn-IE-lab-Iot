import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Database setup
DB_NAME = "iot_db.db"

def init_database():
    """Initialize SQLite database and create table if it doesn't exist"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            value REAL NOT NULL,
            sensor_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_sensor_data(value, sensor_id=None):
    """Save sensor data to database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_data (value, sensor_id) VALUES (?, ?)",
            (float(value), sensor_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

def get_all_data(limit=100):
    """Retrieve all sensor data from database"""
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT {limit}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_statistics():
    """Get basic statistics from the database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), AVG(value), MIN(value), MAX(value) FROM sensor_data")
    stats = cursor.fetchone()
    conn.close()
    return {
        "total_records": stats[0],
        "average": stats[1],
        "minimum": stats[2],
        "maximum": stats[3]
    }

# Initialize database
init_database()

# Page configuration
st.set_page_config(
    page_title="Chulalongkorn IoT Lab",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ Chulalongkorn IoT Lab - Sensor Data Dashboard")

# Get query parameters from URL
query_params = st.query_params

# Check if data is being sent via GET request
if "value" in query_params:
    sensor_value = query_params["value"]
    sensor_id = query_params.get("sensor_id", "pico_w_default")

    # Save to database
    if save_sensor_data(sensor_value, sensor_id):
        st.success(f"✅ Data received and saved: {sensor_value} from sensor '{sensor_id}'")
        st.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Clear the query params to avoid re-saving on refresh
    st.query_params.clear()

# Display dashboard
st.markdown("---")

# Statistics section
st.header("📊 Statistics")
try:
    stats = get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", stats["total_records"])
    with col2:
        st.metric("Average Value", f"{stats['average']:.2f}" if stats['average'] else "N/A")
    with col3:
        st.metric("Minimum Value", f"{stats['minimum']:.2f}" if stats['minimum'] else "N/A")
    with col4:
        st.metric("Maximum Value", f"{stats['maximum']:.2f}" if stats['maximum'] else "N/A")
except Exception as e:
    st.warning("No data available yet")

st.markdown("---")

# Recent data section
st.header("📋 Recent Sensor Data")

# Number of records to display
num_records = st.slider("Number of records to display", 10, 500, 100)

try:
    df = get_all_data(limit=num_records)

    if not df.empty:
        # Display data table
        st.dataframe(df, use_container_width=True)

        # Plot data
        st.subheader("📈 Sensor Value Timeline")
        st.line_chart(df.set_index('timestamp')['value'])

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data recorded yet. Send data from your RP Pico W!")

except Exception as e:
    st.error(f"Error loading data: {e}")

# Instructions section
st.markdown("---")
st.header("🔌 How to Send Data")

st.markdown("""
### From your RP Pico W, send a GET request to:

```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_SENSOR_VALUE>
```

### Optional: Include sensor ID
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_SENSOR_VALUE>&sensor_id=<SENSOR_NAME>
```

### Example MicroPython code for RP Pico W:
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
""")

# Refresh button
st.markdown("---")
if st.button("🔄 Refresh Dashboard"):
    st.rerun()
