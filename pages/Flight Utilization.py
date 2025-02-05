import streamlit as st
import pymysql
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime
import plotly.express as px
from plotly import graph_objects as go

# Create connection
def create_connection():
    secrets = st.secrets["mysql"]
    try:
        conn = pymysql.connect(
            host=secrets["host"],
            user=secrets["username"],
            password=secrets["password"],
            database=secrets["database"],
            port=secrets["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

# Query data
def run_query(query):
    conn = create_connection()
    if conn is None:
        return pd.DataFrame()  # Return empty DataFrame if connection fails
    try:
        df = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return pd.DataFrame()  # Return empty DataFrame if query fails
    finally:
        conn.close()
    return df

st.set_page_config(layout="wide", page_title="Utilization", page_icon="🛠")

# Streamlit UI
st.title("Performance Analytical Dashboard")

# Membuat 3 kolom untuk menata dropdown
col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    # Dropdown untuk memilih airlines
    query_airlines = "SELECT DISTINCT ICAO_AIRLINE FROM pprp"
    airlines_df = run_query(query_airlines)
    airlines_pprp = airlines_df['ICAO_AIRLINE'].tolist()
    selected_airlines = st.selectbox(
        "Pilih airlines:",
        options=airlines_pprp,
        key="airline_selectbox"
    )

with col2:
    # Dropdown untuk memilih flight numbers
    query_flight_numbers = f"SELECT DISTINCT FLIGHT_NUMBER FROM pprp WHERE ICAO_AIRLINE = '{selected_airlines}'"
    flight_numbers_df = run_query(query_flight_numbers)
    available_flight_numbers = flight_numbers_df['FLIGHT_NUMBER'].tolist()
    
    selected_flight_number = st.selectbox(
        "Pilih flight number:",
        options=available_flight_numbers,
        key="flight_number_selectbox"
    )

with col3:
    # Filter rute berdasarkan pilihan airline dan flight number
    if selected_flight_number:
        # Menggunakan '=' untuk satu flight number, bukan 'IN'
        query_rutes = f"SELECT DISTINCT RUTE FROM pprp WHERE ICAO_AIRLINE = '{selected_airlines}' AND FLIGHT_NUMBER = {selected_flight_number}"
        rutes_df = run_query(query_rutes)
        
        # Pastikan kolom 'RUTE' ada dalam hasil query
        if 'RUTE' in rutes_df.columns:
            available_rutes = rutes_df['RUTE'].tolist()
        else:
            available_rutes = []

        # Dropdown untuk memilih rute
        selected_rute = st.selectbox(
            "Pilih rute:",
            options=available_rutes,
            key="rute_selectbox"
        )

# Filter SQL berdasarkan pilihan pengguna
def get_query_filter(selected_airlines, selected_flight_number, selected_rute):
    airline_filter = f"ICAO_AIRLINE = '{selected_airlines}'"
    flight_number_filter = f"FLIGHT_NUMBER = {selected_flight_number}"
    rute_filter = f"RUTE = '{selected_rute}'"
    return f"WHERE {airline_filter} AND {flight_number_filter} AND {rute_filter}"

# Menampilkan query filter (contoh)
query_filter = get_query_filter(selected_airlines, selected_flight_number, selected_rute)

# Mengambil data untuk Izin Route
query_izin_route = "SELECT COUNT(*) AS izin_route_count FROM pprp"
izin_route_df = run_query(query_izin_route)
izin_route_count = izin_route_df.iloc[0]['izin_route_count']

# Mengambil data untuk Realisasi Route (tanggal_dummy antara 27 Okt 2024 hingga 28 Mar 2025)
query_realisasi_route = """
    SELECT COUNT(*) AS realisasi_route_count
    FROM flights
    WHERE tanggal_dummy BETWEEN '2024-10-27' AND '2025-03-28'
"""
realisasi_route_df = run_query(query_realisasi_route)
realisasi_route_count = realisasi_route_df.iloc[0]['realisasi_route_count']

# Menghitung sisa Izin Route
sisa_izin_route = izin_route_count - realisasi_route_count

# Menghitung Persentase Realisasi Route
percentage_realisasi = (realisasi_route_count / izin_route_count) * 100 if izin_route_count != 0 else 0

