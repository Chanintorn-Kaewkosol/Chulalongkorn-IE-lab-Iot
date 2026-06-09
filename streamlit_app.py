import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import random

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
            value TEXT NOT NULL,
            group_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_sensor_data(value, group_id=None):
    """Save sensor data to database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_data (value, group_id) VALUES (?, ?)",
            (str(value), group_id)
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

    # Total records
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    total_records = cursor.fetchone()[0]

    # Most frequent value
    cursor.execute("""
        SELECT value, COUNT(*) as freq
        FROM sensor_data
        GROUP BY value
        ORDER BY freq DESC
        LIMIT 1
    """)
    most_freq = cursor.fetchone()

    conn.close()
    return {
        "total_records": total_records,
        "most_frequent_value": most_freq[0] if most_freq else "N/A",
        "most_frequent_count": most_freq[1] if most_freq else 0
    }

def create_bubble_chart(df):
    """Create a floating bubble chart visualization"""
    if df.empty:
        return None

    # Assign random positions for floating effect
    df['x'] = [random.uniform(0, 10) for _ in range(len(df))]
    df['y'] = [random.uniform(0, 10) for _ in range(len(df))]
    df['size'] = [random.uniform(20, 60) for _ in range(len(df))]

    # Create color mapping for different values
    unique_values = df['value'].unique()
    colors = {}
    color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                     '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B500', '#52B788']

    for idx, val in enumerate(unique_values):
        colors[val] = color_palette[idx % len(color_palette)]

    df['color'] = df['value'].map(colors)

    # Create the bubble chart
    fig = go.Figure()

    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['x']],
            y=[row['y']],
            mode='markers+text',
            marker=dict(
                size=row['size'],
                color=row['color'],
                opacity=0.7,
                line=dict(color='white', width=2)
            ),
            text=str(row['value']),
            textposition="middle center",
            textfont=dict(size=12, color='white', family='Arial Black'),
            hovertemplate=f"<b>Value:</b> {row['value']}<br>" +
                         f"<b>Group ID:</b> {row['group_id']}<br>" +
                         f"<b>Timestamp:</b> {row['timestamp']}<br>" +
                         "<extra></extra>",
            showlegend=False
        ))

    fig.update_layout(
        title="Real-time Data Visualization",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=600,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig

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
    group_id = query_params.get("group_id", None)

    # Save to database
    if save_sensor_data(sensor_value, group_id):
        group_display = f"group '{group_id}'" if group_id else "no group (None)"
        st.success(f"✅ Data received and saved: {sensor_value} from {group_display}")
        st.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Clear the query params to avoid re-saving on refresh
    st.query_params.clear()

# Display dashboard
st.markdown("---")

# Statistics section
st.header("📊 Statistics")
try:
    stats = get_statistics()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Records", stats["total_records"])
    with col2:
        if stats["most_frequent_value"] != "N/A":
            st.metric(
                "Most Frequent Value",
                stats["most_frequent_value"],
                delta=f"{stats['most_frequent_count']} occurrences"
            )
        else:
            st.metric("Most Frequent Value", "N/A")
except Exception as e:
    st.warning("No data available yet")

st.markdown("---")

# Bubble chart visualization
st.header("🔵 Real-time Data Nodes")

# Number of records to display
num_records = st.slider("Number of records to display", 10, 100, 50)

try:
    df = get_all_data(limit=num_records)

    if not df.empty:
        # Create and display bubble chart
        fig = create_bubble_chart(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Display data table
        st.subheader("📋 Data Table")
        st.dataframe(df, use_container_width=True)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data recorded yet. Send data via GET request!")

except Exception as e:
    st.error(f"Error loading data: {e}")

# Instructions section
st.markdown("---")
st.header("🔌 How to Send Data")

st.markdown("""
### Send a GET request to:

```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_DATA>
```

### Optional: Include group ID
```
https://chulalongkorn-lab-iot.streamlit.app/?value=<YOUR_DATA>&group_id=<GROUP_NAME>
```

### Examples:
- `?value=temperature_high&group_id=room1`
- `?value=25.5&group_id=sensor_a`
- `?value=active`
""")

# Refresh button
st.markdown("---")
if st.button("🔄 Refresh Dashboard"):
    st.rerun()
