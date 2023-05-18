import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px

# Function to fetch logs data
def fetch_logs(app_name, last_n_hours):
    response = requests.get(f"http://localhost:6788/logs?app_name={app_name}&last_n_hours={last_n_hours}")
    logs_data = json.loads(response.text)
    return logs_data

# Function to fetch timers data
def fetch_timers(app_name, last_n_hours):
    response = requests.get(f"http://localhost:6788/timers?app_name={app_name}&last_n_hours={last_n_hours}")
    timers_data = json.loads(response.text)
    return timers_data

# Function to display logs data in a table format
def display_logs_data(logs_data):
    df = pd.DataFrame(logs_data)
    df['messages'] = df['messages'].apply(lambda x: ' '.join(x))
    st.write(df)

# Function to display timers data in a bar graph
def display_timers_data(timers_data):
    df = pd.DataFrame(timers_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    df = df.sort_values(by=['u_id', 'timestamp'])
    df['duration'] = df.groupby('u_id')['timestamp'].diff().dt.total_seconds().fillna(0)
    df['status'] = df['stage'].apply(lambda x: 'finished' if x == 'finished' else 'not finished')
    df.loc[df['stage'].str.contains("__fail__"), 'status'] = 'failed'
    
    u_ids = df['u_id'].unique()
    total_time = []
    for u_id in u_ids:
        u_id_df = df[df['u_id'] == u_id]
        start_time = u_id_df['timestamp'].iloc[0]
        end_time = u_id_df['timestamp'].iloc[-1]
        status = u_id_df['status'].iloc[-1]
        total_time.append({
            'u_id': u_id,
            'total_time': (end_time - start_time).total_seconds(),
            'status': status
        })
    
    total_time_df = pd.DataFrame(total_time)
    
    fig = px.line(total_time_df, x='u_id', y='total_time', color='status', title='Timers Data',
                  color_discrete_map={'finished': 'green', 'not finished': 'yellow', 'failed': 'red'},
                  markers=True)
    st.plotly_chart(fig)

# App title
st.title("SmartDash")

# Dropdown for time range selection
time_range_label = st.selectbox("Select time range", ["8 hours", "12 hours", "24 hrs", "7 days", "one month"], index=0)

# Time range mapping
time_range_mapping = {
    "8 hours": 8,
    "12 hours": 12,
    "24 hrs": 24,
    "7 days": 7 * 24,
    "one month": 30 * 24,
}

# Get the actual time range in hours
time_range = time_range_mapping[time_range_label]

# Dropdown for app name selection
app_name = st.selectbox("Select app name", ["analytics"], index=0)



# Fetch and display logs data
logs_data = fetch_logs(app_name, time_range)
st.subheader("Logs Data")
display_logs_data(logs_data)

# Fetch and display timers data
timers_data = fetch_timers(app_name, time_range)
st.subheader("Timers Data")
display_timers_data(timers_data)