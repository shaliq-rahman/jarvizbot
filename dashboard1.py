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
    import ipaddress
    
    host_ip = PGHOST
    try:
        # Get all address info and filter for IPv4 only
        addr_info_list = socket.getaddrinfo(PGHOST, PGPORT, socket.AF_INET, socket.SOCK_STREAM)
        if addr_info_list:
            # Get the first IPv4 address
            for addr_info in addr_info_list:
                if addr_info[0] == socket.AF_INET:  # Ensure it's IPv4
                    host_ip = addr_info[4][0]
                    # Verify it's actually an IPv4 address
                    try:
                        ipaddress.IPv4Address(host_ip)
                        break
                    except ValueError:
                        continue
    except (socket.gaierror, OSError, ValueError):
        # If resolution fails, try using the hostname with IPv4 socket option
        pass
    
    # Build connection parameters
    # Use connection string format which gives more control
    conn_string = f"host={host_ip} port={PGPORT} dbname={PGDATABASE} user={PGUSER} password={PGPASSWORD} connect_timeout=10"
    if PGSSLMODE:
        conn_string += f" sslmode={PGSSLMODE}"
    
    # Try to connect with IPv4 preference
    try:
        return psycopg2.connect(conn_string)
    except psycopg2.OperationalError as e:
        # If direct connection fails, suggest using pooler
        error_msg = str(e)
        if "IPv6" in error_msg or "Cannot assign requested address" in error_msg:
            # Try to construct pooler URL as fallback
            # Supabase pooler format: aws-0-[region].pooler.supabase.com
            if "supabase.co" in PGHOST:
                # Extract region/project info and suggest pooler
                st.warning("⚠️ Direct connection failed. Please use Supabase Connection Pooler instead.")
                st.info("""
                **To fix this:**
                1. Go to Supabase Dashboard → Settings → Database
                2. Scroll to "Connection string" section
                3. Select **"Session pooler"** mode
                4. Copy the connection string
                5. Extract the host (e.g., `aws-0-us-east-1.pooler.supabase.com`)
                6. Update your `.env` file:
                   - `PGHOST=aws-0-[region].pooler.supabase.com`
                   - `PGPORT=6543` (for Session pooler)
                """)
        raise

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
