import streamlit as st
import pandas as pd
import requests
import re
from fpdf import FPDF
from datetime import date

# ==========================================
# --- SECURITY GATEKEEPER ---
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Moneyplan Secure Login")
    
    def password_entered():
        if st.session_state["entered_pin"] == st.secrets["admin_pin"]:
            st.session_state["password_correct"] = True
            del st.session_state["entered_pin"]
        else:
            st.session_state["password_correct"] = False

    st.text_input("Enter Admin PIN", type="password", on_change=password_entered, key="entered_pin")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("Incorrect PIN. Access Denied.")
        
    return False

if not check_password():
    st.stop()

# ==========================================
# --- PLATFORM BRANDING & LIVE DATA ---
# ==========================================
st.set_page_config(page_title="Moneyplan Suggestion Engine", layout="wide")
st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")

st.title("Intelligent Mutual Fund Suggestion Engine")

# --- FETCH ALL 40,000+ AMFI SCHEMES ---
@st.cache_data(ttl=86400)
def get_all_indian_mutual_funds():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", headers=headers, timeout=15)
        response.raise_for_status() 
        fund_dict = {}
        lines = response.text.split('\n')
        for line in lines:
            parts = line.split(';')
            if len(parts) >= 4 and parts[0].strip().isdigit():
                fund_dict[parts[3].strip()] = parts[0].strip()
        return dict(sorted(fund_dict.items()))
    except Exception as e:
        return {"Error: Cloud server blocked.": 0, "SBI Liquid Fund": 1, "Parag Parikh Flexi Cap Fund": 2}

with st.spinner("Syncing Live AMFI Database for Scheme Selection..."):
    all_funds_db = get_all_indian_mutual_funds()
    all_fund_names = list(all_funds_db.keys())

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs([
    "🎯 Tool 1: Goal & Profile Allocator", 
    "📈 Tool 2: Multi-AMC STP Configurator", 
    "📄 Tool 3: Final PDF Report"
])

# ==========================================
# TOOL 1: GOAL-BASED ALLOCATOR
# ==========================================
with tab1:
    st.markdown("### Client Profile & Requirement Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        client_name = st.text_input("Client Name", value="Client")
        client_age = st.number_input("Client Age", value=35, min_value=18, max_value=80)
        risk_profile = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"], index=1)
    with col2:
        investment_type = st.radio("Investment Mode", ["SIP", "Lumpsum", "Multi-AMC STP (HNI)"], index=2)
        invest_amount = st.number_input("Total Capital (₹)", value=2000000, step=100000)
    with col3:
        time_horizon = st.slider("Investment Horizon (Years)", 1, 30, 10)
        expected_return = st.number_input("Expected Return (%)", value=12.0, step=0.5)
        
        stp_duration = 0
        if investment_type == "Multi-AMC STP (HNI)":
            stp_duration = st.slider("STP Duration (Months)", 3, 36, 12, help="How long to spread the lumpsum into the market.")

    # Core Asset Allocation Math
    base_equity = 100 - client_age
    if risk_profile == "Aggressive": 
        base_equity += 15
    elif risk_profile == "Conservative": 
        base_equity -= 15
        
    if time_horizon < 3: 
        base_equity = min(base_equity, 20) 
    elif time_horizon > 10: 
        base_equity = min(base_equity + 10, 95) 
        
    base_equity = max(10, min(base_equity, 95)) 
    base_debt = 100 - base_equity

    st.markdown("---")
    st.markdown("#### Target Portfolio Composition")
    st.progress(int(base_equity))
    st.write(f"**Target Equity:** {int(base_equity)}% | **Target Debt/Gold:** {int(base_debt)}%")

# ==========================================
# TOOL 2: MULTI-AMC STP CONFIGURATOR
# ==========================================
with tab2:
    if investment_type == "Multi-AMC STP (HNI)":
        st.markdown("### 🏛️ Multi-AMC STP Configurator")
        st.write("Distribute large lumpsums across different fund houses to mitigate AMC risk. Source and Target funds are automatically filtered to stay within the same AMC.")
        
        num_amcs = st.slider("Number of AMCs to split across:", 1, 5, 3)
        per_amc_lumpsum = invest_amount / num_amcs
        monthly_stp_per_amc = per_amc_lumpsum / stp_duration
        
        st.info(f"**Math:** ₹{int(invest_amount):,} split across {num_amcs} AMCs = **₹{int(per_amc_lumpsum):,} per AMC.**\n\nMonthly STP over {stp_duration} months = **₹{int(monthly_stp_per_amc):,}/month per AMC.**")
        
        amc_choices = ["SBI", "HDFC", "ICICI", "Nippon India", "Kotak", "Axis", "Quant", "Parag Parikh", "Mirae Asset", "Tata", "Motilal Oswal", "DSP"]
        
        stp_configs = []
        
        for i in range(num_amcs):
            with st.expander(f"⚙️ AMC Slot {i+1} Configuration (₹{int(per_amc_lumpsum):,})", expanded=True):
                selected_amc = st.selectbox(f"Select Fund House for Slot {i+1}", options=amc_choices, key=f"amc_{i}")
                
                # Dynamic filtering of the AMFI Database
                amc_funds = [f for f in all_fund_names if selected_amc.lower() in f.lower()]
                if not amc_funds:
                     amc_funds = ["Manually search..."] + all_fund_names
                     
                liquid_guess = [f for f in amc_funds if "liquid" in f.lower() or "arbitrage" in f.lower()]
                equity_guess = [f for f in amc_funds if "equity" in f.lower() or "flexi" in f.lower() or "midcap" in f.lower() or "small cap" in f.lower()]
                
                c_src, c_tgt = st.columns(2)
                with c_src:
                    source_fund = st.selectbox("Source Fund (Park Lumpsum here):", options=(liquid_guess + amc_funds), key=f"src_{i}")
                with c_tgt:
                    target_fund = st.selectbox("Target Fund (Transfer Monthly here):", options=(equity_guess + amc_funds), key=f"tgt_{i}")
                    
                stp_configs.append({
                    "amc": selected_amc,
                    "lumpsum": per_amc_lumpsum,
                    "monthly": monthly_stp_per_amc,
                    "source": source_fund,
                    "target": target_fund
                })
                
        # Save to session state for the PDF generator
        st.session_
