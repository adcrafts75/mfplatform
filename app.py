import streamlit as st
import pandas as pd
import pdfplumber
import requests
from fpdf import FPDF
from datetime import date

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
                overlapping_stocks.append({"Stock": stock, "Overlap %": overlap_weight})
            
            st.metric(label="True Portfolio Overlap", value=f"{total_overlap:.2f}%")
            if total_overlap < 15:
                st.success("✅ **SAFE TO INVEST:** Low overlap. This new fund adds true diversification.")
            else:
                st.error("⚠️ **WARNING:** High overlap. Adding this fund duplicates existing risk.")

# ==========================================
# TAB 2: WHAT-IF PERFORMANCE ENGINE
# ==========================================
with tab2:
    st.markdown("### The Cost of Poor Fund Selection")
    st.write("Calculate the opportunity cost by comparing the client's current fund growth against a proposed alternative.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        invested_amt = st.number_input("Total Invested Amount (₹)", min_value=10000, value=100000, step=10000)
        years_invested = st.slider("Years Invested", 1, 15, 5)
        
    with col_b:
        actual_fund_name = st.text_input("Client's Underperforming Fund Name", value="Old Regular Plan Fund")
        actual_rate = st.number_input(f"Historical CAGR of Client's Fund (%)", value=10.0, step=0.5)
        
        better_alternative = st.selectbox("Proposed Moneyplan Alternative", options=all_fund_names)
        alt_rate = st.number_input(f"Expected/Historical CAGR of Proposed Fund (%)", value=15.0, step=0.5)
    
    if st.button("Run Alternate Universe Scenario"):
        actual_corpus = invested_amt * ((1 + (actual_rate/100)) ** years_invested)
        alt_corpus = invested_amt * ((1 + (alt_rate/100)) ** years_invested)
        wealth_lost = alt_corpus - actual_corpus
        
        st.markdown("---")
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown(f"#### Value in {actual_fund_name}:")
            st.markdown(f"<h2 style='color: #ef4444;'>₹ {int(actual_corpus):,}</h2>", unsafe_allow_html=True)
        with res_col2:
            st.markdown(f"#### Value if invested in {better_alternative}:")
            st.markdown(f"<h2 style='color: #10b981;'>₹ {int(alt_corpus):,}</h2>", unsafe_allow_html=True)
            
        st.error(f"### 📉 Wealth Lost due to poor selection: ₹ {int(wealth_lost):,}")

# ==========================================
# TAB 3: MARKET-AWARE GOAL PLANNER & ADVISORY NOTE
# ==========================================
with tab3:
    st.markdown("### Dynamic Strategy & Client Communication")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        client_name = st.text_input("Client First Name", value="Client")
        target_goal = st.number_input("Target Goal Amount (₹)", value=5000000, step=500000)
        duration = st.slider("Time Horizon (Years)", 1, 25, 10)
    with c2:
        risk_profile = st.radio("Client Risk Profile", ["Conservative", "Moderate", "Aggressive"], index=1)
    with c3:
        market_valuation = st.selectbox("Current Market Valuation (Nifty P/E)", 
                                        ["Undervalued (PE < 18)", "Fair Value (PE 18-22)", "Overvalued (PE > 22)"], index=2)

    st.markdown("---")
    
    recommended_rate = 12.0
    action_text = ""
    
    if duration < 3:
        action_text = "100% allocation to Arbitrage or Liquid Funds to protect capital."
        recommended_rate = 7.0
    elif "Overvalued" in market_valuation and duration > 5:
        action_text = "Stagger lumpsum investments via a 6-month STP from Liquid to Equity. Route fresh SIPs predominantly into Flexi-Cap and Balanced Advantage Funds to mitigate immediate market risk."
        recommended_rate = 11.0
    elif "Undervalued" in market_valuation:
        action_text = "Aggressive deployment. Increase allocation to Mid and Small Cap categories to capture the upcoming growth cycle."
        recommended_rate = 14.0
    else:
        action_text = "Standard asset allocation based on your risk profile. Continue regular staggered SIPs."
        
    monthly_rate = (recommended_rate / 100) / 12
    months = duration * 12
    required_sip = (target_goal * monthly_rate) / (((1 + monthly_rate)**months - 1) * (1 + monthly_rate))
    
    st.markdown(f"### 🎯 Required Monthly SIP: **₹{int(required_sip):,}** *(Assuming {recommended_rate}% return)*")
    
    st.markdown("### 📝 Formal Advisory Note")
    st.write("Click the copy icon to paste into WhatsApp, or download the official PDF below.")
    
    current_date = date.today().strftime('%B %d, %Y')
    val_text = market_valuation.split('(')[0].strip()
    
    draft_note = f"""Dear {client_name},

Following our portfolio review on {current_date}, and discussing your goal of ₹{int(target_goal):,} in {duration} years, I have analyzed the current market conditions to optimize your strategy.

CURRENT MARKET OUTLOOK:
The market is currently considered to be {val_text.lower()}. 

RECOMMENDED STRATEGY:
{action_text}

ACTION PLAN:
To comfortably reach your target within the desired timeframe, assuming a conservative average return of {recommended_rate}%, a monthly SIP of ₹{int(required_sip):,} is required. 

Best regards,
Sachin Thorat
Moneyplan Financial Services
Nashik & Pune
"""
    st.code(draft_note, language='text')

    def generate_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        pdf.set_font("Helvetica", 'B', 16)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
        pdf.set_font("Helvetica", 'I', 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "Automated Portfolio Strategy & Advisory Note", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 8, f"Date: {current_date}", ln=True)
        pdf.cell(0, 8, f"Prepared For: {client_name}", ln=True)
        pdf.cell(0, 8, f"Prepared By: Sachin Thorat", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, "1. Financial Goal Assessment", ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(0, 8, f"Target Goal: Rs. {int(target_goal):,} to be achieved in {duration} years.")
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, "2. Market Outlook & Strategy", ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(0, 8, f"Current Market Valuation: {val_text}.\n{action_text}")
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, "3. Execution Plan", ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(0, 8, f"Required Monthly SIP: Rs. {int(required_sip):,}\n(Assuming a conservative {recommended_rate}% CAGR based on asset allocation).")
        pdf.ln(15)
        
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 6, "Moneyplan Financial Services", ln=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 6, "AMFI Registered Mutual Fund Distributor", ln=True)
        pdf.cell(0, 6, "Nashik & Pune", ln=True)
        pdf.ln(15)
        
        pdf.set_text_color(120, 120, 120)
        pdf.set_font("Helvetica", 'I', 8)
        disclaimer = "STANDARD DISCLAIMER: Mutual Fund investments are subject to market risks, read all scheme related documents carefully. The NAVs of the schemes may go up or down depending upon the factors and forces affecting the securities market including the fluctuations in the interest rates. The past performance of the mutual funds is not necessarily indicative of future performance of the schemes. This report is auto-generated for advisory planning purposes only and does not constitute binding legal or tax advice."
        pdf.multi_cell(0, 4, disclaimer)
        
        return bytes(pdf.output())

    st.markdown("---")
    st.download_button(
        label="📄 Download Official PDF Report",
        data=generate_pdf(),
        file_name=f"{client_name}_Moneyplan_Advisory_Report.pdf",
        mime="application/pdf"
    )

st.markdown("---")
st.markdown("### 🔍 Live Mutual Fund Database")
selected_fund_live = st.selectbox("Search any active fund in India to get its AMFI Scheme Code:", options=all_fund_names)
if selected_fund_live:
    if "Error" not in selected_fund_live:
        st.write(f"**AMFI Scheme Code:** {all_funds_db[selected_fund_live]}")
