import streamlit as st
from streamlit_option_menu import option_menu
import requests
import datetime
import pandas as pd
import altair as alt

# Sidebar Navigation
with st.sidebar:
    selected = option_menu("LEAD Accounting", ["Sales Report", "Receivables / Payables", "Send Reminders"],
                           icons=['bar-chart', 'currency-exchange', 'send'],
                           menu_icon="cast", default_index=0)

# Shared Config
BASE_URL = "https://lytmart-a2dqaebzh8edfqez.centralindia-01.azurewebsites.net"
OID = "8"
SID = "1179"

# Helper function
def post_api(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    response = requests.post(url, json=payload)
    return response.json()

import streamlit as st
import datetime

#page1
# page1
if selected == "Sales Report":
    st.title("📊 Sales Report")

    # Row 1: Dates
    col1, col2 = st.columns(2)
    from_date = col1.date_input("From Date", datetime.date(2025, 2, 22))
    to_date = col2.date_input("To Date", datetime.date(2025, 2, 23))

    # Row 2: Salesman, Account, Location
    col3, col4, col5 = st.columns(3)

    # Salesman Filter
    salesman_data = post_api("/api/getrows", {
        "oid": OID, "sid": SID, "type": "salesman", "name": "", "maxrows": "50"
    })
    salesman_list = {s['name']: s['id'] for s in salesman_data['items']}
    selected_salesman = col3.selectbox("Salesman", ["All"] + list(salesman_list.keys()))

    # Account Filter
    customer_data = post_api("/api/getrows", {
        "oid": OID, "sid": SID, "type": "customer", "name": "", "maxrows": "50"
    })
    account_list = {c['name']: c['id'] for c in customer_data['items']}
    selected_account = col4.selectbox("Account", ["All"] + list(account_list.keys()))

    # Location Filter
    location_data = post_api("/api/getrows", {
        "oid": OID, "sid": SID, "type": "location", "name": "", "maxrows": "50"
    })
    location_list = {l['name']: l['id'] for l in location_data['items']}
    selected_location = col5.selectbox("Location", ["All"] + list(location_list.keys()))

    if st.button("Get Report"):
        payload = {
            "oid": OID,
            "sid": SID,
            "from": from_date.strftime('%Y-%m-%d'),
            "to": to_date.strftime('%Y-%m-%d'),
            "location": location_list.get(selected_location, "0") if selected_location != "All" else "0",
            "document": "7",
            "account": account_list.get(selected_account, "0") if selected_account != "All" else "0",
            "salesman": salesman_list.get(selected_salesman, "0") if selected_salesman != "All" else "0",
            "subaccount": "0",
            "route": "0",
            "ordertoken": "",
            "maxrows": "1000000000"
        }

        result = post_api("/api/getinvorord", payload)


        if result['status'] == "success":
            lines = result.get('lines', [])
            total_sales = sum(float(row['amount']) for row in lines)
            total_invoices = len(lines)

            # Convert to DataFrame
            df = pd.DataFrame(lines)

            # Convert and format date column
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], dayfirst=True)  # 👈 tells pandas it's dd-mm-yyyy
                df['month'] = df['date'].dt.to_period("M").astype(str)
                df['date'] = df['date'].dt.strftime('%d-%m-%Y')

                # Ensure 'amount' is numeric and clean
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).round(2)

                # 📊 Month-wise Sales Chart
                monthly_sales = df.groupby('month')['amount'].sum().round(2).sort_index()
                st.subheader("📈 Month-wise Sales Chart")
                st.bar_chart(monthly_sales)

            # 🎯 Metrics Cards
            card_style = """
                <style>
                .metric-card {
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    margin-bottom: 10px;
                }
                .metric-header {
                    font-size: 18px;
                    color: #444;
                    margin-bottom: 8px;
                }
                .metric-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #2e7d32;
                }
                </style>
            """
            st.markdown(card_style, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-header">Total Sales</div>
                    <div class="metric-value">₹ {total_sales:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-header">Total Invoices</div>
                    <div class="metric-value">{total_invoices}</div>
                </div>
                """, unsafe_allow_html=True)

            st.success(f"Found {total_invoices} record(s)")
            st.dataframe(df[["date", "location", "account", "subaccount", "name", "salesman", "route", "amount", "state", "country", "tin"]])
        else:
            st.error("Failed to fetch data.")



#page2
elif selected == "Receivables / Payables":
    st.title("💰 Receivables / Payables Report")
    
    bill_type = st.radio("Select Bill Type", ["Receivables", "Payables"])
    is_receivable = bill_type == "Receivables"
    btype = "R" if is_receivable else "P"

    report_lines = []

    # Fetch accounts based on type
    account_type = "customer" if is_receivable else "vendor"
    accounts = post_api("/api/getrows", {
        "oid": OID, "sid": SID, "type": account_type, "name": "", "maxrows": "100"
    })

    for acc in accounts['items']:
        payload = {
            "oid": OID,
            "sid": SID,
            "billtype": btype,
            "account": acc['id'],
            "salesman": "0",
            "route": "0",
            "maxrows": "99999999999999999999"
        }
        data = post_api("/api/getbills", payload)
        if data.get("lines"):
            report_lines.extend(data['lines'])

    # Calculate total balance
    total_balance = sum(float(line.get('balance', 0)) for line in report_lines)

    # Styled card for total balance
    st.markdown("""
        <style>
        .metric-card {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.07);
            text-align: center;
            margin-bottom: 20px;
        }
        .metric-header {
            font-size: 18px;
            color: #444;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 26px;
            font-weight: bold;
            color: #1c6f57;
        }
        </style>
    """, unsafe_allow_html=True)

    col1 = st.columns(1)[0]
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-header">Total {bill_type} Balance</div>
            <div class="metric-value">₹ {total_balance:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.success(f"Found {len(report_lines)} entries")
    st.dataframe(report_lines)


# Page 3: WhatsApp Reminders
elif selected == "Send Reminders":
    st.title("📲 Send WhatsApp Reminders")

    st.info("This will scan pending receivables/payables and send WhatsApp messages.")
    
    bill_type = st.radio("Remind For", ["Receivables", "Payables"])
    btype = "R" if bill_type == "Receivables" else "P"

    # Assuming your WhatsApp API or message logic is handled separately
    if st.button("Send Reminders"):
        # Loop through accounts again like Page 2
        accounts = post_api("/api/getrows", {
            "oid": OID, "sid": SID, "type": "customer" if btype == "R" else "vendor", "name": "", "maxrows": "100"
        })
        reminders_sent = 0
        for acc in accounts['items']:
            bills = post_api("/api/getbills", {
                "oid": OID,
                "sid": SID,
                "billtype": btype,
                "account": acc['id'],
                "salesman": "0",
                "route": "0",
                "maxrows": "15"
            })
            for bill in bills.get("lines", []):
                # Call your WhatsApp API here with `bill["mobile"]` and message
                # Example:
                # send_whatsapp(bill["mobile"], f"Reminder: ₹{bill['balance']} due on {bill['duedate']}")
                reminders_sent += 1

        st.success(f"✅ Sent {reminders_sent} reminders")

