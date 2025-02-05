import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime

def create_connection():
    secrets = st.secrets["mysql"]
    return pymysql.connect(
        host=secrets["host"],
        user=secrets["username"],
        password=secrets["password"],
        database=secrets["database"],
        port=secrets["port"]
    )

# Query data
def run_query(query):
    conn = create_connection()
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()
    return df

# Streamlit UI
st.title("Flights Data Viewer")

# Date filters
st.sidebar.header("Filter by Date")
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2023, 12, 31))

# Validate date range
if start_date > end_date:
    st.error("Error: Start date must be earlier than end date.")
else:
    # Format dates for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Query with date filter
    query = f"""
        SELECT * FROM flights 
        WHERE tanggal_dummy BETWEEN '{start_date_str}' AND '{end_date_str}';
    """

    # Run query
    df = run_query(query)

    # Display results
    if not df.empty:
        st.write(f"Displaying flights from {start_date_str} to {end_date_str}:")
        st.dataframe(df)
    else:
        st.write(f"No flights found between {start_date_str} and {end_date_str}.")