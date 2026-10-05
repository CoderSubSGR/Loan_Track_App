import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

EMI_CATEGORIES = [
    "Monthly EMI", "Additional Amount"
]

DISBURSEMENT_CATEGORIES = [
    "Payment"
]

spreadsheet_url = None
if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
    spreadsheet_url = st.secrets["connections"]["gsheets"].get("spreadsheet")

def load_database():
    df_emi = pd.DataFrame(columns=["Date", "Month-Year", "Remarks", "EMI Category", "Amount"])
    df_dis = pd.DataFrame(columns=["Date", "Month-Year", "Remarks",  "Amount"])

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            df_emi = conn.read(worksheet="EMI", ttl="0d")
            if df_emi.empty or "Amount" not in df_emi.columns:
                df_emi = pd.DataFrame(columns=["Date", "Month-Year", "EMI Remarks", "EMI Category", "Amount"])
        except: pass
        try:
            df_dis = conn.read(worksheet="Payment", ttl="0d")
            if df_dis.empty or "Amount" not in df_dis.columns:
                dfdf_dis_inc = pd.DataFrame(columns=["Date", "Month-Year", "Disbursement Remarks", "Disbursement Category" "Amount"])
        except: pass
        return df_emi, df_dis, True
    except:
        return df_emi, df_dis, False

def save_database(df_emi, df_dis):
    if not spreadsheet_url: return False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="EMI", data=df_emi)
        conn.update(worksheet="Payment", data=df_dis)
        return True
    except: return False

st.set_page_config(page_title="Loan EMI Tracker Console", page_icon="📉", layout="wide")
df_emi, df_dis, connection_status = load_database()

st.sidebar.title("🛠️ Control Console")
if not connection_status:
    st.sidebar.error("⚠️ Google Spreadsheet secret missing or invalid.")
else:
    st.sidebar.success("🔗 Connected to Live Google Sheet database.")

menu_choice = st.sidebar.selectbox("Choose Operation Mode", ["Log New Transaction", "Undo Last Record"])

if menu_choice == "Log New Transaction":
    st.sidebar.subheader("📝 Transaction Input")
    tx_type = st.sidebar.radio("Transaction Type", ["EMI 💸", "Payment 💰"])
    with st.sidebar.form("transaction_form", clear_on_submit=True):
        selected_date = st.date_input("Date", datetime.today())
        month_year_str = selected_date.strftime("%B %Y")
        entity_label = "EMI Remarks" if "EMI" in tx_type else "Remarks"
        entity_name = st.text_input(entity_label)
        cats_list = EMI_CATEGORIES if "EMI" in tx_type else DISBURSEMENT_CATEGORIES
        selected_cat = st.selectbox("Category", cats_list)
        amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0, format="%.2f")

        submitted = st.form_submit_button("Save Entry")
        if submitted:
            if not connection_status: st.sidebar.error("Offline")
            elif not entity_name.strip(): st.sidebar.error("Blank Name")
            elif amount <= 0: st.sidebar.error("Invalid Amount")
            else:
                date_str = selected_date.strftime("%Y-%m-%d")
                if "EMI" in tx_type:
                    new_row = {"Date": date_str, "Month-Year": month_year_str, "EMI Remarks": entity_name, "EMI Category": selected_cat, "Amount": amount}
                    df_emi = pd.concat([df_emi, pd.DataFrame([new_row])], ignore_index=True)
                else:
                    new_row = {"Date": date_str, "Month-Year": month_year_str, "Disbursement Remarks": entity_name, "Disbursement Category": selected_cat, 
                               "Amount": amount}
                    df_dis = pd.concat([df_dis, pd.DataFrame([new_row])], ignore_index=True)
                if save_database(df_emi, df_dis):
                    st.sidebar.success("Recorded entry!")
                    st.rerun()

elif menu_choice == "Undo Last Record":
    st.sidebar.subheader("⚠️ Ledger Maintenance")
    del_target = st.sidebar.radio("Target Ledger Sheet", ["EMI Ledger", "Payment Ledger"])
    if st.sidebar.button("🗑️ Delete Most Recent Entry"):
        if not connection_status: st.sidebar.error("Offline")
        elif del_target == "EMI Ledger" and not df_emi.empty:
            df_emi = df_emi.drop(df_emi.index[-1])
            save_database(df_emi, df_dis)
            st.rerun()
        elif del_target == "Payment Ledger" and not df_dis.empty:
            df_dis = df_dis.drop(df_dis.index[-1])
            save_database(df_emi, df_dis)
            st.rerun()

def calculate_loan_balance():
    print("--- Loan & EMI Calculator ---")
    
    # User Inputs
    principal = float(input("Enter the Loan Amount: "))
    annual_rate = float(input("Enter the Annual Interest Rate (%): "))
    tenure_years = int(input("Enter the Total Loan Tenure (in years): "))
    months_paid = int(input("Enter the number of EMIs already paid: "))
    
    # Conversions
    monthly_rate = (annual_rate / 100) / 12
    total_months = tenure_years * 12
    
    # 1. Calculate Monthly EMI using standard formula
    # EMI = [P x R x (1+R)^N] / [(1+R)^N - 1]
    if monthly_rate > 0:
        emi = (principal * monthly_rate * (1 + monthly_rate) ** total_months) / ((1 + monthly_rate) ** total_months - 1)
    else:
        emi = principal / total_months  # 0% interest fallback
        
    # 2. Calculate Total Repayment and Total Interest
    total_payment = emi * total_months
    total_interest = total_payment - principal
    
    # 3. Calculate Accumulated EMI paid so far
    accumulated_emi = emi * months_paid
    
    # 4. Your custom requested logic: Loan Amount + Total Interest - Accumulated EMI
    # Note: (Principal + Total Interest) equals the absolute Total Payment required.
    custom_balance = (principal + total_interest) - accumulated_emi
    
    # Outputs
    print("\n--- Results ---")
    print(f"Monthly EMI:                 {emi:.2f}")
    print(f"Total Interest Payable:      {total_interest:.2f}")
    print(f"Total Amount (Principal+Int): {principal + total_interest:.2f}")
    print(f"Accumulated EMI Paid ({months_paid} mos): {accumulated_emi:.2f}")
    print(f"Remaining Balance Formula:    {custom_balance:.2f}")

st.title("🌟 Loan Tracker Dashboard 🌟")
total_emi = df_emi["Amount"].sum() if not df_emi.empty else 0.0
total_dis = df_dis["Amount"].sum() if not df_dis.empty else 0.0
net_balance = (total_dis + (.19334 * total_dis)) - total_emi

m1, m2, m3 = st.columns(3)
m1.metric("Disbursed Amount", f"₹{total_dis:,.2f}")
m2.metric("EMIs Paid so far", f"₹{total_emi:,.2f}")
m3.metric("Remaining Balance Amount", f"₹{net_balance:,.2f}")

st.markdown("---")
tab1, tab2 = st.tabs(["🗂️ EMI Ledger", "📥 Payment Ledger"])
with tab1: st.dataframe(df_emi, use_container_width=True)
with tab2: st.dataframe(df_dis, use_container_width=True)
