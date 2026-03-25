import streamlit as st
import pandas as pd
import pdfplumber
import requests

# --- PLATFORM BRANDING ---
st.set_page_config(page_title="Moneyplan Advisory Platform", layout="wide")

st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")

# --- 1. THE LIVE DATA ENGINE (OFFICIAL AMFI SOURCE) ---
@st.cache_data(ttl=86400) # Updates once every 24 hours
def get_all_indian_mutual_funds():
    # Bypassing third-party APIs and pulling the raw daily text file directly from AMFI
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", headers=headers, timeout=15)
        response.raise_for_status() 
        
        fund_dict = {}
        # The AMFI file is a giant block of text separated by semicolons
        lines = response.text.split('\n')
        
        for line in lines:
            parts = line.split(';')
            # Check if the line is an actual fund (starts with a numeric Scheme Code)
            if len(parts) >= 4 and parts[0].strip().isdigit():
                scheme_code = parts[0].strip()
                scheme_name = parts[3].strip()
                fund_dict[scheme_name] = scheme_code
                
        # Sort it alphabetically so it looks clean in your dropdown
        return dict(sorted(fund_dict.items()))
        
    except Exception as e:
        return {
            "Error: Cloud server blocked. Use offline CSV method instead.": 0,
            "Parag Parikh Flexi Cap Fund": 122639,
            "Nippon India Small Cap Fund": 118778,
            "Canara Robeco Mid Cap Fund": 147824,
            "Kotak Midcap Fund": 120152
        }

with st.spinner("Downloading Official AMFI Database..."):
    all_funds_db = get_all_indian_mutual_funds()
    all_fund_names = list(all_funds_db.keys())

# --- 2. INTERNAL HOLDINGS DATABASE (For Overlap) ---
master_holdings_db = {
    "Canara Robeco Mid Cap Fund": {"TVS Motor Company": 3.2, "Bharat Electronics": 2.8, "Indian Hotels": 2.5},
    "Kotak Midcap Fund": {"Supreme Industries": 3.5, "Cummins India": 2.8, "Bharat Electronics": 2.1},
    "Parag Parikh Flexi Cap Fund": {"HDFC Bank": 7.5, "Bajaj Holdings": 6.2, "ITC": 5.8},
    "Nippon India Small Cap Fund": {"Tube Investments": 3.1, "HDFC Bank": 1.2, "KPIT Tech": 2.5}
}

def get_fund_holdings(fund_name):
    for known_fund in master_holdings_db.keys():
        if known_fund.lower() in str(fund_name).lower():
            return master_holdings_db[known_fund], True
    return {"HDFC Bank (Placeholder)": 5.0, "Reliance (Placeholder)": 4.0, "ICICI (Placeholder)": 3.0}, False

# --- 3. THE PDF PROCESSING ENGINE ---
def process_client_pdf(uploaded_file):
    extracted_funds = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if "INF" in line and "|" in line:
                        fund_name = line.split('|')[0].strip()
                        if fund_name not in extracted_funds:
                            extracted_funds.append(fund_name)
                    elif ("- Regular Plan" in line or "- Direct Plan" in line) and "Fund" in line:
                        fund_name = line.split('-')[0].strip()
                        if fund_name not in extracted_funds:
                            extracted_funds.append(fund_name)
    return extracted_funds

st.sidebar.markdown("### Client Data Input")
uploaded_pdf = st.sidebar.file_uploader("Upload CAS PDF", type=["pdf"])

if 'extracted_portfolio' not in st.session_state:
    st.session_state.extracted_portfolio = []

if uploaded_pdf is not None:
    with st.sidebar.status("Reading Statement..."):
        st.session_state.extracted_portfolio = process_client_pdf(uploaded_pdf)
    st.sidebar.success(f"Found {len(st.session_state.extracted_portfolio)} funds.")

# --- MAIN UI DASHBOARD ---
st.title("Comprehensive Portfolio Review")

if not st.session_state.extracted_portfolio:
    st.info("👈 Please upload a client's CAS PDF in the sidebar to begin. (If no PDF, you can still use the Live Search at the bottom).")
else:
    with st.expander("View Detected Client Holdings", expanded=False):
        for f in st.session_state.extracted_portfolio:
            st.write(f"- 🏦 {f}")

# --- TABS FOR ANALYTICS ---
tab1, tab2, tab3 = st.tabs(["📊 Portfolio Overlap", "📈 What-If Performance", "🎯 Market-Aware Goal Planner"])

# ==========================================
# TAB 1: OVERLAP ANALYZER
# ==========================================
with tab1:
    st.markdown("### Compare Existing Portfolio vs. Proposed Additions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.extracted_portfolio:
            existing_fund = st.selectbox("Select Client's Existing Fund", options=st.session_state.extracted_portfolio)
        else:
            existing_fund = st.selectbox("Select Client's Existing Fund", options=["Please upload PDF first"])
            
    with col2:
        proposed_fund = st.selectbox("Select Proposed New Fund", options=all_fund_names)

    if st.button("Analyze True Overlap"):
        if existing_fund == "Please upload PDF first":
            st.warning("Upload a PDF to analyze actual client holdings.")
        else:
            dict_existing, found_existing = get_fund_holdings(existing_fund)
            dict_proposed, found_proposed = get_fund_holdings(proposed_fund)
            
            if not found_existing:
                st.warning(f"⚠️ We don't have the internal stocks for '{existing_fund}' in our database yet. Using placeholder data.")
            if not found_proposed:
                st.warning(f"⚠️ We don't have the internal stocks for '{proposed_fund}' in our database yet. Using placeholder data.")
            
            total_overlap = 0.0
            overlapping_stocks = []
            
            common_keys = set(dict_existing.keys()).intersection(set(dict_proposed.keys()))
            for stock in common_keys:
                overlap_weight = min(dict_existing[stock], dict_proposed[stock])
                total_overlap += overlap_weight
                overlapping_stocks.append
