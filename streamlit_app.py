import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os
import time

# Database setup
DB_NAME = "iot_db.db"

def init_database():
    """Initialize SQLite database and create table if it doesn't exist"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check if table exists and has old schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_data'")
    table_exists = cursor.fetchone()

    if table_exists:
        # Check if old column sensor_id exists
        cursor.execute("PRAGMA table_info(sensor_data)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'sensor_id' in columns and 'group_id' not in columns:
            # Migrate: rename sensor_id to group_id
            cursor.execute("ALTER TABLE sensor_data RENAME COLUMN sensor_id TO group_id")
            conn.commit()
    else:
        # Create new table with group_id
        cursor.execute("""
            CREATE TABLE sensor_data (
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

def clear_all_data():
    """Delete all records from the database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_data")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error clearing data: {e}")
        return False

def create_network_graph(df):
    """Create an interactive physics-based network graph with draggable nodes"""
    if df.empty:
        return None

    # Create a Network object with physics enabled
    net = Network(
        height='700px',
        width='100%',
        bgcolor='#f0f0f5',
        font_color='#333333',
        notebook=False
    )

    # Enable physics for spring-force simulation
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0.5
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
                "enabled": true,
                "iterations": 100
            }
        },
        "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hover": true
        },
        "nodes": {
            "font": {
                "size": 14,
                "color": "white",
                "bold": {
                    "color": "white"
                }
            }
        }
    }
    """)

    # Color palette for different values
    color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                     '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B500', '#52B788']

    # Create color mapping
    unique_values = df['value'].unique()
    colors = {}
    for idx, val in enumerate(unique_values):
        colors[val] = color_palette[idx % len(color_palette)]

    # Get unique group_ids
    group_ids = df['group_id'].unique()

    # Add group nodes (squares)
    for group_id in group_ids:
        if group_id is not None:
            group_node_id = f"group_{group_id}"
            count = len(df[df['group_id'] == group_id])

            net.add_node(
                group_node_id,
                label=str(group_id),
                shape='box',
                color='#FFFFFF',
                size=50,
                title=f"Group: {group_id}<br>Records: {count}",
                mass=5,  # Heavier mass for group nodes
                font=16
            )

    # Add data nodes (circles) and edges
    for idx, row in df.iterrows():
        node_id = f"data_{row['id']}"
        node_color = colors.get(row['value'], '#95A5A6')
        value_display = str(row['value'])[:10]  # Truncate long values

        # Add data node
        net.add_node(
            node_id,
            label=value_display,
            shape='dot',
            color=node_color,
            size=20,
            title=f"ID: {row['id']}<br>Value: {row['value']}<br>Group: {row['group_id']}<br>Time: {row['timestamp']}",
            mass=2  # Lighter mass for data nodes
        )

        # Add edge connecting data node to group node
        if row['group_id'] is not None:
            group_node_id = f"group_{row['group_id']}"
            net.add_edge(
                node_id,
                group_node_id,
                color='rgba(150, 150, 150, 0.5)',
                width=5
            )

    return net

# Initialize database
init_database()

# Initialize session state for delete confirmation
if 'delete_clicks' not in st.session_state:
    st.session_state.delete_clicks = 0
if 'last_click_time' not in st.session_state:
    st.session_state.last_click_time = 0

# Page configuration
st.set_page_config(
    page_title="Chulalongkorn IoT Lab",
    page_icon="🌡️",
    layout="wide"
)

# Auto-reload every 5 seconds
st_autorefresh = st.empty()
with st_autorefresh:
    # This creates a placeholder that will trigger rerun
    time.sleep(0.1)

# JavaScript for auto-refresh every 5 seconds
st.markdown("""
    <script>
        setTimeout(function() {
            window.parent.location.reload();
        }, 5000);
    </script>
""", unsafe_allow_html=True)

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

    col1, col2, col3 = st.columns(3)
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
    with col3:
        # Clear data button with multi-click confirmation
        current_time = time.time()

        # Reset clicks if more than 3 seconds passed since last click
        if current_time - st.session_state.last_click_time > 3:
            st.session_state.delete_clicks = 0

        clicks_remaining = 5 - st.session_state.delete_clicks

        if st.session_state.delete_clicks < 5:
            button_label = f"🗑️ Clear All Data ({clicks_remaining} clicks)"
        else:
            button_label = "🗑️ DELETING..."

        if st.button(button_label, type="primary" if st.session_state.delete_clicks >= 4 else "secondary"):
            st.session_state.delete_clicks += 1
            st.session_state.last_click_time = time.time()

            if st.session_state.delete_clicks >= 5:
                if clear_all_data():
                    st.success("✅ All data has been cleared!")
                    st.session_state.delete_clicks = 0
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning(f"⚠️ Click {5 - st.session_state.delete_clicks} more times to confirm deletion!")

        if st.session_state.delete_clicks > 0 and st.session_state.delete_clicks < 5:
            st.caption(f"Progress: {st.session_state.delete_clicks}/5 clicks")

except Exception as e:
    st.warning("No data available yet")

st.markdown("---")

# Interactive Network Graph
st.header("🔵 Interactive Network Graph")

# Number of records input (exact value)
num_records = st.number_input("Number of records to display", min_value=1, max_value=500, value=50, step=10)

try:
    df = get_all_data(limit=num_records)

    if not df.empty:
        # Create and display network graph
        net = create_network_graph(df)
        if net:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmpfile:
                net.save_graph(tmpfile.name)
                tmpfile_path = tmpfile.name

            # Read the HTML
            with open(tmpfile_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Display using Streamlit components
            components.html(html_content, height=720, scrolling=False)

            # Clean up temp file
            try:
                os.unlink(tmpfile_path)
            except:
                pass

            st.info("🎮 **Controls:** Drag nodes to move them! They'll bounce back with physics. Scroll to zoom, drag background to pan.")

        st.markdown("---")

        # Display data table (only id, timestamp, value, group_id)
        st.subheader("📋 Data Table")
        df_display = df[['id', 'timestamp', 'value', 'group_id']]
        st.dataframe(df_display, use_container_width=True)

        # Download button
        csv = df_display.to_csv(index=False)
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
