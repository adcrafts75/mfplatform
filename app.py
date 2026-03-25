import streamlit as st
import pandas as pd
import pdfplumber
import numpy as np

# --- PLATFORM BRANDING ---
st.set_page_config(page_title="Moneyplan Advisory Platform", layout="wide")

st.sidebar.image("https://img.icons8.com/color/96/000000/line-chart.png", width=60)
st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")

st.title("Comprehensive Portfolio Review")

# --- MOCK DATABASES (Replace with live APIs/CSVs in production) ---
moneyplan_recommended_funds = {
    "Parag Parikh Flexi Cap": {"HDFC Bank": 7.5, "Bajaj Holdings": 6.2, "ITC": 5.8, "Microsoft": 4.5},
    "Nippon India Small Cap": {"Tube Investments": 3.1, "HDFC Bank": 1.2, "KPIT Tech": 2.5},
    "SBI Contra Fund": {"Gail India": 4.1, "Reliance Industries": 3.5, "HDFC Bank": 2.1}
}

client_existing_db = {
    "Canara Robeco Mid Cap Fund": {"TVS Motor Company": 3.2, "Bharat Electronics": 2.8, "Indian Hotels": 2.5},
    "Kotak Midcap Fund": {"Supreme Industries": 3.5, "Cummins India": 2.8, "Bharat Electronics": 2.1}
}

historical_cagr_db = {
    "Canara Robeco Mid Cap Fund": 18.5,
    "Kotak Midcap Fund": 16.2,
    "Parag Parikh Flexi Cap": 21.4,
    "Nippon India Small Cap": 26.8
}

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Overlap Analyzer", "📈 What-If Performance", "🎯 Market-Aware Goal Planner"])

# ==========================================
# TAB 1: OVERLAP ANALYZER (Existing vs New)
# ==========================================
with tab1:
    st.markdown("### Compare Existing Portfolio vs. Proposed Additions")
    
    col1, col2 = st.columns(2)
    with col1:
        # Pulls from client's existing holdings
        existing_fund = st.selectbox("Select Client's Existing Fund", options=list(client_existing_db.keys()))
    with col2:
        # Pulls from Moneyplan's master list
        proposed_fund = st.selectbox("Select Proposed New Fund", options=list(moneyplan_recommended_funds.keys()))

    if st.button("Analyze Overlap"):
        dict_existing = client_existing_db[existing_fund]
        dict_proposed = moneyplan_recommended_funds[proposed_fund]
        
        overlapping_stocks = []
        total_overlap = 0.0
        
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
    st.markdown("### The Cost of Delay / Poor Fund Selection")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        invested_amt = st.number_input("Total Invested Amount (₹)", min_value=10000, value=100000, step=10000)
    with col_b:
        years_invested = st.slider("Years Invested", 1, 15, 5)
    with col_c:
        better_alternative = st.selectbox("Alternative Moneyplan Fund", options=["Parag Parikh Flexi Cap", "Nippon India Small Cap"])
        
    actual_fund = st.selectbox("Client's Underperforming Fund", options=["Canara Robeco Mid Cap Fund", "Kotak Midcap Fund"])
    
    if st.button("Run Alternate Universe Scenario"):
        # Calculate Future Value: FV = P * (1 + r)^n
        actual_rate = historical_cagr_db[actual_fund] / 100
        alt_rate = historical_cagr_db[better_alternative] / 100
        
        actual_corpus = invested_amt * ((1 + actual_rate) ** years_invested)
        alt_corpus = invested_amt * ((1 + alt_rate) ** years_invested)
        wealth_lost = alt_corpus - actual_corpus
        
        st.markdown(f"#### Value of {actual_fund}: **₹{int(actual_corpus):,}**")
        st.markdown(f"#### Value if invested in {better_alternative}: **₹{int(alt_corpus):,}**")
        
        st.error(f"### Wealth Lost due to poor fund selection: ₹{int(wealth_lost):,}")
        st.info("💡 **Advisory Action:** Switch immediately to stop further opportunity loss.")

# ==========================================
# TAB 3: MARKET-AWARE GOAL PLANNER
# ==========================================
with tab3:
    st.markdown("### Dynamic Strategy based on Valuations & PMI")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        target_goal = st.number_input("Target Goal Amount (₹)", value=5000000, step=500000)
        duration = st.slider("Time Horizon (Years)", 1, 25, 10)
    with c2:
        risk_profile = st.radio("Client Risk Profile", ["Conservative", "Moderate", "Aggressive"])
    with c3:
        # In production, fetch this live from NSE API
        market_valuation = st.selectbox("Current Market Valuation (Nifty P/E)", 
                                        ["Undervalued (PE < 18)", "Fair Value (PE 18-22)", "Overvalued (PE > 22)"], index=2)
        macro_trend = st.selectbox("Manufacturing PMI", ["Expanding (>50)", "Contracting (<50)"])

    st.markdown("---")
    st.markdown("### 📋 Automated Strategy Recommendation")
    
    # --- The Intelligence Engine ---
    recommended_rate = 12.0 # Default equity return
    
    if duration < 3:
        st.warning("**Time Horizon Too Short for Equity.**")
        st.write("👉 **Action:** 100% allocation to Arbitrage or Liquid Funds. Protect capital.")
        recommended_rate = 7.0
    elif "Overvalued" in market_valuation and duration > 5:
        st.error("**Market is Overvalued / High Risk.**")
        st.write("👉 **Action:** Stagger lumpsum investments via a 6-month STP from Liquid to Equity. Route fresh SIPs predominantly into Flexi-Cap and Balanced Advantage Funds. Avoid Small Caps.")
        recommended_rate = 11.0
    elif "Undervalued" in market_valuation and "Expanding" in macro_trend:
        st.success("**Market is Undervalued with Strong Economic Growth.**")
        st.write("👉 **Action:** Aggressive deployment. Increase allocation to Mid and Small Cap categories to capture the upcoming growth cycle.")
        recommended_rate = 14.0
    else:
        st.info("**Normal Market Conditions.**")
        st.write("👉 **Action:** Standard asset allocation based on risk profile. Continue regular SIPs.")
        
    # SIP Calculator Math: SIP = [FV * r] / [(1+r)^n - 1] * (1+r)
    monthly_rate = (recommended_rate / 100) / 12
    months = duration * 12
    required_sip = (target_goal * monthly_rate) / (((1 + monthly_rate)**months - 1) * (1 + monthly_rate))
    
    st.markdown(f"### Required Monthly SIP: **₹{int(required_sip):,}** *(Assuming {recommended_rate}% return based on current strategy)*")
