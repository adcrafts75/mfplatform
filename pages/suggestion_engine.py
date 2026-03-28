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

# --- INTERNAL MASTER DATABASE (Curated Fundamentals & Historicals) ---
fund_database = {
    "Parag Parikh Flexi Cap Fund": {"Alpha": 4.52, "Beta": 0.81, "Sharpe": 1.65, "10Y_Return": 19.5},
    "Nippon India Small Cap Fund": {"Alpha": 7.43, "Beta": 0.92, "Sharpe": 1.88, "10Y_Return": 26.2},
    "Quant Multi Asset Allocation": {"Alpha": 6.67, "Beta": 1.05, "Sharpe": 1.51, "10Y_Return": 16.8},
    "HDFC Balanced Advantage": {"Alpha": 3.85, "Beta": 0.75, "Sharpe": 1.45, "10Y_Return": 15.2},
    "SBI Magnum Midcap": {"Alpha": 5.12, "Beta": 0.88, "Sharpe": 1.55, "10Y_Return": 20.4},
    "ICICI Pru Corporate Bond": {"Alpha": 1.05, "Beta": 0.45, "Sharpe": 0.95, "10Y_Return": 7.5},
}

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs([
    "🎯 Tool 1: Goal Allocator", 
    "📈 Tool 2: Scheme Engine", 
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
        investment_type = st.radio("Investment Mode", ["SIP", "Lumpsum", "Multi-AMC STP (HNI)"], index=0)
        invest_amount = st.number_input("Total Capital / Monthly SIP (₹)", value=10000, step=1000)
    with col3:
        time_horizon = st.slider("Investment Horizon (Years)", 1, 30, 10)
        expected_return = st.number_input("Client's Target Return (%)", value=12.0, step=0.5)
        
        stp_duration = 0
        if investment_type == "Multi-AMC STP (HNI)":
            stp_duration = st.slider("STP Duration (Months)", 3, 36, 12, help="How long to spread the lumpsum into the market.")

    # Core Asset Allocation Math
    base_equity = 100 - client_age
    if risk_profile == "Aggressive": base_equity += 15
    elif risk_profile == "Conservative": base_equity -= 15
    if time_horizon < 3: base_equity = min(base_equity, 20) 
    elif time_horizon > 10: base_equity = min(base_equity + 10, 95) 
    base_equity = max(10, min(base_equity, 95)) 
    base_debt = 100 - base_equity

    st.markdown("---")
    st.markdown("#### Target Portfolio Composition")
    st.progress(int(base_equity))
    st.write(f"**Target Equity:** {int(base_equity)}% | **Target Debt/Gold:** {int(base_debt)}%")
    
    st.success("👉 **Profile saved! Click on 'Tab 2: Scheme Engine' above to map the schemes and calculate overall performance.**")

# ==========================================
# TOOL 2: SCHEME ENGINE (Handles both SIP/Lumpsum & STP)
# ==========================================
with tab2:
    # --- SCENARIO A: MULTI-AMC STP ---
    if investment_type == "Multi-AMC STP (HNI)":
        st.markdown("### 🏛️ Multi-AMC STP Configurator")
        num_amcs = st.slider("Number of AMCs to split across:", 1, 5, 3)
        per_amc_lumpsum = invest_amount / num_amcs
        monthly_stp_per_amc = per_amc_lumpsum / stp_duration
        
        st.info(f"**Math:** ₹{int(invest_amount):,} split across {num_amcs} AMCs = **₹{int(per_amc_lumpsum):,} per AMC.**")
        
        amc_choices = ["SBI", "HDFC", "ICICI", "Nippon India", "Kotak", "Axis", "Quant", "Parag Parikh", "Mirae Asset", "Tata", "Motilal Oswal", "DSP"]
        stp_configs = []
        overall_stp_target_cagr = 0
        
        for i in range(num_amcs):
            with st.expander(f"⚙️ AMC Slot {i+1} Configuration (₹{int(per_amc_lumpsum):,})", expanded=True):
                selected_amc = st.selectbox(f"Select Fund House for Slot {i+1}", options=amc_choices, key=f"amc_{i}")
                
                amc_funds = [f for f in all_fund_names if selected_amc.lower() in f.lower()]
                if not amc_funds: amc_funds = ["Manually search..."] + all_fund_names
                     
                liquid_guess = [f for f in amc_funds if "liquid" in f.lower() or "arbitrage" in f.lower()]
                equity_guess = [f for f in amc_funds if "equity" in f.lower() or "flexi" in f.lower() or "midcap" in f.lower() or "small cap" in f.lower()]
                
                c_src, c_tgt = st.columns(2)
                with c_src:
                    source_fund = st.selectbox("Source Fund (Park Lumpsum here):", options=(liquid_guess + amc_funds), key=f"src_{i}")
                with c_tgt:
                    target_fund = st.selectbox("Target Fund (Transfer Monthly here):", options=(equity_guess + amc_funds), key=f"tgt_{i}")
                    target_cagr = st.number_input("Target Fund's Historical CAGR (%)", value=15.0, step=0.5, key=f"cagr_{i}")
                    overall_stp_target_cagr += target_cagr
                    
                stp_configs.append({
                    "amc": selected_amc, "lumpsum": per_amc_lumpsum, "monthly": monthly_stp_per_amc,
                    "source": source_fund, "target": target_fund, "target_cagr": target_cagr
                })
        
        st.session_state['stp_configs'] = stp_configs
        st.session_state['overall_stp_cagr'] = overall_stp_target_cagr / num_amcs
        
        st.markdown("---")
        st.markdown(f"### 📊 Overall Expected Target Portfolio CAGR: **{st.session_state['overall_stp_cagr']:.2f}%**")

    # --- SCENARIO B: STANDARD SIP & LUMPSUM ---
    else:
        st.markdown("### 📈 Macro-Adjusted Scheme Selection")
        st.write("Adjusts the baseline allocation using current Nifty Valuations.")
        
        mc1, mc2 = st.columns(2)
        with mc1:
            nifty_pe = st.number_input("Current Nifty 50 P/E Ratio", value=22.5, step=0.5)
        with mc2:
            macro_trend = st.selectbox("Broader Economy Trend", ["Expanding (Bullish)", "Neutral", "Slowing (Bearish)"], index=1)
            
        st.markdown("---")
        
        final_equity = base_equity
        scheme_recommendations = {}
        
        if nifty_pe > 24:
            st.error("🚨 Market is Overvalued. Shifting 15% from pure Equity to Multi-Asset/Debt to protect downside.")
            final_equity = max(10, base_equity - 15)
            scheme_recommendations = {"Quant Multi Asset Allocation": final_equity * 0.5, "HDFC Balanced Advantage": final_equity * 0.5, "ICICI Pru Corporate Bond": 100 - final_equity}
        elif nifty_pe < 18 and macro_trend == "Expanding (Bullish)":
            st.success("🟢 Market is Undervalued. Increasing Mid/Small Cap exposure to capture growth.")
            final_equity = min(95, base_equity + 10)
            scheme_recommendations = {"Parag Parikh Flexi Cap Fund": final_equity * 0.4, "SBI Magnum Midcap": final_equity * 0.3, "Nippon India Small Cap Fund": final_equity * 0.3, "ICICI Pru Corporate Bond": 100 - final_equity}
        else:
            st.info("🟡 Market is Fairly Valued. Proceeding with standard diversified allocation.")
            scheme_recommendations = {"Parag Parikh Flexi Cap Fund": final_equity * 0.6, "SBI Magnum Midcap": final_equity * 0.4, "ICICI Pru Corporate Bond": 100 - final_equity}
            
        st.markdown("#### Curated Scheme Recommendations")
        weighted_portfolio_return = 0.0
        
        for fund, pct in scheme_recommendations.items():
            if pct > 0:
                amt = (pct / 100) * invest_amount
                mode_text = "/ month" if investment_type == "SIP" else ""
                
                # Fetch historical return and calculate weighted impact
                hist_return = fund_database.get(fund, {}).get("10Y_Return", 10.0)
                weighted_portfolio_return += (pct / 100) * hist_return
                
                st.metric(label=f"{fund} ({int(pct)}% Alloc.)", value=f"₹ {int(amt):,}{mode_text}", delta=f"{hist_return}% Hist. CAGR")
                
        st.session_state['standard_configs'] = scheme_recommendations
        st.session_state['nifty_pe'] = nifty_pe
        st.session_state['weighted_return'] = weighted_portfolio_return
        
        st.markdown("---")
        st.markdown(f"### 📊 Overall Expected Portfolio CAGR: **{weighted_portfolio_return:.2f}%**")
        st.info("Note: The overall expected return is mathematically derived by calculating the weighted average of the long-term historical performance of the selected schemes.")

# ==========================================
# TOOL 3: RATIONALE & PDF GENERATOR
# ==========================================
with tab3:
    st.markdown("### Client Presentation & Automated PDF")
    
    # Text Cleaners
    def clean_paragraph(text):
        """Removes weird web characters but keeps the paragraph intact for wrapping."""
        if not text: return ""
        text = str(text)
        text = re.sub(r'[^\x20-\x7E]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def clean_name(text):
        """Hard truncates ONLY the mutual fund names to prevent FPDF crash."""
        text = clean_paragraph(text)
        if len(text) > 75: text = text[:72] + "..."
        return text

    # Standard Disclaimer String
    disclaimer_text = """STANDARD MUTUAL FUND DISCLAIMERS & TERMS:
1. Mutual Fund investments are subject to market risks, read all scheme related documents carefully before investing.
2. Past performance of the schemes is neither an indicator nor a guarantee of future performance.
3. The 'Overall Expected Portfolio CAGR' is calculated mathematically using weighted historical averages. It is strictly for illustrative planning purposes and does not constitute a promise or guarantee of minimum returns.
4. Moneyplan Financial Services (Sachin Thorat) is an AMFI Registered Mutual Fund Distributor and earns commissions from Asset Management Companies
