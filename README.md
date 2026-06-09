# 🌡️ Chulalongkorn IoT Lab - Sensor Data Dashboard

A Streamlit web application for collecting and visualizing sensor data from IoT devices with real-time floating bubble visualization.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chulalongkorn-lab-iot.streamlit.app/)

## Features

- ✅ Receive sensor data via GET requests (supports string and numeric values)
- ✅ Store data in SQLite database (`iot_db.db`)
- ✅ Real-time floating bubble visualization (nodes appear as data arrives)
- ✅ Statistics: Total records & Most frequent value
- ✅ Export data to CSV
- ✅ Support for multiple groups with group IDs

## How to Send Data

Send a GET request to:
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_DATA>
```

With optional group ID:
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_DATA>&group_id=<GROUP_NAME>
```

### Examples:
- `?value=temperature_high&group_id=room1`
- `?value=25.5&group_id=sensor_a`
- `?value=active`

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
- `value`: Sensor value (TEXT - supports any string or number)
- `group_id`: Optional group identifier (TEXT)

## Visualization

Data appears as **floating bubble nodes** with:
- Random positioning for dynamic effect
- Color-coded by value
- Hover to see details (value, group_id, timestamp)
- Real-time updates when new data arrives

## Deployment

This app is deployed on Streamlit Cloud at: https://chulalongkorn-lab-iot.streamlit.app/

To deploy your own:
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy!
