import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

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
st.set_page_config(layout="wide", page_title="Traffic Summary", page_icon="📊")

# 1. Menambahkan Border Hitam pada Header menggunakan HTML dan CSS
header_html = """
    <div style="border: 0px solid black; padding: 5px; border-radius: 0px;">
        <h3 style="text-align: center;">DATA TRAFFIC CABANG SURABAYA</h3>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Sidebar for date selection
st.sidebar.header("Select Date")
tanggal_dummy_query = "SELECT DISTINCT tanggal_dummy FROM flights;"
tanggal_dummy_df = run_query(tanggal_dummy_query)
# tanggal_options = [pd.to_datetime(date).date() for date in tanggal_dummy_df["tanggal_dummy"].tolist()]
# selected_date = st.sidebar.date_input("Tanggal", value=tanggal_options[0] if tanggal_options else datetime.now().date())
tanggal_options = [
    pd.to_datetime(date, errors='coerce').date() if pd.notnull(date) else None
    for date in tanggal_dummy_df["tanggal_dummy"].tolist()
]

# Hapus nilai None atau NaT dari tanggal_options
tanggal_options = [date for date in tanggal_options if date is not None]

# Pastikan ada setidaknya satu tanggal yang valid
if not tanggal_options:
    tanggal_options = [datetime.now().date()]  # Jika tidak ada tanggal valid, gunakan tanggal sekarang

# Pilihan tanggal dari sidebar, gunakan tanggal pertama jika ada, atau default ke hari ini
selected_date = st.sidebar.date_input(
    "Tanggal", 
    value=tanggal_options[0]
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

# Main query to get flight data
query = f"""
    SELECT 
        flights.tanggal_dummy,
        flights.ADEP, 
        flights.ADES, 
        flights.STATUS_FLIGHT, 
        flights.ACID, 
        flights.DEP_ARR_LOCAL, 
        flights.ATD, 
        flights.ATA, 
        dep_airports.COUNTRY AS DEP_COUNTRY,  -- Country dari ADEP
        arr_airports.COUNTRY AS ARR_COUNTRY,  -- Country dari ADES
        airlines.AIRLINE_NAME
    FROM sub_flight_db.flights
    LEFT JOIN sub_flight_db.airports AS dep_airports
        ON flights.ADEP = dep_airports.ICAO_CODE
    LEFT JOIN sub_flight_db.airports AS arr_airports
        ON flights.ADES = arr_airports.ICAO_CODE
    LEFT JOIN sub_flight_db.airlines
        ON flights.ICAO_CODE = airlines.ICAO_CODE
    WHERE 
    (flights.ADEP = 'WARR' OR flights.ADES = 'WARR')
    AND flights.tanggal_dummy = '{selected_date.strftime('%Y-%m-%d')}';"""
data = run_query(query)

# Konversi waktu menggunakan fungsi convert_to_time
reference_time = datetime.strptime(f"{selected_date} 00:00:00", "%Y-%m-%d %H:%M:%S")
data["ATD_converted"] = data["ATD"].apply(lambda x: convert_to_time(reference_time, x))
data["ATA_converted"] = data["ATA"].apply(lambda x: convert_to_time(reference_time, x))

# Initialize counters and data structures
movement_data = {"SCHEDULE": {}, "UNSCHEDULE": {}, "MILITARY": {}}
schedule_keterangan = {}
unschedule_keterangan = {"POSITIONING": 0, "CARGO": 0, "CHARTER": 0, "EXTRA": 0, "VIP": 0}

def count_movements(row, movement_type):
    if movement_type not in movement_data:
        return

    adep, ades = row["ADEP"], row["ADES"]
    dep_country, arr_country = row["DEP_COUNTRY"], row["ARR_COUNTRY"]

    # Local movement (L): Both ADEP and ADES are WARR
    if adep == "WARR" and ades == "WARR":
        movement_data[movement_type]["DOM_DEP"] = movement_data[movement_type].get("DOM_DEP", 0) + 1
        movement_data[movement_type]["DOM_ARR"] = movement_data[movement_type].get("DOM_ARR", 0) + 1
        return  # No need to check other conditions

    # Domestic Departure (hanya untuk WARR)
    if adep == "WARR" and arr_country.strip() == "Domestik":
        movement_data[movement_type]["DOM_DEP"] = movement_data[movement_type].get("DOM_DEP", 0) + 1

    # Domestic Arrival (hanya untuk WARR)
    if ades == "WARR" and dep_country.strip() == "Domestik":
        movement_data[movement_type]["DOM_ARR"] = movement_data[movement_type].get("DOM_ARR", 0) + 1

    # International Departure (hanya untuk WARR)
    if adep == "WARR" and arr_country.strip() == "International":
        movement_data[movement_type]["INT_DEP"] = movement_data[movement_type].get("INT_DEP", 0) + 1

    # International Arrival (hanya untuk WARR)
    if ades == "WARR" and dep_country.strip() == "International":
        movement_data[movement_type]["INT_ARR"] = movement_data[movement_type].get("INT_ARR", 0) + 1

# Process data
for _, row in data.iterrows():
    status = row["STATUS_FLIGHT"]
    
    if status == "REGULER":
        count_movements(row, "SCHEDULE")
        airline_name = row["AIRLINE_NAME"]
        schedule_keterangan[airline_name] = schedule_keterangan.get(airline_name, 0) + 1
        if row["DEP_ARR_LOCAL"] == "L":
            schedule_keterangan[airline_name] = schedule_keterangan.get(airline_name, 0) + 1
    elif status in ["POSITIONING", "EXTRA", "VIP", "CHARTER", "CARGO"]:
        # Ensure the key exists in unschedule_keterangan dictionary
        if status not in unschedule_keterangan:
            unschedule_keterangan[status] = 0  # Initialize if not already present
        count_movements(row, "UNSCHEDULE")
        unschedule_keterangan[status] += 1
        # Jika DEP_ARR_LOCAL adalah 'L', gandakan jumlahnya
        if row["DEP_ARR_LOCAL"] == "L":
            unschedule_keterangan[status] += 1  # Gandakan untuk 'L'
    else:
        count_movements(row, "MILITARY")

# Prepare table data
rows = []
number = 1
total_dom_dep = 0
total_dom_arr = 0
total_int_dep = 0
total_int_arr = 0
total_movements = 0

for status, counts in movement_data.items():
    dom_dep = counts.get("DOM_DEP", 0)
    dom_arr = counts.get("DOM_ARR", 0)
    int_dep = counts.get("INT_DEP", 0)
    int_arr = counts.get("INT_ARR", 0)
    total = dom_dep + dom_arr + int_dep + int_arr

    # Update total movements
    total_dom_dep += dom_dep
    total_dom_arr += dom_arr
    total_int_dep += int_dep
    total_int_arr += int_arr
    total_movements += total

    if status == "SCHEDULE":
        keterangan = "<ul>" + "".join([f"<li>{key} = {value}</li>" for key, value in schedule_keterangan.items()]) + "</ul>"
    elif status == "UNSCHEDULE":
        # Include the unscheduled flight statuses and counts
        keterangan = "<ul>" + "".join([f"<li>{key} = {value}</li>" for key, value in unschedule_keterangan.items()]) + "</ul>"
    else:
        keterangan = "MILITARY MOVEMENT"

    rows.append({
        "NO": number,
        "STATUS": status,
        "DOM DEP": dom_dep,
        "DOM ARR": dom_arr,
        "INT DEP": int_dep,
        "INT ARR": int_arr,
        "TOTAL": total,
        "KETERANGAN": keterangan
    })
    number += 1
# Menambahkan baris terakhir untuk total movement hari itu
rows.append({
    "NO": number,
    "STATUS": "TOTAL",
    "DOM DEP": total_dom_dep,
    "DOM ARR": total_dom_arr,
    "INT DEP": total_int_dep,
    "INT ARR": total_int_arr,
    "TOTAL": total_movements,
    "KETERANGAN": "Total movement for the day"
})

# Convert to DataFrame
movement_df = pd.DataFrame(rows)

# 4. Styling for the table
table_style = """
    <style>
        table {
            width: 100%;  /* Set table to occupy full available width */
            margin-left: auto;
            margin-right: auto;
            font-size: 14px;
            border-collapse: collapse;  /* Ensures borders are merged */
        }
        th, td {
            padding: 8px;
            text-align: center;
        }
        th {
            background-color: #f2f2f2;
            border: 1px solid black;
            text-align: center; /* Header aligned to center */
        }
        td {
            border: 1px solid black;
            text-align: center; /* Data cells aligned to center by default */
        }
        
        /* Align last column (KETERANGAN) to left */
        td:last-child {
            width: 350px;  /* Ensure KETERANGAN column has enough space */
            text-align: left;  /* Left align text for KETERANGAN */
            padding-left: 10px;  /* Add padding for better readability */
        }

        /* Adjust line (hr) to be consistent with the table */
        hr {
            width: 100%;
            border: 1px solid black;
        }
    </style>
"""

# Display the table with the custom style
movement_df_styled = movement_df.style \
    .set_properties(**{
        'border': '1px solid black',
        'text-align': 'center',
        'font-size': '14px'
    }) \
    .set_table_styles([{
        'selector': 'th',
        'props': [('border', '1px solid black'), ('background-color', '#f2f2f2'), ('font-size', '14px')]
    }, {
        'selector': 'td',
        'props': [('border', '1px solid black'), ('font-size', '14px')]
    }]) \
    .hide(axis="index")

# Display the table and style it
st.markdown(table_style, unsafe_allow_html=True)
st.write(movement_df_styled.to_html(escape=False), unsafe_allow_html=True)

# Membagi data ke dalam bin waktu
time_bins = [f"{i:02}:00-{i:02}:59" for i in range(24)]  # Binning waktu per jam
hourly_summary = {time: {"Arrival": 0, "Departure": 0, "Movement": 0} for time in time_bins}

# Menghitung jumlah kedatangan, keberangkatan, dan total per jam
for _, row in data.iterrows():
    dep_arr_local = row["DEP_ARR_LOCAL"]
    atd_time = row["ATD_converted"]
    ata_time = row["ATA_converted"]
    adep = row["ADEP"]
    ades = row["ADES"]
    dep_country = row["DEP_COUNTRY"]
    arr_country = row["ARR_COUNTRY"]

    # Local movement
    if dep_arr_local == "L" and adep == "WARR" and ades == "WARR":
        if pd.notna(ata_time):  # Arrival part
            hour = f"{ata_time.hour:02}:00-{ata_time.hour:02}:59"
            hourly_summary[hour]["Arrival"] += 1
            hourly_summary[hour]["Movement"] += 1
        if pd.notna(atd_time):  # Departure part
            hour = f"{atd_time.hour:02}:00-{atd_time.hour:02}:59"
            hourly_summary[hour]["Departure"] += 1
            hourly_summary[hour]["Movement"] += 1
    # Domestic Arrival
    elif dep_arr_local == "A" and pd.notna(ata_time) and arr_country == "Domestik":
        hour = f"{ata_time.hour:02}:00-{ata_time.hour:02}:59"
        hourly_summary[hour]["Arrival"] += 1
        hourly_summary[hour]["Movement"] += 1
    # Domestic Departure
    elif dep_arr_local == "D" and pd.notna(atd_time) and dep_country == "Domestik":
        hour = f"{atd_time.hour:02}:00-{atd_time.hour:02}:59"
        hourly_summary[hour]["Departure"] += 1
        hourly_summary[hour]["Movement"] += 1
    # International Arrival
    elif dep_arr_local == "A" and pd.notna(ata_time) and arr_country == "International":
        hour = f"{ata_time.hour:02}:00-{ata_time.hour:02}:59"
        hourly_summary[hour]["Arrival"] += 1
        hourly_summary[hour]["Movement"] += 1
    # International Departure
    elif dep_arr_local == "D" and pd.notna(atd_time) and dep_country == "International":
        hour = f"{atd_time.hour:02}:00-{atd_time.hour:02}:59"
        hourly_summary[hour]["Departure"] += 1
        hourly_summary[hour]["Movement"] += 1

# Konversi hasil ke DataFrame
hourly_df = pd.DataFrame.from_dict(hourly_summary, orient="index").reset_index()
hourly_df.columns = ["Hour", "Departure", "Arrival",  "Movement"]

total_row = pd.DataFrame({
    "Hour": ["Total"],
    "Arrival": [hourly_df["Arrival"].sum()],
    "Departure": [hourly_df["Departure"].sum()],
    "Movement": [hourly_df["Movement"].sum()]
})
hourly_df = pd.concat([hourly_df, total_row], ignore_index=True)

#st.markdown("<h4 style='text-align: center;'>Hourly Summary</h4>", unsafe_allow_html=True)
# Layout Landscape: Tabel di Sebelah Kiri, Grafik di Sebelah Kanan
col1, col2 = st.columns([1, 2])  # Proporsi kolom: 1 untuk tabel, 2 untuk grafik

# Hitung tinggi tabel berdasarkan jumlah baris
row_height = 29  # Tinggi setiap baris dalam tabel
header_height = 30  # Tinggi header
table_height = len(hourly_df) * row_height + header_height  # Total tinggi tabel

# Tabel di Kolom Kiri
with col1:
    st.markdown("<h5 style='text-align: center;'>ARRIVAL, DEPARTURE, dan TOTAL MOVEMENT</h5>", unsafe_allow_html=True)
    # Buat tabel menggunakan Plotly
    fig_table = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["<b>Hour</b>", "<b>Arrival</b>", "<b>Departure</b>", "<b>Movement</b>"],
                    fill_color="black",
                    font=dict(color="white", size=13),
                    align="center",
                ),
                cells=dict(
                    values=[
                        hourly_df["Hour"],
                        hourly_df["Arrival"],
                        hourly_df["Departure"],
                        hourly_df["Movement"],
                    ],
                    fill=dict(color=["white", "lightgrey"]),
                    align="center",
                    font=dict(size=13),
                    height=row_height,
                ),
            )
        ]
    )

    # Atur lebar dan tinggi tabel
    fig_table.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=table_height,  # Tinggi tabel otomatis sesuai jumlah baris
        width=600,  # Lebar tabel (opsional)
    )

    # Tampilkan tabel dengan Streamlit
    st.plotly_chart(fig_table, use_container_width=True)

# Buat DataFrame baru tanpa baris total
hourly_df_chart = hourly_df[hourly_df["Hour"] != "Total"]

# Bar Chart di Kolom Kanan
with col2:
    # Chart 1: Arrival vs Departure
    fig1 = px.bar(
        hourly_df_chart,  # Gunakan DataFrame tanpa total row
        x='Hour', 
        y=['Departure', 'Arrival'], 
        barmode='group', 
        labels={'value': 'Frequency', 'Hour': 'Hour'},
        color_discrete_map={"Arrival": "orange", "Departure": "blue"},
        text_auto=True  # Menambahkan angka otomatis di atas bar
    )
    fig1.update_traces(textposition='outside')  # Posisi teks di luar batang
    fig1.update_layout(
        height=400,  # Tinggi chart
        title_x=0.4,  # Center alignment untuk judul
        margin=dict(l=50, r=50, t=50, b=50),  # Jarak margin chart
        title=dict(text="Departure vs Arrival", font=dict(size=14)),  # Judul lebih kecil
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Total Movement
    # st.markdown("<h4 style='text-align: center;'>Total Movement Chart</h4>", unsafe_allow_html=True)
    fig2 = px.bar(
        hourly_df_chart, 
        x='Hour', 
        y='Movement', 
        labels={'Movement': 'Frequency', 'Hour': 'Hour'},
        color_discrete_sequence=["green"],
        text='Movement'  # Menambahkan angka dari kolom Movement
    )
    fig2.update_traces(textposition='outside')  # Posisi teks di luar batang
    fig2.update_layout(
        height=400,  # Tinggi chart
        title_x=0.4,  # Center alignment untuk judul
        margin=dict(l=50, r=50, t=30, b=50),  # Jarak margin chart untuk mepet
        title=dict(text="Total Movement", font=dict(size=14),),  # Judul lebih kecil
    )
    st.plotly_chart(fig2, use_container_width=True)

# page 3

# Query untuk menghitung total movement per tanggal pada tahun 2023, 2024, dan 2025
query2 = f"""
    SELECT 
        tanggal_dummy,
        SUM(CASE WHEN YEAR(tanggal_dummy) = 2023 AND DEP_ARR_LOCAL = 'L' AND STATUS_FLIGHT = 'REGULER' THEN 2
                 WHEN YEAR(tanggal_dummy) = 2023 AND STATUS_FLIGHT = 'REGULER' THEN 1
                 ELSE 0 END) AS total_movement_2023,
        SUM(CASE WHEN YEAR(tanggal_dummy) = 2024 AND DEP_ARR_LOCAL = 'L' AND STATUS_FLIGHT = 'REGULER' THEN 2
                 WHEN YEAR(tanggal_dummy) = 2024 AND STATUS_FLIGHT = 'REGULER' THEN 1
                 ELSE 0 END) AS total_movement_2024,
        SUM(CASE WHEN YEAR(tanggal_dummy) = 2025 AND DEP_ARR_LOCAL = 'L' AND STATUS_FLIGHT = 'REGULER' THEN 2
                 WHEN YEAR(tanggal_dummy) = 2025 AND STATUS_FLIGHT = 'REGULER' THEN 1
                 ELSE 0 END) AS total_movement_2025
    FROM sub_flight_db.flights
    WHERE MONTH(tanggal_dummy) = {selected_date.month}  -- Mengambil bulan yang dipilih
    GROUP BY tanggal_dummy
    ORDER BY tanggal_dummy;
"""

# Menjalankan query untuk mengambil data movement
data2 = run_query(query2)

# Pastikan kolom tanggal_dummy dalam format datetime
data2['tanggal_dummy'] = pd.to_datetime(data2['tanggal_dummy'], errors='coerce')

# Menghapus baris dengan nilai NaT setelah konversi
data2 = data2.dropna(subset=['tanggal_dummy'])

# Format tanggal untuk bulan yang dipilih
data2['Tanggal'] = data2['tanggal_dummy'].dt.strftime('%d %B')

# Mengisi nilai yang NaN dengan 0
data2['total_movement_2023'] = data2['total_movement_2023'].fillna(0)
data2['total_movement_2024'] = data2['total_movement_2024'].fillna(0)
data2['total_movement_2025'] = data2['total_movement_2025'].fillna(0)

# Group data by Tanggal
pivot_data = data2.groupby('Tanggal').agg({
    'total_movement_2023': 'sum',
    'total_movement_2024': 'sum',
    'total_movement_2025': 'sum'
}).reset_index()

# Menghitung Growth 2023-2024 dan Growth 2024-2025
pivot_data['Growth 2023-2024'] = pivot_data.apply(
    lambda row: 0 if row['total_movement_2023'] == 0 else ((row['total_movement_2024'] - row['total_movement_2023']) / row['total_movement_2023']) * 100,
    axis=1
)

pivot_data['Growth 2024-2025'] = pivot_data.apply(
    lambda row: 0 if row['total_movement_2024'] == 0 else ((row['total_movement_2025'] - row['total_movement_2024']) / row['total_movement_2024']) * 100,
    axis=1
)

# Membulatkan growth menjadi angka bulat
pivot_data['Growth 2023-2024'] = pivot_data['Growth 2023-2024'].round(1).astype(float)
pivot_data['Growth 2024-2025'] = pivot_data['Growth 2024-2025'].round(1).astype(float)

# Menangani pembagian dengan 0 dan NaN dengan mengisi dengan 0
pivot_data['Growth 2023-2024'] = pivot_data['Growth 2023-2024'].fillna(0)
pivot_data['Growth 2024-2025'] = pivot_data['Growth 2024-2025'].fillna(0)

avg_growth_2023_2024 = pivot_data['Growth 2023-2024'].mean()
avg_growth_2024_2025 = pivot_data['Growth 2024-2025'].mean()

pivot_data = pivot_data.append({
    'Tanggal': 'Rata-rata',
    'total_movement_2023': '',
    'total_movement_2024': '',
    'Growth 2023-2024': round(avg_growth_2023_2024,1),
    'total_movement_2025': '',
    'Growth 2024-2025': round(avg_growth_2024_2025,1)
}, ignore_index=True)

pivot_data['Growth 2023-2024'] = pivot_data['Growth 2023-2024'].astype(str) + '%'
pivot_data['Growth 2024-2025'] = pivot_data['Growth 2024-2025'].astype(str) + '%'

# Membuat data untuk line chart dan menghapus baris 'Rata-rata' untuk chart
line_chart_data = pivot_data[pivot_data['Tanggal'] != 'Rata-rata']

# Mengonversi Growth menjadi angka (tanpa persen)
line_chart_data['Growth 2023-2024'] = line_chart_data['Growth 2023-2024'].str.replace('%', '').astype(float)
line_chart_data['Growth 2024-2025'] = line_chart_data['Growth 2024-2025'].str.replace('%', '').astype(float)

# Mengonversi 'Tanggal' menjadi datetime
line_chart_data['Tanggal'] = pd.to_datetime(line_chart_data['Tanggal'], errors='coerce', format='%d %B')

# Menghapus baris yang memiliki NaT di kolom 'Tanggal' atau kolom lainnya yang digunakan dalam grafik
line_chart_data = line_chart_data.dropna(subset=['Tanggal', 'total_movement_2023', 'total_movement_2024', 'total_movement_2025'])

# Membuat dua kolom untuk menampilkan grafik secara berdampingan
col1, col2 = st.columns(2)
selected_month = selected_date.strftime("%B")
# Grafik Perbandingan Total Movement
with col1:
    st.markdown(f"<h4 style='text-align: center;'>Data Traffik Domestik dan Internasional Berjadwal Bulan {selected_month} 2025</h4>", unsafe_allow_html=True)
    # Membuat tabel pergerakan dan growth berdasarkan tanggal
    fig_table = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["<b>Tanggal</b>", "<b>2023</b>", "<b>2024</b>", 
                            "<b>Growth</b>", "<b>2025</b>", "<b>Growth</b>"],
                    fill_color="black",
                    font=dict(color="white", size=13),
                    align="center",
                ),
                cells=dict(
                    values=[
                        pivot_data['Tanggal'],
                        pivot_data['total_movement_2023'],
                        pivot_data['total_movement_2024'],
                        pivot_data['Growth 2023-2024'],
                        pivot_data['total_movement_2025'],
                        pivot_data['Growth 2024-2025']
                    ],
                    fill=dict(color=["white", "lightgrey"]),
                    align="center",
                    font=dict(size=11),
                    height=27,
                ),
            )
        ]
    )

    # Atur lebar dan tinggi tabel agar lebih sempit
    fig_table.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),  # Margin tabel
        height=27*(len(pivot_data)+3),  # Sesuaikan tinggi tabel
        width=500,  # Lebar tabel lebih sempit
        autosize=True,
    )

    # Tampilkan tabel dengan Streamlit
    st.plotly_chart(fig_table, use_container_width=True)
    

# Grafik Growth 2024-2025
with col2:
    st.markdown(f"<h4 style='text-align: center;'>Periodesasi Bulan {selected_month} 2023 vs 2024 vs 2025</h4>", unsafe_allow_html=True)
    plt.figure(figsize=(10, 6))

    # Plot untuk setiap tahun
    plt.plot(line_chart_data['Tanggal'].dt.strftime('%d %B'), line_chart_data['total_movement_2023'], label="2023", marker='o')
    plt.plot(line_chart_data['Tanggal'].dt.strftime('%d %B'), line_chart_data['total_movement_2024'], label="2024", marker='o')
    plt.plot(line_chart_data['Tanggal'].dt.strftime('%d %B'), line_chart_data['total_movement_2025'], label="2025", marker='o')

    # # Menambahkan angka di setiap marker 'o'
    # for i in range(len(line_chart_data)):
    #     plt.text(line_chart_data['Tanggal'].dt.strftime('%d %B')[i], 
    #              line_chart_data['total_movement_2023'][i], 
    #              str(line_chart_data['total_movement_2023'][i]), 
    #              ha='center', va='bottom', fontsize=8)
    #     plt.text(line_chart_data['Tanggal'].dt.strftime('%d %B')[i], 
    #              line_chart_data['total_movement_2024'][i], 
    #              str(line_chart_data['total_movement_2024'][i]), 
    #              ha='center', va='bottom', fontsize=8)
    #     plt.text(line_chart_data['Tanggal'].dt.strftime('%d %B')[i], 
    #              line_chart_data['total_movement_2025'][i], 
    #              str(line_chart_data['total_movement_2025'][i]), 
    #              ha='center', va='bottom', fontsize=8)

    plt.xlabel("Tanggal")
    plt.ylabel("Total Movement")
    plt.xticks(rotation=45)
    plt.legend()

    st.pyplot(plt)
    st.markdown("<h4 style='text-align: center;'>Grafik Growth 2024-2025</h4>", unsafe_allow_html=True)
    plt.figure(figsize=(10, 6))

    # Plot untuk Growth 2024-2025
    plt.plot(line_chart_data['Tanggal'].dt.strftime('%d %B'), line_chart_data['Growth 2024-2025'], label="Growth 2024-2025", marker='o', color='r')
    # Menambahkan angka di setiap marker 'o' untuk Growth
    for i in range(len(line_chart_data)):
        plt.text(line_chart_data['Tanggal'].dt.strftime('%d %B')[i], 
                 line_chart_data['Growth 2024-2025'][i], 
                 str(line_chart_data['Growth 2024-2025'][i]), 
                 ha='center', va='bottom', fontsize=8)

    plt.xlabel("Tanggal")
    plt.ylabel("Growth (%)")
    plt.axhline(0, color='black', linestyle='--')  # Menambahkan garis horizontal di 0%
    plt.xticks(rotation=45)
    plt.legend()

    st.pyplot(plt)