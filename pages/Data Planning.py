import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

# Fungsi untuk konversi waktu
def convert_to_time(reference_time, value):
    if pd.isna(value):  # Jika nilai NaN atau None
        return None
    if isinstance(value, str):  # Jika nilai berupa string
        if "minute" in value:
            minutes = int(value.split()[0])
            return reference_time + timedelta(minutes=minutes)
        elif "hour" in value:
            hours = int(value.split()[0])
            return reference_time + timedelta(hours=hours)
        elif "day" in value:
            days = int(value.split()[0])
            return reference_time + timedelta(days=days)
        else:
            return None
    elif isinstance(value, pd.Timedelta):  # Jika nilai berupa Timedelta
        return reference_time + value
    else:
        return None  # Jika tipe data lain, abaikan

# Streamlit UI
st.set_page_config(layout="wide", page_title="Data Planning", page_icon="✈️")

# 1. Menambahkan Border Hitam pada Header menggunakan HTML dan CSS
header_html = """
    <div style="border: 0px solid black; padding: 5px; border-radius: 0px;">
        <h3 style="text-align: center;">DATA PLANNING CABANG SURABAYA</h3>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Sidebar for date selection
st.sidebar.header("Select Date")
tanggal_query = "SELECT DISTINCT tanggal FROM pprp ORDER BY tanggal ASC"
tanggal_df = run_query(tanggal_query)
tanggal_options = [
    pd.to_datetime(date, errors='coerce').date() if pd.notnull(date) else None
    for date in tanggal_df["tanggal"].tolist()
]

# Hapus nilai None atau NaT dari tanggal_options
tanggal_options = [date for date in tanggal_options if date is not None]

# Pastikan ada setidaknya satu tanggal yang valid
if not tanggal_options:
    tanggal_options = [datetime.now().date()]  # Jika tidak ada tanggal valid, gunakan tanggal sekarang

# Pilihan tanggal dari sidebar, gunakan tanggal pertama jika ada, atau default ke hari ini
selected_date = st.sidebar.date_input(
    "Tanggal", 
    value=datetime.now().date()
)
# 2. Menambahkan Tanggal yang Dipilih di Bawah Header
selected_date_str = selected_date.strftime('%d %B %Y')
date_html = f"""
    <div style="text-align: center; margin-top: 0px; font-size: 18px;">
        {selected_date_str}
    </div>
"""
st.markdown(date_html, unsafe_allow_html=True)

# 3. Menambahkan Garis Pembatas
st.markdown("<hr style='border:1px solid black'>", unsafe_allow_html=True)

query = f"""  
    SELECT
        COUNT(*) AS total_movements,          -- Menghitung total baris (movement)
        COUNT(DISTINCT RUTE) AS total_routes, -- Menghitung jumlah rute unik
        COUNT(DISTINCT IATA_CODE) AS total_airlines -- Menghitung jumlah maskapai unik berdasarkan ICAO_AIRLINE
    FROM
        sub_flight_db_2.pprp
    WHERE
        TANGGAL = '{selected_date}'
    """
# Eksekusi query
conn = create_connection()
result=run_query(query)
# Menampilkan hasil ke dalam kotak Streamlit

if not result.empty:
    total_movements = result['total_movements'][0]
    total_routes = result['total_routes'][0]
    total_airlines = result['total_airlines'][0]

    # Menampilkan data dalam format kotak
    col1, col2, col3 = st.columns(3)
    
# Menambahkan warna pastel menggunakan st.markdown dan HTML
    with col1:
        st.markdown(
            f"""
            <div style="background-color: #fef5a2; padding: 10px 15px; border-radius: 8px; text-align: center;">
                <h5>Total Movements</h5>
                <p style="font-size: 22px; font-weight: bold;">{total_movements}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(
            f"""
            <div style="background-color: #a2cbe7; padding: 10px 15px; border-radius: 8px; text-align: center;">
                <h5>Total Rute</h5>
                <p style="font-size: 22px; font-weight: bold;">{total_routes}</p>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown(
            f"""
            <div style="background-color: #b2e0b8; padding: 10px 15px; border-radius: 8px; text-align: center;">
                <h5>Total Maskapai</h5>
                <p style="font-size: 22px; font-weight: bold;">{total_airlines}</p>
            </div>
            """, unsafe_allow_html=True)
# Menambahkan jarak antara kotak dan expander
st.markdown("<br>", unsafe_allow_html=True)

# Query untuk mengambil data dengan nomor urut
movement_query = f"""
    SELECT 
        p.TANGGAL, 
        p.RUTE,
        a.AIRLINE_NAME,
        p.FLIGHT_NUMBER,  
        p.ETD, 
        p.ETA, 
        p.TYPE
    FROM 
        sub_flight_db_2.pprp p
    LEFT JOIN 
        sub_flight_db_2.airlines a ON p.ICAO_AIRLINE = a.ICAO_CODE
    WHERE 
        p.TANGGAL = '{selected_date}'
"""
# Menjalankan query menggunakan pandas
movements_df = pd.read_sql_query(movement_query, conn)

# Fungsi untuk mengonversi waktu menjadi HH:MM
def convert_to_time(timedelta_obj):
    try:
        # Mengambil hanya jam dan menit dari timedelta
        total_seconds = timedelta_obj.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        # Menampilkan jam dan menit dalam format "HH:MM"
        return f"{hours:02}:{minutes:02}"
    except Exception as e:
        return None  # Jika konversi gagal, kembalikan None
    
# Mengonversi kolom ETD dan ETA menjadi timedelta (dari HH:MM:SS)
movements_df['ETD'] = pd.to_timedelta(movements_df['ETD'])
movements_df['ETA'] = pd.to_timedelta(movements_df['ETA'])

# Mengonversi kolom ETD dan ETA menjadi HH:MM
movements_df["ETD"] = movements_df["ETD"].apply(lambda x: convert_to_time(x))
movements_df["ETA"] = movements_df["ETA"].apply(lambda x: convert_to_time(x))
conn.close()

# Menampilkan data dalam bentuk tabel
if not movements_df.empty:
    with st.expander("Klik untuk melihat daftar movement"):
        st.dataframe(movements_df)  # Menampilkan data movement dalam bentuk tabel
else:
    st.write("Tidak ada data untuk tanggal yang dipilih.")

#============================visual2==============
# Membuat koneksi ke database
conn = create_connection()

# Query untuk mendapatkan frekuensi arrival dan departure per jam
barchart_query = f"""
    SELECT 
        HOUR(
            CASE
                WHEN ARR_ICAO = 'WARR' THEN ETA
                WHEN DEP_ICAO = 'WARR' THEN ETD
                ELSE NULL
            END
        ) AS hour,
        SUM(CASE WHEN ARR_ICAO = 'WARR' THEN 1 ELSE 0 END) AS arrival_count,
        SUM(CASE WHEN DEP_ICAO = 'WARR' THEN 1 ELSE 0 END) AS departure_count
    FROM 
        sub_flight_db_2.pprp
    WHERE 
        TANGGAL = '{selected_date}'
    GROUP BY 
        hour
    ORDER BY 
        hour
"""

# Query untuk mendapatkan perbandingan international vs domestic berdasarkan TYPE
piechart_query = f"""
    SELECT 
        TYPE, 
        COUNT(*) AS frequency
    FROM 
        sub_flight_db_2.pprp
    WHERE 
        TANGGAL = '{selected_date}'
    GROUP BY 
        TYPE;
"""

# Menjalankan query menggunakan pandas
barchart_df = pd.read_sql_query(barchart_query, conn)
piechart_df = pd.read_sql_query(piechart_query, conn)

# Menutup koneksi
conn.close()
max_arrival = barchart_df['arrival_count'].max()
max_departure = barchart_df['departure_count'].max()
# Membuat subplot dengan 1 baris, 2 kolom (rasio 3:1 antara Barchart dan Piechart)
fig = make_subplots(
    rows=1, cols=2,  # 1 baris, 2 kolom
    column_widths=[0.75, 0.25],  # Rasio 3:1 untuk Barchart dan Piechart
    shared_yaxes=True,  # Berbagi sumbu Y antara kedua grafik
    subplot_titles=('Arrival vs Departure', 'International vs Domestic'),
    horizontal_spacing=0.05,
    specs=[[{"type": "bar"}, {"type": "pie"}]],  # Menentukan jenis plot: Bar untuk Barchart, Pie untuk Piechart
)

# --- Barchart ---
all_hours = list(range(24))
# Menentukan warna berdasarkan frekuensi tertinggi
arrival_pattern = ['\\' if count == max_arrival else '' for count in barchart_df['arrival_count']]
departure_pattern = ['\\' if count == max_departure else '' for count in barchart_df['departure_count']]

barchart = go.Bar(
    x=barchart_df['hour'],
    y=barchart_df['arrival_count'],
    name='Arrival',
    marker=dict(color='blue', pattern_shape=arrival_pattern),
    text=barchart_df['arrival_count'],
    textposition='outside'
)

departure = go.Bar(
    x=barchart_df['hour'],
    y=barchart_df['departure_count'],
    name='Departure',
    marker=dict(color='orange', pattern_shape=departure_pattern),
    text=barchart_df['departure_count'],
    textposition='outside'
)

fig.add_trace(barchart, row=1, col=1)
fig.add_trace(departure, row=1, col=1)

# --- Piechart ---
piechart = go.Pie(
    labels=piechart_df['TYPE'],
    values=piechart_df['frequency'],
    hole=0.5,  # Membuat hole di tengah pie chart
    marker=dict(colors=['rebeccaPurple', 'lavender'])
)

fig.add_trace(piechart, row=1, col=2)

# Update layout untuk sumbu dan gaya
fig.update_layout(
    title='Flight Statistics',
    showlegend=True,
    height=500,  # Total tinggi gambar
    xaxis_title='Hour of the Day',
    yaxis_title='Frequency',
    xaxis=dict(tickmode='array', tickvals=all_hours, ticktext=[f'{i:02}:00-{i+1:02}:59' for i in all_hours])
)

# Menampilkan grafik di Streamlit
st.plotly_chart(fig)
#=================visualisasi 3=================
movement_query2 = f"""
    (SELECT 
        IATA_CODE AS category,
        'Maskapai' AS type,
        COUNT(*) AS total_movements
    FROM 
        sub_flight_db_2.pprp
    WHERE 
        TANGGAL = '{selected_date}'
    GROUP BY 
        IATA_CODE)

    UNION ALL

    (SELECT 
        RUTE AS category,
        'Rute' AS type,
        COUNT(*) AS total_movements
    FROM 
        sub_flight_db_2.pprp
    WHERE 
        TANGGAL = '{selected_date}'
    GROUP BY 
        RUTE)
"""

# Membuat koneksi ke database dan menjalankan query
conn = create_connection()
movement_df2 = pd.read_sql_query(movement_query2, conn)
conn.close()

# Membuat 2 kolom untuk menampilkan konten
col1, col2 = st.columns(2)

# Bar Chart untuk Total Movement berdasarkan Maskapai (ICAO_AIRLINE)
with col1:
    maskapai_df = movement_df2[movement_df2['type'] == 'Maskapai']
    maskapai_df = maskapai_df.sort_values(by='total_movements', ascending=False)
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=maskapai_df['category'],
        y=maskapai_df['total_movements'],
        text=maskapai_df['total_movements'],
        textposition='outside',
        marker=dict(color='royalblue'),
        name='Total Movements by Airline'
    ))
    fig1.update_layout(
        title="Total Movements berdasarkan Maskapai",
        xaxis_title="Maskapai",
        yaxis_title="Total Movements",
        xaxis_tickangle=-45,  # Mengatur agar label x-axis miring
        showlegend=False,
        xaxis=dict(tickmode='array', tickvals=maskapai_df['category'], ticktext=maskapai_df['category']),  # Menampilkan semua nilai x
        bargap=0.2,  # Jarak antar bar
        xaxis_rangeslider_visible=False,  # Menambahkan slider untuk sumbu X
    )
    st.plotly_chart(fig1)

# Bar Chart untuk Total Movement berdasarkan Rute (RUTE)
with col2:
    rute_df = movement_df2[movement_df2['type'] == 'Rute']
    rute_df = rute_df.sort_values(by='total_movements', ascending=False)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=rute_df['category'],
        y=rute_df['total_movements'],
        text=rute_df['total_movements'],
        textposition='outside',
        marker=dict(color='darkorange'),
        name='Total Movements by Route'
    ))
    fig2.update_layout(
        title="Total Movements berdasarkan Rute",
        xaxis_title="Rute",
        yaxis_title="Total Movements",
        xaxis_tickangle=-45,  # Mengatur agar label x-axis miring
        showlegend=False,
        xaxis=dict(tickmode='array', tickvals=rute_df['category'], ticktext=rute_df['category']),  # Menampilkan semua nilai x
        bargap=0.2,  # Jarak antar bar
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig2)

#=============expander==================
exp1_query = f"""
    SELECT 
        HOUR(
            CASE
                WHEN ARR_ICAO = 'WARR' THEN ETA
                WHEN DEP_ICAO = 'WARR' THEN ETD
                ELSE NULL
            END
        ) AS hour,
        FLIGHT_NUMBER,
        IATA_CODE,
        ETD,
        ETA,
        TYPE,
        RUTE
    FROM 
        sub_flight_db_2.pprp
    WHERE 
        TANGGAL = '{selected_date}'
    ORDER BY 
        hour
"""
conn = create_connection()
exp1_df = pd.read_sql_query(exp1_query, conn)
conn.close()

# Mengonversi kolom ETD dan ETA menjadi timedelta (dari HH:MM:SS)
exp1_df['ETD'] = pd.to_timedelta(exp1_df['ETD'])
exp1_df['ETA'] = pd.to_timedelta(exp1_df['ETA'])

# Mengonversi kolom ETD dan ETA menjadi HH:MM
exp1_df["ETD"] = exp1_df["ETD"].apply(lambda x: convert_to_time(x))
exp1_df["ETA"] = exp1_df["ETA"].apply(lambda x: convert_to_time(x))

# Query untuk mendapatkan daftar maskapai dan rute yang tersedia untuk selected_date
airlines_query = f"""
    SELECT DISTINCT IATA_CODE
    FROM sub_flight_db_2.pprp
    WHERE TANGGAL = '{selected_date}'
"""

routes_query = f"""
    SELECT DISTINCT RUTE
    FROM sub_flight_db_2.pprp
    WHERE TANGGAL = '{selected_date}'
"""

# Membuat koneksi ke database dan menjalankan query untuk mendapatkan maskapai dan rute
conn = create_connection()
airlines_df = pd.read_sql_query(airlines_query, conn)
routes_df = pd.read_sql_query(routes_query, conn)
conn.close()

# Menampilkan kolom untuk filter
col1, col2, col3 = st.columns(3)

# Filter Jam
with col1:
    hour_filter = st.slider(
        "Pilih Jam", 
        min_value=0, 
        max_value=23, 
        value=(0, 23),  # Default untuk rentang jam dari 00:00 - 23:59
        step=1
    )

# Filter Tipe Penerbangan
with col2:
    flight_type = st.selectbox(
        "Pilih Tipe Penerbangan", 
        options=["All", "Domestik", "Internasional"],
        index=0
    )

# Filter Maskapai dan Rute
with col3:
    additional_filter = st.selectbox(
        "Pilih Filter", 
        options=["All", "Airline", "Rute"],
        index=0
    )

# Menambahkan filter untuk maskapai
if additional_filter == "Airline":
    selected_airlines = st.multiselect("Pilih Maskapai", airlines_df['IATA_CODE'].tolist(), default=airlines_df['IATA_CODE'].tolist())
else:
    selected_airlines = None  # Jika tidak memilih filter airline

# Menambahkan filter untuk rute
if additional_filter == "Rute":
    selected_routes = st.multiselect("Pilih Rute", routes_df['RUTE'].tolist(), default=routes_df['RUTE'].tolist())
else:
    selected_routes = None  # Jika tidak memilih filter route

# Mengonversi nilai jam ke format HH:MM
start_hour = f"{hour_filter[0]:02}:00"
end_hour = f"{hour_filter[1]:02}:59"

# Menentukan filter berdasarkan tipe penerbangan
if flight_type == "All":
    filtered_df = exp1_df[(exp1_df['hour'] >= hour_filter[0]) & (exp1_df['hour'] <= hour_filter[1])]
elif flight_type == "Domestik":
    filtered_df = exp1_df[(exp1_df['hour'] >= hour_filter[0]) & (exp1_df['hour'] <= hour_filter[1]) & (exp1_df['TYPE'] == "domestik")]
else:  # Internasional
    filtered_df = exp1_df[(exp1_df['hour'] >= hour_filter[0]) & (exp1_df['hour'] <= hour_filter[1]) & (exp1_df['TYPE'] == "internasional")]

# Menambahkan filter berdasarkan Maskapai dan Rute
if selected_airlines:
    filtered_df = filtered_df[filtered_df['IATA_CODE'].isin(selected_airlines)]

if selected_routes:
    filtered_df = filtered_df[filtered_df['RUTE'].isin(selected_routes)]

# Menambahkan satu expander untuk data
with st.expander(f"Klik untuk melihat data movement per jam dan data domestic/international antara {start_hour} - {end_hour}"):
    st.write(f"Data movement per jam (terfilter oleh jam {start_hour} - {end_hour}, tipe {flight_type}, dan filter {additional_filter}):")
    st.dataframe(filtered_df)  # Menampilkan data movement per jam yang terfilter