import streamlit as st
import pymysql
import pandas as pd
import folium
from streamlit_folium import folium_static
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

# Bandara Jawa Timur dan koordinatnya
airports = {
    "WARR": {"name": "Surabaya", "coords": [-7.3798, 112.7873]},
    "WARW": {"name": "Bawean", "coords": [-5.8674, 112.5908]},
    "WARD": {"name": "Blora", "coords": [-6.9694, 111.4238]},
    "WART": {"name": "Kediri", "coords": [-7.8162, 112.0123]},
    "WADY": {"name": "Sumenep", "coords": [-7.0243, 113.8689]},
    "WAWR": {"name": "Banyuwangi", "coords": [-8.3107, 114.3408]},
    "WAOO": {"name": "Malang", "coords": [-7.9266, 112.7166]}
}

# Streamlit UI
st.title("Flights Movement Visualization in East Java Airports")

# Date filters
st.sidebar.header("Filter by Date")
start_date = st.sidebar.date_input("Start Date", datetime(2025, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2025, 1, 1))

# Validate date range
if start_date > end_date:
    st.error("Error: Start date must be earlier than end date.")
else:
    # Format dates for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Query to calculate movements
    query = f"""
        SELECT 
            flights.ADEP, flights.ADES, flights.STATUS_FLIGHT, flights.DEP_ARR_LOCAL
        FROM flights 
        WHERE tanggal_dummy BETWEEN '{start_date_str}' AND '{end_date_str}';
    """

    # Run query
    df = run_query(query)

    # Initialize movement counts
    movement_data = {icao: {"REGULER": 0, "IRREGULER": 0, "TOTAL": 0} for icao in airports}

    # Process data
    for _, row in df.iterrows():
        locations = [row["ADEP"], row["ADES"]]
        for loc in locations:
            if loc in movement_data:
                category = "REGULER" if row["STATUS_FLIGHT"] == "REGULER" else "IRREGULER"
                movement_data[loc][category] += 1
                movement_data[loc]["TOTAL"] += 1

                # Add extra movement if DEP_ARR_LOCAL is 'L'
                if row["DEP_ARR_LOCAL"] == "L":
                    movement_data[loc][category] += 1
                    movement_data[loc]["TOTAL"] += 1

    # Create a map
    m = folium.Map(location=[-7.536, 112.238], zoom_start=8)

    # Add markers for each airport
    for icao, data in airports.items():
        location_name = data["name"]
        coords = data["coords"]
        movements = movement_data[icao]
        popup_text = f"""
            <b>{location_name}</b><br>
            Reguler: {movements['REGULER']}<br>
            Irreguler: {movements['IRREGULER']}<br>
            Total: {movements['TOTAL']}
        """
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=location_name
        ).add_to(m)

    # Display map
    folium_static(m)

    # Create movement detail table
    table_data = []
    for icao, counts in movement_data.items():
        table_data.append({
            "LOKASI": airports[icao]["name"],
            "REGULER": counts["REGULER"],
            "IRREGULER": counts["IRREGULER"],
            "TOTAL": counts["TOTAL"]
        })

    movement_df = pd.DataFrame(table_data)
    st.subheader("Movement Details")
    st.dataframe(movement_df)