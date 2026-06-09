import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os
import time
import hashlib

# Database setup
DB_NAME = "iot_db.db"

# Admin credentials from Streamlit secrets (secure)
# Set this in Streamlit Cloud: Settings > Secrets
# Format in secrets.toml:
# admin_password = "your_secure_password_here"
try:
    ADMIN_PASSWORD = st.secrets["admin_password"]
except:
    # Fallback for local development - NEVER commit real passwords!
    ADMIN_PASSWORD = "CHANGE_ME_IN_STREAMLIT_SECRETS"

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

def delete_record(record_id):
    """Delete a specific record by ID"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_data WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def update_record(record_id, value, group_id):
    """Update a specific record"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE sensor_data SET value = ?, group_id = ? WHERE id = ?",
                      (value, group_id, record_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def add_record(value, group_id):
    """Manually add a new record"""
    return save_sensor_data(value, group_id)

def check_admin_password(password):
    """Check if the provided password matches admin password"""
    return password == ADMIN_PASSWORD

def hex_to_hsl(hex_color):
    """Convert hex color to HSL"""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2

    if max_c == min_c:
        h = s = 0
    else:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)

        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6

    return h * 360, s * 100, l * 100

def hsl_to_hex(h, s, l):
    """Convert HSL to hex color"""
    h, s, l = h / 360, s / 100, l / 100

    if s == 0:
        r = g = b = l
    else:
        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p

        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)

    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

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
                "centralGravity": 0.001,
                "springLength": 100,
                "springConstant": 0.08,
                "damping": 0.2,
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
                "size": 36,
                "color": "white",
                "bold": {
                    "color": "white"
                }
            }
        }
    }
    """)

    # Rainbow color palette (7 colors) for groups
    rainbow_colors = [
        '#FF0000',  # Red
        '#FF7F00',  # Orange
        '#FFFF00',  # Yellow
        '#00FF00',  # Green
        '#0000FF',  # Blue
        '#4B0082',  # Indigo
        '#9400D3'   # Violet
    ]

    # Get unique group_ids and create color mapping
    group_ids = [g for g in df['group_id'].unique() if g is not None]
    group_colors = {}

    for idx, group_id in enumerate(group_ids):
        # Assign rainbow color cycling through if more than 7 groups
        group_colors[group_id] = rainbow_colors[idx % len(rainbow_colors)]

    # Add group nodes (hexagons) with rainbow colors
    for group_id in group_ids:
        group_node_id = f"group_{group_id}"
        count = len(df[df['group_id'] == group_id])
        group_color = group_colors[group_id]

        net.add_node(
            group_node_id,
            label=str(group_id),
            shape='hexagon',
            color=group_color,
            size=30,  # Larger box size
            title=f"Group: {group_id}<br>Records: {count}",
            mass=2,  # Heavier mass for group nodes
            font={'color': 'white', 'size': 16, 'face': 'Arial'}
        )

    # Add data nodes (circles) with color variations based on group
    node_counter = {}  # Track nodes per group for variation
    for idx, row in df.iterrows():
        node_id = f"data_{row['id']}"
        value_display = str(row['value'])

        # Determine node color
        if row['group_id'] is not None and row['group_id'] in group_colors:
            # Get base color from group
            base_color = group_colors[row['group_id']]
            h, s, l = hex_to_hsl(base_color)

            # Create variation by adjusting lightness and saturation
            # Track how many nodes we've seen in this group
            if row['group_id'] not in node_counter:
                node_counter[row['group_id']] = 0
            node_counter[row['group_id']] += 1

            # Vary lightness between 40% and 80%
            # Vary saturation between 60% and 100%
            variation = (node_counter[row['group_id']] * 37) % 100  # pseudo-random variation
            new_l = 40 + (variation % 40)
            new_s = 60 + (variation % 40)

            node_color = hsl_to_hex(h, new_s, new_l)
        else:
            # Nodes without group get a gray color
            node_color = '#95A5A6'

        # Add data node
        net.add_node(
            node_id,
            label=value_display,
            shape='dot',
            color=node_color,
            size=30,
            title=f"ID: {row['id']}<br>Value: {row['value']}<br>Group: {row['group_id']}<br>Time: {row['timestamp']}",
            mass=1  # Lighter mass for data nodes
        )

        # Add edge connecting data node to group node
        if row['group_id'] is not None:
            group_node_id = f"group_{row['group_id']}"
            net.add_edge(
                node_id,
                group_node_id,
                color='rgba(150, 150, 150, 0.5)',
                width=10
            )

    return net

# Initialize database
init_database()

# Initialize session state
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

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

# Admin Panel Access
if "admin" in query_params:
    st.markdown("---")
    st.header("🔐 Admin Panel")

    if not st.session_state.admin_logged_in:
        # Login form
        password = st.text_input("Enter Admin Password", type="password", key="admin_password")
        if st.button("Login"):
            if check_admin_password(password):
                st.session_state.admin_logged_in = True
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid password!")
    else:
        # Admin is logged in
        st.success("✅ Admin Access Granted")

        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("---")

        # Admin tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 View All Data", "➕ Add Record", "✏️ Edit Record", "🗑️ Delete"])

        with tab1:
            st.subheader("All Records")
            all_data = get_all_data(limit=1000)
            if not all_data.empty:
                st.dataframe(all_data, use_container_width=True)

                csv = all_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download Full Database as CSV",
                    data=csv,
                    file_name=f"full_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No data available")

        with tab2:
            st.subheader("Add New Record")
            new_value = st.text_input("Value")
            new_group_id = st.text_input("Group ID (leave empty for None)")

            if st.button("➕ Add Record"):
                if new_value:
                    group = new_group_id if new_group_id else None
                    if add_record(new_value, group):
                        st.success(f"✅ Record added: {new_value} (Group: {group})")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Please enter a value")

        with tab3:
            st.subheader("Edit Record")
            all_data = get_all_data(limit=1000)
            if not all_data.empty:
                record_id = st.selectbox("Select Record ID", all_data['id'].tolist())
                selected_record = all_data[all_data['id'] == record_id].iloc[0]

                st.info(f"Current: ID={selected_record['id']}, Value={selected_record['value']}, Group={selected_record['group_id']}")

                edit_value = st.text_input("New Value", value=str(selected_record['value']))
                edit_group_id = st.text_input("New Group ID", value=str(selected_record['group_id']) if selected_record['group_id'] else "")

                if st.button("💾 Update Record"):
                    group = edit_group_id if edit_group_id else None
                    if update_record(record_id, edit_value, group):
                        st.success(f"✅ Record {record_id} updated!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("No data available")

        with tab4:
            st.subheader("Delete Records")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("#### Delete Single Record")
                all_data = get_all_data(limit=1000)
                if not all_data.empty:
                    delete_id = st.selectbox("Select Record ID to Delete", all_data['id'].tolist())
                    selected = all_data[all_data['id'] == delete_id].iloc[0]
                    st.warning(f"⚠️ You are about to delete: ID={selected['id']}, Value={selected['value']}, Group={selected['group_id']}")

                    if st.button("🗑️ Delete This Record"):
                        if delete_record(delete_id):
                            st.success(f"✅ Record {delete_id} deleted!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("No data available")

            with col_b:
                st.markdown("#### Clear All Data")
                st.warning("⚠️ **DANGER ZONE**: This will delete ALL records from the database!")
                confirm_text = st.text_input("Type 'DELETE ALL' to confirm")

                if st.button("🗑️ Clear All Data", type="primary"):
                    if confirm_text == "DELETE ALL":
                        if clear_all_data():
                            st.success("✅ All data cleared!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("❌ Please type 'DELETE ALL' to confirm")

        st.markdown("---")
        st.info("💡 To exit admin panel, remove ?admin from the URL")

        # Stop here - don't show the public dashboard
        st.stop()

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
- `?value=Hello&group_id=Group_1`
- `?value=25.5&group_id=Group_2`
- `?value=1234`
""")

# Refresh button
st.markdown("---")
if st.button("🔄 Refresh Dashboard"):
    st.rerun()
