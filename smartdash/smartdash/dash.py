# Importing required libraries
import streamlit as st
import pandas as pd
import requests
import os
import json
import plotly.express as px
from datetime import datetime

SERVER_URL = os.getenv("SMARTDASH_SERVER_URL")

if not SERVER_URL:
    print("--server_url is required for --dash")
    quit()


# Function to fetch data
def fetch_dash_data(app_name, last_n_hours, long_running_n_hours=1):
    data = requests.get(
        f"{SERVER_URL}/get_dash_metrics?app_name={app_name}&last_n_hours={last_n_hours}&long_running_n_hours={long_running_n_hours}"
    ).json()

    return data["data_by_uid"], data["metrics"]


def get_all_tags_levels_stages(data_by_uid):
    tags = set()
    levels = set()
    stages = set()

    for uid, data in data_by_uid.items():
        for log in data["logs"]:
            tags.update(log["tags"])
            levels.add(log["level"])
            stages.add(log["stage"])

    return sorted(tags), sorted(levels), sorted(stages)


# Main function to run the Streamlit app
def main():
    st.set_page_config(page_title="SmartDash", layout="wide")

    st.sidebar.title("SmartDash - App Dashboard")

    # Dropdowns for app_name and last_n_hours in the sidebar
    st.sidebar.markdown("## Settings")
    app_name = st.sidebar.selectbox(
        "Select App",
        requests.get(f"{SERVER_URL}/app_names").json()["app_names"],
        index=0,
    )
    time_range = st.sidebar.selectbox(
        "Select Time Range", ["8 hours", "12 hours", "Last day", "Last week"], index=0
    )

    in_process_range = st.sidebar.selectbox(
        "Highlight long running uids", ["1 hour", "15 min", "30 min"], index=0
    )

    time_mapping = {"8 hours": 8, "12 hours": 12, "Last day": 24, "Last week": 168}
    last_n_hours = time_mapping[time_range]

    data_by_uid, _ = fetch_dash_data(app_name, last_n_hours)

    all_tags, all_levels, all_stages = get_all_tags_levels_stages(data_by_uid)

    # Add filters in the sidebar
    st.sidebar.markdown("## Filter Logs")
    filter_tags = st.sidebar.multiselect("Tags", all_tags)
    filter_level = st.sidebar.selectbox("Level", ["All"] + all_levels, index=0)
    filter_stage = st.sidebar.selectbox("Stage", ["All"] + all_stages, index=0)
    filter_uid = st.sidebar.text_input("UID")

    # Calculate total time per unique ID
    total_times = {}
    for uid, data in data_by_uid.items():
        if data["logs"]:
            first_log_time = data["logs"][0]["timestamp"]
            last_log_time = data["logs"][-1]["timestamp"]
            total_times[uid] = last_log_time - first_log_time

    # Create a pie chart showing the distribution of times taken by each stage
    stage_times = {}
    for uid, data in data_by_uid.items():
        for stage, times in data["stage_wise_times"].items():
            if stage not in stage_times:
                stage_times[stage] = times["end"] - times["start"]
            else:
                stage_times[stage] += times["end"] - times["start"]

    stage_time_pie = px.pie(
        values=list(stage_times.values()),
        names=list(stage_times.keys()),
        title="Time distribution by stage",
    )

    # Create a line chart showing the time taken by each stage with unique IDs on the x-axis and time taken on the y-axis
    line_chart_data = []
    for uid, data in data_by_uid.items():
        for stage, times in data["stage_wise_times"].items():
            line_chart_data.append(
                {
                    "uid": uid,
                    "stage": stage,
                    "time_taken": times["end"] - times["start"],
                }
            )

    line_chart_df = pd.DataFrame(line_chart_data)
    stage_time_line = px.line(
        line_chart_df,
        x="uid",
        y="time_taken",
        color="stage",
        title="Time taken by each stage",
    )

    # Pie chart showing number of failed, success, and in-process uids
    metrics_pie = px.pie(
        values=[
            sum([1 for uid, data in data_by_uid.items() if data["success"]]),
            sum([1 for uid, data in data_by_uid.items() if data["in_process"]]),
            sum([1 for uid, data in data_by_uid.items() if data["failed"]]),
            sum([1 for uid, data in data_by_uid.items() if data["long_running"]]),
        ],
        names=["Success", "In Process", "Failed", "Long running"],
        title="Uids by Status",
    )

    graphs = [stage_time_pie, stage_time_line, metrics_pie]

    cols = st.columns(2, gap="small")
    for i, graph in enumerate(graphs):
        cols[i % 2].write(graph)

    with st.expander("Show/hide logs"):
        logs_data = []
        for uid, data in data_by_uid.items():
            logs_data.extend(data["logs"])
            if data["success"]:
                logs_data[-1]["status"] = "Success"
            elif data["failed"]:
                logs_data[-1]["status"] = "Failed"
            elif data["in_process"]:
                logs_data[-1]["status"] = "In Process"
            elif data["long_running"]:
                logs_data[-1]["status"] = "Long running"
            else:
                logs_data[-1]["status"] = "Unknown"

        # Convert timestamp to datetime format
        for log in logs_data:
            log["timestamp"] = datetime.fromtimestamp(log["timestamp"])

        # Apply filters
        if filter_tags:
            logs_data = [
                log for log in logs_data if set(log["tags"]) & set(filter_tags)
            ]
        if filter_level != "All":
            logs_data = [log for log in logs_data if log["level"] == filter_level]
        if filter_stage != "All":
            logs_data = [log for log in logs_data if log["stage"] == filter_stage]
        if filter_uid:
            logs_data = [log for log in logs_data if log["u_id"] == filter_uid]

        logs_df = pd.DataFrame(logs_data)
        st.dataframe(logs_df)


if __name__ == "__main__":
    main()
