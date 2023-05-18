import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Dummy function to fetch data for the datatable
def get_data():
    data = {
        'unique_id': np.random.randint(1000, 9999, 10),
        'log_time': pd.date_range(start='2021-01-01', periods=10, freq='D'),
        'message': [f"message_{i}" for i in range(10)],
        'tags': [f"tag_{np.random.choice(range(1, 4), 2)}" for _ in range(10)],
    }
    return pd.DataFrame(data)

# Dummy function to fetch data for the pie chart
def get_tags_count():
    return {'tag_1': 100, 'tag_2': 150}

# Dummy function to fetch data for the bar chart
def get_names_time():
    return {'name': 100, 'name_2': 50}

st.set_page_config(layout="wide")

# App title
st.title("SmartDash")

# Data table
st.subheader("Data Table")
data = get_data()
st.dataframe(data, use_container_width=True)

# Set up columns for the graphs
col1, col2 = st.columns(2)

# Pie chart
col1.subheader("Pie Chart")
tags_count = get_tags_count()
fig, ax = plt.subplots()
ax.pie(tags_count.values(), labels=tags_count.keys(), autopct='%1.1f%%')
col1.pyplot(fig)

# Bar chart
col2.subheader("Bar Chart")
names_time = get_names_time()
fig, ax = plt.subplots()
ax.bar(names_time.keys(), names_time.values())
ax.set_ylabel('Time in seconds')
col2.pyplot(fig)