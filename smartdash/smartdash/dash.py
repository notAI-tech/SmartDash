# Importing required libraries
import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

SERVER_URL = os.getenv("SERVER_URL")
if not SERVER_URL:
    print("--server_url is must of --dash")
    exit()

# Function to fetch logs data
def fetch_logs(app_name, last_n_hours):
    logs_data = requests.get(
        f"{SERVER_URL}logs?app_name={app_name}&last_n_hours={last_n_hours}"
    ).json()
    # Convert timestamp to datetime format
    for log in logs_data:
        log["timestamp"] = datetime.fromtimestamp(log["timestamp"])
    return logs_data


# Function to fetch logs data
def fetch_ml_inputs_outputs(app_name, last_n_hours):
    logs_data = requests.get(
        f"{SERVER_URL}ml_inputs_outputs?app_name={app_name}&last_n_hours={last_n_hours}"
    ).json()
    # Convert timestamp to datetime format
    for log in logs_data:
        log["timestamp"] = datetime.fromtimestamp(log["timestamp"])
    return logs_data


# Function to fetch timers data
def fetch_timers(app_name, last_n_hours):
    timers_data = requests.get(
        f"{SERVER_URL}timers?app_name={app_name}&last_n_hours={last_n_hours}"
    ).json()
    return timers_data


# Function to group timers data by u_id
def group_timers(timers_data):
    grouped_timers = {}
    for timer in timers_data:
        u_id = timer["u_id"]
        if u_id not in grouped_timers:
            grouped_timers[u_id] = []
        grouped_timers[u_id].append(timer)
    return grouped_timers


# Function to categorize timers data
def categorize_timers(grouped_timers):
    categories = {
        "finished_no_failed": 0,
        "finished_failed": 0,
        "not_finished_no_failed": 0,
        "not_finished_failed": 0,
    }
    for u_id, timers in grouped_timers.items():
        finished = any(timer["stage"] == "finished" for timer in timers)
        failed = any(timer["failed"] == 1 for timer in timers)

        if finished and not failed:
            categories["finished_no_failed"] += 1
        elif finished and failed:
            categories["finished_failed"] += 1
        elif not finished and not failed:
            categories["not_finished_no_failed"] += 1
        else:
            categories["not_finished_failed"] += 1
    return categories


# Function to get u_ids for finished_no_failed and finished_failed categories
def get_finished_u_ids(grouped_timers):
    finished_no_failed_u_ids = []
    finished_failed_u_ids = []
    for u_id, timers in grouped_timers.items():
        finished = any(timer["stage"] == "finished" for timer in timers)
        failed = any(timer["failed"] == 1 for timer in timers)

        if finished and not failed:
            finished_no_failed_u_ids.append(u_id)
        elif finished and failed:
            finished_failed_u_ids.append(u_id)
    return finished_no_failed_u_ids, finished_failed_u_ids


def calculate_time_per_stage(
    grouped_timers, finished_no_failed_u_ids, finished_failed_u_ids
):
    unique_stages = set()
    for timers in grouped_timers.values():
        for timer in timers:
            unique_stages.add(timer["stage"])

    time_per_stage = []
    for u_id, timers in grouped_timers.items():
        if u_id in finished_no_failed_u_ids or u_id in finished_failed_u_ids:
            stage_times = {stage: 0 for stage in unique_stages}
            stage_times["u_id"] = u_id
            stage_start_times = {}

            for timer in timers:
                stage = timer["stage"]
                timestamp = timer["timestamp"]

                if stage in stage_start_times:
                    stage_times[stage] += timestamp - stage_start_times[stage]
                    del stage_start_times[stage]
                else:
                    stage_start_times[stage] = timestamp

            time_per_stage.append(stage_times)

    return time_per_stage


# Function to calculate average and median time taken for all unique stage names from timers data
def calculate_stage_times(timers_data):
    stages = {}
    for timer in timers_data:
        stage = timer["stage"]
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(timer["timestamp"])

    stage_times = []
    for stage, timestamps in stages.items():
        timestamps.sort()
        time_diffs = [
            (timestamps[i + 1] - timestamps[i]) for i in range(len(timestamps) - 1)
        ]
        avg_time = sum(time_diffs) / len(time_diffs)
        median_time = (
            time_diffs[len(time_diffs) // 2]
            if len(time_diffs) % 2 == 1
            else (
                time_diffs[len(time_diffs) // 2 - 1] + time_diffs[len(time_diffs) // 2]
            )
            / 2
        )
        stage_times.append(
            {"stage": stage, "avg_time": avg_time, "median_time": median_time}
        )
    return stage_times


# Main function to run the Streamlit app
def main():
    st.set_page_config(page_title="SmartDash", layout="wide")  # Add layout parameter

    st.sidebar.title("SmartDash - App Dashboard")

    # Dropdowns for app_name and last_n_hours in the sidebar
    st.sidebar.markdown("## Settings")
    app_name = st.sidebar.selectbox(
        "Select App",
        requests.get("{SERVER_URL}app_names").json()["app_names"],
        index=0,
    )
    time_range = st.sidebar.selectbox(
        "Select Time Range", ["8 hours", "12 hours", "Last day", "Last week"], index=0
    )

    time_mapping = {"8 hours": 8, "12 hours": 12, "Last day": 24, "Last week": 168}
    last_n_hours = time_mapping[time_range]

    # Fetch and process timers data
    timers_data = fetch_timers(app_name, last_n_hours)
    grouped_timers = group_timers(timers_data)
    categories = categorize_timers(grouped_timers)

    # Get u_ids for finished_no_failed and finished_failed categories
    finished_no_failed_u_ids, finished_failed_u_ids = get_finished_u_ids(grouped_timers)

    # Calculate total time taken for each u_id and create a DataFrame
    time_per_stage = calculate_time_per_stage(
        grouped_timers, finished_no_failed_u_ids, finished_failed_u_ids
    )
    time_per_stage_df = pd.DataFrame(time_per_stage)

    # Create a list of graphs
    graphs = []

    # Add the pie chart for Timers Categorization to the list
    fig = px.pie(
        names=categories.keys(),
        values=categories.values(),
        title="Timers Categorization",
    )
    fig.update_traces(textinfo="percent+label")
    graphs.append(fig)

    fig = go.Figure()
    # Add the line chart for Total Time Taken per U_ID to the list
    for stage in time_per_stage_df.columns:
        if stage != "u_id":
            fig.add_trace(
                go.Scatter(
                    x=time_per_stage_df["u_id"], y=time_per_stage_df[stage], name=stage
                )
            )

    # Add a line for the total time
    # fig.add_trace(go.Scatter(x=total_times_df["u_id"], y=total_times_df["total_time"], name="Total Time"))

    fig.update_layout(
        title="Time Taken per Stage and Total Time",
        xaxis_title="U_ID",
        yaxis_title="Time",
    )
    graphs.append(fig)

    # Display the graphs in columns
    cols = st.columns(2, gap="small")
    for i, graph in enumerate(graphs):
        cols[i % 2].write(graph)

    # Make logs datatable collapsible
    with st.expander("Show/hide logs"):
        logs_data = fetch_logs(app_name, last_n_hours)
        logs_df = pd.DataFrame(logs_data)
        st.write(logs_df)

    # Make logs datatable collapsible
    with st.expander("Show/hide ML Inputs Outputs"):
        ml_io_data = fetch_ml_inputs_outputs(app_name, last_n_hours)
        ml_io_df = pd.DataFrame(ml_io_data)
        st.write(ml_io_df)


if __name__ == "__main__":
    main()
