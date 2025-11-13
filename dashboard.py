# dashboard_live.py — Streamlit auto-refresh when DB file changes
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import date

# Absolute path to DB in same folder as this file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, "expenses.db")

st.set_page_config(layout="wide")
st.title("Expense Dashboard (Live)")

st.subheader("DB diagnostics")
st.write("DB file path:", DB)
exists = os.path.exists(DB)
st.write("Exists:", exists)
if exists:
    st.write("Size (bytes):", os.path.getsize(DB))
    st.write("Last modified (timestamp):", os.path.getmtime(DB))
else:
    st.warning("Database file not found. Make sure bot writes to this folder or update DB path.")

def db_mtime(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0

@st.cache_data
def load_data_with_mtime(db_path, mtime):
    """
    Cache keyed by (db_path, mtime). When file mtime changes,
    Streamlit will call this function again and return fresh data.
    """
    if not os.path.exists(db_path):
        return pd.DataFrame()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    try:
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
    except Exception as e:
        st.error(f"Error reading DB: {e}")
        df = pd.DataFrame()
    conn.close()
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if not df.empty and 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    return df

# Pass the current DB mtime as parameter to the cached loader
current_mtime = db_mtime(DB)
df = load_data_with_mtime(DB, current_mtime)

st.markdown("---")
if df.empty:
    st.info("No transactions loaded from DB (empty DataFrame). If the bot is writing data, check DB path.")
else:
    st.success(f"Loaded {len(df)} rows from DB (mtime: {current_mtime}).")

st.subheader("Last 10 rows (raw)")
if df.empty:
    st.write("No rows to show.")
else:
    st.dataframe(df.head(10))

if not df.empty:
    st.sidebar.header("Filters")
    categories_all = sorted(df['category'].dropna().unique())
    categories = st.sidebar.multiselect("Category", options=categories_all, default=categories_all)

    date_min = df['date'].min()
    date_max = df['date'].max()
    if pd.notna(date_min) and pd.notna(date_max):
        date_from = st.sidebar.date_input("From", value=date_min.date())
        date_to = st.sidebar.date_input("To", value=date_max.date())
    else:
        date_from = st.sidebar.date_input("From", value=date.today())
        date_to = st.sidebar.date_input("To", value=date.today())

    filtered = df[df['category'].isin(categories)]
    filtered = filtered[(filtered['date'] >= pd.to_datetime(date_from)) & (filtered['date'] <= pd.to_datetime(date_to))]

    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("Refresh now"):
            # Force reload by clearing the cache entry and rerun
            load_data_with_mtime.clear()
            st.experimental_rerun()

    st.subheader("Transactions")
    st.dataframe(filtered[['date','category','amount','description']].sort_values('date', ascending=False), height=400)

    st.subheader("Summary by Category")
    summary = filtered.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)
    st.table(summary)

    st.subheader("Time series (daily totals)")
    daily = filtered.groupby(filtered['date'].dt.date)['amount'].sum().reset_index()
    if not daily.empty:
        daily.columns = ['date', 'amount']
        st.line_chart(data=daily.set_index('date')['amount'])

    st.download_button("Export CSV", filtered.to_csv(index=False), file_name="filtered_expenses.csv")
