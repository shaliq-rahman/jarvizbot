# How to Fix Supabase Connection for Streamlit Cloud

## Problem
The direct Supabase connection (`db.yzkbleuhvrhjabrpwlow.supabase.co`) doesn't work in Streamlit Cloud due to IPv6 connectivity issues.

## Solution: Use Supabase Connection Pooler

### Step 1: Get Pooler Connection String

1. Go to your **Supabase Dashboard**: https://supabase.com/dashboard
2. Select your project
3. Click **Settings** (gear icon) → **Database**
4. Scroll down to **"Connection string"** section
5. Select **"Session pooler"** mode (recommended for web apps)
6. Copy the connection string

The connection string will look like:
```
postgresql://postgres.yzkbleuhvrhjabrpwlow:[YOUR_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Step 2: Extract Connection Details

From the connection string, extract:
- **Host**: `aws-0-us-east-1.pooler.supabase.com` (the part after `@` and before `:6543`)
- **Port**: `6543` (for Session pooler) or `5432` (for Transaction pooler)
- **User**: `postgres.yzkbleuhvrhjabrpwlow` (the part before `:` in the user section)
- **Password**: Your database password
- **Database**: `postgres` (usually)

### Step 3: Update Environment Variables

#### For Local Development (.env file):
Update your `.env` file in the `expense-tracker-bot` directory:

```env
PGHOST=aws-0-us-east-1.pooler.supabase.com
PGPORT=6543
PGDATABASE=postgres
PGUSER=postgres.yzkbleuhvrhjabrpwlow
PGPASSWORD=K14gKTz1NyHcrsFx
PGSSLMODE=require
```

**Note**: Replace `aws-0-us-east-1` with your actual region from the pooler URL.

#### For Streamlit Cloud:
1. Go to your Streamlit Cloud app settings
2. Click **"Secrets"** or **"Environment variables"**
3. Add/update these variables:
   - `PGHOST=aws-0-us-east-1.pooler.supabase.com`
   - `PGPORT=6543`
   - `PGDATABASE=postgres`
   - `PGUSER=postgres.yzkbleuhvrhjabrpwlow`
   - `PGPASSWORD=K14gKTz1NyHcrsFx`
   - `PGSSLMODE=require`

### Step 4: Test Connection

After updating, restart your Streamlit app. The connection should work!

## Why Pooler Works Better

- ✅ Designed for serverless/web applications
- ✅ Better connection management
- ✅ More reliable for external connections
- ✅ Handles IPv4/IPv6 better
- ✅ Optimized for short-lived connections

## Troubleshooting

If you still have issues:
1. Make sure you're using **Session pooler** (port 6543), not Transaction pooler
2. Verify your password is correct
3. Check that your Supabase project allows external connections
4. Ensure SSL mode is set to `require`

