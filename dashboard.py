# dashboard_live.py — Streamlit auto-refresh with PostgreSQL
import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import date

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

st.set_page_config(layout="wide")
st.title("Expense Dashboard (Live)")

st.subheader("DB diagnostics")
st.write("Database:", PGDATABASE)
st.write("Host:", PGHOST)

@st.cache_data(ttl=5)  # Cache for 5 seconds to allow refresh
def load_data():
    """
    Load data from PostgreSQL database.
    Cache refreshes every 5 seconds or when manually cleared.
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if not df.empty and 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        return df
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "IPv6" in error_msg or "Cannot assign requested address" in error_msg:
            st.error(f"Connection error (IPv6 issue): {error_msg}")
            st.info("💡 Tip: If using Supabase, try using the connection pooler URL instead of the direct connection URL. Check your Supabase dashboard > Settings > Database > Connection string > Session pooler")
        else:
            st.error(f"Database connection error: {error_msg}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading database: {e}")
        return pd.DataFrame()

df = load_data()

st.markdown("---")
if df.empty:
    st.info("No transactions loaded from database. If the bot is writing data, check database connection.")
else:
    st.success(f"Loaded {len(df)} rows from database.")

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
            load_data.clear()
            st.rerun()

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
