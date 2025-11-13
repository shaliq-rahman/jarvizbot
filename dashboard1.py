import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

DB = "expenses.db"

def init_db():
    """Initialize the database and create the transactions table if it doesn't exist."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      category TEXT NOT NULL,
      amount REAL NOT NULL,
      currency TEXT DEFAULT 'INR',
      date TEXT NOT NULL,
      description TEXT,
      tags TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );
    ''')
    conn.commit()
    conn.close()

@st.cache_data
def load_data():
    # Initialize database if needed
    init_db()
    try:
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
        conn.close()
        # Convert date columns to datetime
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if not df.empty and 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        return df
    except (sqlite3.OperationalError, pd.errors.DatabaseError) as e:
        # Table doesn't exist or other database error
        return pd.DataFrame()

st.title("Expense Dashboard")
df = load_data()

if df.empty:
    st.info("No transactions yet. Add via your Telegram bot.")
else:
    st.sidebar.header("Filters")
    categories = st.sidebar.multiselect("Category", options=sorted(df['category'].dropna().unique()), default=sorted(df['category'].dropna().unique()))
    # Handle date inputs safely
    date_min = df['date'].min()
    date_max = df['date'].max()
    if pd.notna(date_min) and pd.notna(date_max):
        # Convert Timestamp to date if needed
        if isinstance(date_min, pd.Timestamp):
            date_from = st.sidebar.date_input("From", value=date_min.date())
        else:
            date_from = st.sidebar.date_input("From", value=date_min)
        if isinstance(date_max, pd.Timestamp):
            date_to = st.sidebar.date_input("To", value=date_max.date())
        else:
            date_to = st.sidebar.date_input("To", value=date_max)
    else:
        date_from = st.sidebar.date_input("From", value=date.today())
        date_to = st.sidebar.date_input("To", value=date.today())
    filtered = df[df['category'].isin(categories)]
    filtered = filtered[(filtered['date'] >= pd.to_datetime(date_from)) & (filtered['date'] <= pd.to_datetime(date_to))]
    st.subheader("Transactions")
    st.dataframe(filtered[['date','category','amount','description']].sort_values('date', ascending=False))

    st.subheader("Summary by Category")
    summary = filtered.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)
    st.table(summary)

    st.subheader("Time series (daily totals)")
    daily = filtered.groupby('date')['amount'].sum().reset_index()
    st.line_chart(daily.rename(columns={'date':'index'}).set_index('index')['amount'])

    st.download_button("Export CSV", filtered.to_csv(index=False), file_name="filtered_expenses.csv")
 