import streamlit as st
import pandas as pd
import pymysql
import re

# Konfigurasi halaman
st.set_page_config(
    page_title="Upload File",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="auto",
)

# Template nama file dan mapping kolom
required_files = ["WARE", "WARR", "WARW", "WARC", "WARD", "WADY", "WARA", "WART"]
file_template = r"\(Data Movement Cabang (\w+)\) .+\.(xls|xlsx)"
column_mapping = [
    "TANGGAL", "ACID", "A_REG", "A_TYPE", "ADEP", "ADES", "EOBT", "PUSHBACK", "TAXI",
    "DEP_ARR_LOCAL", "ATD", "ETA", "ATA", "RIU", "POB", "REMARK", "STATUS_FLIGHT"
]

st.title("Halaman Upload File")

# Fungsi untuk mendapatkan koneksi database MySQL
def get_db_connection():
    try:
        secrets = st.secrets["mysql"]
        conn = pymysql.connect(
            host=secrets["host"],
            user=secrets["username"],
            password=secrets["password"],
            database=secrets["database"],
            port=secrets["port"]
        )
        return conn
    except pymysql.MySQLError as e:
        st.error(f"Koneksi MySQL gagal: {e}")
        return None

# Fungsi untuk membaca file Excel
@st.cache_data
def read_excel_file(uploaded_file):
    try:
        data = pd.read_excel(uploaded_file, skiprows=6, engine="openpyxl", header=None)
        data = data.iloc[:, 1:]  # Hapus kolom pertama
        if len(data.columns) != len(column_mapping):
            raise ValueError(
                f"Jumlah kolom di file Excel ({len(data.columns)}) tidak sesuai dengan yang diharapkan ({len(column_mapping)})."
            )
        data.columns = column_mapping
        return data
    except Exception as e:
        raise ValueError(f"Kesalahan saat membaca file Excel: {e}")

# Fungsi untuk membersihkan dan menyesuaikan data
def clean_data(data):
    # Konversi kolom `TANGGAL` ke format DATE
    if "TANGGAL" in data.columns:
        data["TANGGAL"] = pd.to_datetime(data["TANGGAL"], errors="coerce").dt.date

    # # Pastikan kolom waktu dalam format `HH:MM:SS`
    # time_columns = ["EOBT", "PUSHBACK", "TAXI", "ATD", "ETA", "ATA"]
    # for col in time_columns:
    #     if col in data.columns:
    #         data[col] = pd.to_datetime(data[col], format="%H:%M:%S", errors="coerce").dt.time

    # Ganti semua NaN dengan None untuk MySQL
    data = data.where(pd.notnull(data), None)

    # Pastikan semua nilai diubah menjadi tipe Python-native
    for col in data.columns:
        if data[col].dtype == "float64":
            data[col] = data[col].astype(object).where(pd.notnull(data[col]), None)
        elif data[col].dtype == "int64":
            data[col] = data[col].astype(object).where(pd.notnull(data[col]), None)
        elif data[col].dtype == "datetime64[ns]":
            data[col] = data[col].astype(str).where(pd.notnull(data[col]), None)
        else:
            data[col] = data[col].where(pd.notnull(data[col]), None)
    return data

# Fungsi untuk menyimpan data ke MySQL
def insert_data(conn, table_name, data):
    try:
        placeholders = ", ".join(["%s" for _ in data.columns])
        query = f"INSERT INTO {table_name} ({', '.join(data.columns)}) VALUES ({placeholders})"

        values = [tuple(row) for row in data.itertuples(index=False, name=None)]

        with conn.cursor() as cursor:
            cursor.executemany(query, values)
        conn.commit()
    except pymysql.MySQLError as e:
        raise ValueError(f"Kesalahan saat menyimpan ke database: {e}")

# Loop untuk memproses file yang diunggah
for file_key in required_files:
    uploaded_file = st.file_uploader(f"Unggah file '{file_key}'", type=["xlsx", "xls"], key=file_key)
    
    if uploaded_file is not None:
        try:
            match = re.match(file_template, uploaded_file.name)
            if not match:
                st.error(f"Nama file '{uploaded_file.name}' tidak sesuai template.")
                continue

            cabang_name = match.group(1)
            if cabang_name != file_key:
                st.error(f"File '{uploaded_file.name}' bukan untuk cabang {file_key}. Harap unggah file yang sesuai.")
                continue

            data = read_excel_file(uploaded_file)
            data = clean_data(data)

            with get_db_connection() as conn:
                if conn:
                    try:
                        insert_data(conn, "flights", data)
                        st.success(f"Data untuk cabang {file_key} berhasil disimpan ke database!")
                    except Exception as e:
                        st.error(f"Kesalahan saat menyimpan ke database: {e}")
        except ValueError as ve:
            st.error(f"Kesalahan saat memproses file {uploaded_file.name}: {ve}")
        except Exception as e:
            st.error(f"Kesalahan tak terduga: {e}")
    else:
        st.info(f"File {file_key} belum diunggah.")