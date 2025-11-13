import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime, date

# Load .env file if it exists
def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)

# Load .env file
load_env_file()

# Database connection parameters
PGHOST = os.getenv("PGHOST")
PGPORT = int(os.getenv("PGPORT", "5432"))
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGSSLMODE = os.getenv("PGSSLMODE", "require")

def get_db_connection():
    """Get a PostgreSQL database connection with IPv4 and connection timeout."""
    if not all([PGHOST, PGDATABASE, PGUSER, PGPASSWORD]):
        raise ValueError(
            "Please set PGHOST, PGDATABASE, PGUSER, PGPASSWORD environment variables. "
            "Create a .env file or set them as environment variables."
        )
    
    # Force IPv4 by resolving hostname to IPv4 address only
    import socket
    try:
        # Get IPv4 address only (AF_INET = IPv4)
        addr_info = socket.getaddrinfo(PGHOST, PGPORT, socket.AF_INET, socket.SOCK_STREAM)
        if addr_info:
            host_ip = addr_info[0][4][0]  # Get the IPv4 address
        else:
            host_ip = PGHOST
    except (socket.gaierror, OSError):
        # If resolution fails, use hostname directly
        host_ip = PGHOST
    
    # Build connection parameters
    conn_params = {
        'host': host_ip,
        'port': PGPORT,
        'dbname': PGDATABASE,
        'user': PGUSER,
        'password': PGPASSWORD,
        'connect_timeout': 10,
        'sslmode': PGSSLMODE if PGSSLMODE else 'require'
    }
    
    return psycopg2.connect(**conn_params)

@st.cache_data(ttl=5)  # Cache for 5 seconds
def load_data():
    """Load data from PostgreSQL database."""
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
        conn.close()
        # Convert date columns to datetime
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if not df.empty and 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error reading database: {e}")
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
