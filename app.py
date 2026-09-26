import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os

st.set_page_config(page_title="Smart Budget Tracker", layout="wide")

# --- FILES SETUP ---
USERS_FILE = "users.csv"
BUDGET_FILE = "budgets.csv"
TRANSACTIONS_FILE = "transactions.csv"

def init_files():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["Username", "Password"]).to_csv(USERS_FILE, index=False)
    if not os.path.exists(BUDGET_FILE):
        pd.DataFrame(columns=["Username", "Month", "Category", "Base_Budget", "Carry_Forward"]).to_csv(BUDGET_FILE, index=False)
    if not os.path.exists(TRANSACTIONS_FILE):
        pd.DataFrame(columns=["Username", "Date", "Month", "Category", "Amount"]).to_csv(TRANSACTIONS_FILE, index=False)

init_files()

# --- LOGIN & REGISTRATION SYSTEM ---
if 'logged_in_user' not in st.session_state:
    st.title("🔐 Smart Budget - Login")
    tab1, tab2 = st.tabs(["Login", "Create New Account"])
    users_df = pd.read_csv(USERS_FILE)
    
    with tab1:
        l_user = st.text_input("Username / Mobile No.", key="l_user")
        l_pass = st.text_input("PIN / Password", type="password", key="l_pass")
        if st.button("Login"):
            if l_user in users_df['Username'].values:
                actual_pass = str(users_df[users_df['Username'] == l_user]['Password'].values[0])
                if str(l_pass) == actual_pass:
                    st.session_state.logged_in_user = l_user
                    st.rerun()
                else:
                    st.error("Incorrect PIN!")
            else:
                st.error("User not found! Please create an account first.")
                
    with tab2:
        r_user = st.text_input("New Username / Mobile No.", key="r_user")
        r_pass = st.text_input("New PIN / Password", type="password", key="r_pass")
        if st.button("Register"):
            if r_user in users_df['Username'].values:
                st.error("Username already exists.")
            elif r_user and r_pass:
                new_user = pd.DataFrame([{"Username": r_user, "Password": r_pass}])
                new_user.to_csv(USERS_FILE, mode='a', header=False, index=False)
                st.success("Account created successfully! You can now log in.")
            else:
                st.error("Please fill in all details.")
    st.stop()

# --- MAIN APP (Logged In) ---
current_user = st.session_state.logged_in_user
st.sidebar.success(f"👤 Welcome, {current_user}!")
if st.sidebar.button("Logout"):
    del st.session_state.logged_in_user
    st.rerun()

st.title("📊 Smart Expense Dashboard")

# Load User Data
all_budgets = pd.read_csv(BUDGET_FILE)
all_trans = pd.read_csv(TRANSACTIONS_FILE)

user_budgets = all_budgets[all_budgets['Username'] == current_user]
user_trans = all_trans[all_trans['Username'] == current_user]

# Month Selection
current_month_str = datetime.now().strftime("%Y-%m")
all_months = list(user_budgets['Month'].unique())
if current_month_str not in all_months:
    all_months.append(current_month_str)
all_months.sort(reverse=True)

st.sidebar.divider()
selected_month = st.sidebar.selectbox("📅 Select Month", all_months, index=0)

month_budgets = user_budgets[user_budgets['Month'] == selected_month]
month_trans = user_trans[user_trans['Month'] == selected_month]

# --- ADD CATEGORY ---
st.sidebar.header("⚙️ Add New Category")
with st.sidebar.form("add_cat_form"):
    new_cat = st.text_input("Category Name")
    new_budget = st.number_input("Monthly Budget (₹)", min_value=0, step=500)
    if st.form_submit_button("Add Category"):
        if new_cat:
            new_b = pd.DataFrame([{"Username": current_user, "Month": selected_month, "Category": new_cat, "Base_Budget": new_budget, "Carry_Forward": 0}])
            new_b.to_csv(BUDGET_FILE, mode='a', header=False, index=False)
            st.rerun()

# --- ADD EXPENSE ---
st.sidebar.header("📝 Add Daily Expense")
cat_list = list(month_budgets['Category'].unique())
with st.sidebar.form("add_exp_form"):
    date_val = st.date_input("Date", datetime.now())
    if len(cat_list) > 0:
        sel_cat = st.selectbox("Category", cat_list)
        amount_val = st.number_input("Amount (₹)", min_value=0, step=10)
        if st.form_submit_button("Add Expense"):
            new_t = pd.DataFrame([{"Username": current_user, "Date": date_val.strftime("%Y-%m-%d"), "Month": date_val.strftime("%Y-%m"), "Category": sel_cat, "Amount": amount_val}])
            new_t.to_csv(TRANSACTIONS_FILE, mode='a', header=False, index=False)
            st.rerun()
    else:
        st.warning("Please create a category first.")
        st.form_submit_button("Add Expense", disabled=True)

# --- DASHBOARD CALCULATION ---
if not month_budgets.empty:
    spent_summary = month_trans.groupby("Category")["Amount"].sum().reset_index() if not month_trans.empty else pd.DataFrame(columns=["Category", "Amount"])
    
    summary_df = pd.merge(month_budgets, spent_summary, on="Category", how="left").fillna(0)
    summary_df.rename(columns={"Amount": "Spent"}, inplace=True)
    summary_df["Total_Budget"] = summary_df["Base_Budget"] + summary_df["Carry_Forward"]
    summary_df["Remaining"] = summary_df["Total_Budget"] - summary_df["Spent"]
    
    # Smart Pacing
    now = datetime.now()
    if selected_month == current_month_str:
        total_days = calendar.monthrange(now.year, now.month)[1]
        rem_days = max(1, total_days - now.day)
    else:
        rem_days = 1 
        
    summary_df["Daily Limit"] = summary_df["Remaining"].apply(lambda x: x / rem_days if x > 0 else 0)

    # Display Metrics
    total_b = summary_df["Total_Budget"].sum()
    total_s = summary_df["Spent"].sum()
    total_r = total_b - total_s

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Monthly Budget", f"₹{total_b:,.0f}")
    col2.metric("Total Spent", f"₹{total_s:,.0f}")
    col3.metric("Total Remaining", f"₹{total_r:,.0f}")

    # Color Alert Logic
    def style_rows(row):
        if row['Remaining'] < 0: return ['background-color: #ffcccc'] * len(row)
        elif row['Remaining'] < (row['Total_Budget'] * 0.2): return ['background-color: #fff2cc'] * len(row)
        else: return ['background-color: #d9ead3'] * len(row)

    st.subheader(f"🎯 Category Status ({selected_month})")
    display_df = summary_df[["Category", "Base_Budget", "Carry_Forward", "Total_Budget", "Spent", "Remaining", "Daily Limit"]]
    styled_df = display_df.style.apply(style_rows, axis=1).format({"Base_Budget": "₹{:.0f}", "Carry_Forward": "₹{:.0f}", "Total_Budget": "₹{:.0f}", "Spent": "₹{:.0f}", "Remaining": "₹{:.0f}", "Daily Limit": "₹{:.0f}"})
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # --- CARRY FORWARD SYSTEM ---
    st.sidebar.divider()
    st.sidebar.subheader("⏩ Carry Forward")
    st.sidebar.info("Transfer remaining (or negative) balance to the next month.")
    if st.sidebar.button("Carry Forward to Next Month"):
        year, month = map(int, selected_month.split('-'))
        next_month_str = f"{year+1}-01" if month == 12 else f"{year}-{month+1:02d}"
        
        all_b = pd.read_csv(BUDGET_FILE)
        for _, row in summary_df.iterrows():
            cat = row['Category']
            rem = row['Remaining']
            base = row['Base_Budget']
            
            exists = all_b[(all_b['Username'] == current_user) & (all_b['Month'] == next_month_str) & (all_b['Category'] == cat)]
            if exists.empty:
                new_entry = pd.DataFrame([{"Username": current_user, "Month": next_month_str, "Category": cat, "Base_Budget": base, "Carry_Forward": rem}])
                new_entry.to_csv(BUDGET_FILE, mode='a', header=False, index=False)
        st.sidebar.success(f"Data transferred to {next_month_str}! Select the new month above.")
        
else:
    st.info("Please create a 'New Category' from the left menu.")