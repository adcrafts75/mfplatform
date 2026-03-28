import streamlit as st
import pandas as pd
import requests
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

# --- INTERNAL MASTER DATABASE (Curated Fundamentals) ---
fund_database = {
    "Parag Parikh Flexi Cap Fund": {"Category": "Flexi Cap", "Alpha": 4.52, "Beta": 0.81, "Sharpe": 1.65, "Expense Ratio": 0.60, "1Y Return": 36.5},
    "Nippon India Small Cap Fund": {"Category": "Small Cap", "Alpha": 7.43, "Beta": 0.92, "Sharpe": 1.88, "Expense Ratio": 0.68, "1Y Return": 52.4},
    "Quant Multi Asset Allocation": {"Category": "Hybrid", "Alpha": 6.67, "Beta": 1.05, "Sharpe": 1.51, "Expense Ratio": 0.58, "1Y Return": 41.2},
    "HDFC Balanced Advantage": {"Category": "BAF", "Alpha": 3.85, "Beta": 0.75, "Sharpe": 1.45, "Expense Ratio": 0.77, "1Y Return": 24.5},
    "SBI Magnum Midcap": {"Category": "Mid Cap", "Alpha": 5.12, "Beta": 0.88, "Sharpe": 1.55, "Expense Ratio": 0.82, "1Y Return": 45.1},
    "ICICI Pru Corporate Bond": {"Category": "Debt", "Alpha": 1.05, "Beta": 0.45, "Sharpe": 0.95, "Expense Ratio": 0.35, "1Y Return": 7.4},
    "SBI Liquid Fund": {"Category": "Liquid (STP Source)", "Alpha": 0.5, "Beta": 0.1, "Sharpe": 0.8, "Expense Ratio": 0.20, "1Y Return": 7.1},
}

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs([
    "🎯 Tool 1: Goal & Profile Allocator", 
    "📈 Tool 2: Macro & Scheme Engine", 
    "🔍 Tool 3: Final Plan & Rationale"
])

# ==========================================
# TOOL 1: GOAL-BASED ALLOCATOR (Now with STP)
# ==========================================
with tab1:
    st.markdown("### Client Profile & Requirement Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        client_age = st.number_input("Client Age", value=35, min_value=18, max_value=80)
        risk_profile = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"], index=1)
    with col2:
        investment_type = st.radio("Investment Mode", ["SIP", "Lumpsum", "STP (Systematic Transfer)"])
        invest_amount = st.number_input("Total Capital / Monthly SIP (₹)", value=500000, step=10000)
    with col3:
        time_horizon = st.slider("Investment Horizon (Years)", 1, 30, 10)
        
        # New STP specific inputs
        stp_duration = 0
        if investment_type == "STP (Systematic Transfer)":
            stp_duration = st.slider("STP Duration (Months)", 3, 24, 6, help="How long to spread the lumpsum into the market.")
            monthly_transfer = invest_amount / stp_duration
            st.info(f"**Monthly Transfer:** ₹ {int(monthly_transfer):,}/month")
        else:
            expected_return = st.number_input("Client's Expected Return (%)", value=12.0, step=0.5)

    st.markdown("---")
    
    # Logic: Target Equity based on Age and Risk
    base_equity = 100 - client_age
    if risk_profile == "Aggressive": base_equity += 15
    elif risk_profile == "Conservative": base_equity -= 15
        
    if time_horizon < 3: base_equity = min(base_equity, 20) 
    elif time_horizon > 10: base_equity = min(base_equity + 10, 95) 
        
    base_equity = max(10, min(base_equity, 95)) 
    base_debt = 100 - base_equity

    st.markdown("#### Target Portfolio Composition")
    st.progress(int(base_equity))
    st.write(f"**Target Equity:** {int(base_equity)}% | **Target Debt/Gold:** {int(base_debt)}%")
    
    if investment_type == "STP (Systematic Transfer)":
        st.warning(f"**STP Strategy:** 100% of capital (₹{int(invest_amount):,}) will initially park in a Liquid/Debt fund, transferring steadily to achieve the {int(base_equity)}% Equity target over {stp_duration} months.")

# ==========================================
# TOOL 2: MACRO-ECONOMIC OVERLAY & SCHEME SELECTOR
# ==========================================
with tab2:
    st.markdown("### Macro-Adjusted Scheme Selection")
    
    mc1, mc2 = st.columns(2)
    with mc1:
        nifty_pe = st.number_input("Current Nifty 50 P/E Ratio", value=22.5, step=0.5)
    with mc2:
        macro_trend = st.selectbox("Broader Economy Trend", ["Expanding (Bullish)", "Neutral", "Slowing (Bearish)"], index=1)
        
    st.markdown("---")
    
    # Macro Engine Logic
    final_equity = base_equity
    if nifty_pe > 24:
        st.error("🚨 Market is Overvalued. Shifting 15% from pure Equity to Multi-Asset/Debt to protect downside.")
        final_equity = max(10, base_equity - 15)
    elif nifty_pe < 18 and macro_trend == "Expanding (Bullish)":
        st.success("🟢 Market is Undervalued. Increasing Mid/Small Cap exposure to capture growth.")
        final_equity = min(95, base_equity + 10)
    else:
        st.info("🟡 Market is Fairly Valued. Proceeding with standard allocation.")

    # Generate Recommendations based on Mode
    st.markdown("#### Curated Scheme Strategy")
    if investment_type == "STP (Systematic Transfer)":
        st.write("**Step 1: Park Lumpsum in Source Fund (Liquid/Ultra Short Term)**")
        st.metric(label="Suggested Source: SBI Liquid Fund", value=f"₹ {int(invest_amount):,}")
        
        st.write(f"**Step 2: Monthly Transfer into Target Equity ({stp_duration} Months)**")
        st.metric(label="Suggested Target 1: Parag Parikh Flexi Cap Fund", value=f"₹ {int((invest_amount/stp_duration) * 0.6):,}/mo")
        st.metric(label="Suggested Target 2: SBI Magnum Midcap", value=f"₹ {int((invest_amount/stp_duration) * 0.4):,}/mo")
        
    else:
        scheme_recommendations = {
            "Parag Parikh Flexi Cap Fund": final_equity * 0.6,
            "SBI Magnum Midcap": final_equity * 0.4,
            "ICICI Pru Corporate Bond": 100 - final_equity
        }
        for fund, pct in scheme_recommendations.items():
            if pct > 0:
                alloc_amt = (pct / 100) * invest_amount
                st.metric(label=f"{fund} ({int(pct)}%)", value=f"₹ {int(alloc_amt):,}")

    st.markdown("---")
    st.markdown("### 🎛️ Advanced: Select Live AMFI Schemes")
    st.write("Override curated suggestions by selecting specific schemes from the live database of 40,000+ funds.")
    
    if investment_type == "STP (Systematic Transfer)":
        custom_source = st.selectbox("Select Custom Source Fund (Liquid/Debt):", options=all_fund_names, index=all_fund_names.index("SBI Liquid Fund - Regular Plan - Growth") if "SBI Liquid Fund - Regular Plan - Growth" in all_fund_names else 0)
        custom_target = st.selectbox("Select Custom Target Fund (Equity):", options=all_fund_names, index=all_fund_names.index("Parag Parikh Flexi Cap Fund - Regular Plan - Growth") if "Parag Parikh Flexi Cap Fund - Regular Plan - Growth" in all_fund_names else 1)
    else:
        custom_fund_1 = st.selectbox("Select Primary Scheme:", options=all_fund_names)
        custom_fund_2 = st.selectbox("Select Secondary Scheme:", options=all_fund_names)

# ==========================================
# TOOL 3: FUNDAMENTAL RATIONALE & REPORT
# ==========================================
with tab3:
    st.markdown("### Client Presentation & Rationale")
    
    if investment_type == "STP (Systematic Transfer)":
        st.markdown(f"#### 📝 Advisory Pitch for STP Strategy")
        rationale = f"""Based on current market valuations (Nifty P/E: {nifty_pe}), committing your entire ₹{int(invest_amount):,} directly into equity carries high 'timing risk'. 

**The Strategy:**
1. We will park your capital in a low-risk Liquid/Arbitrage fund. This immediately starts earning ~6.5-7% annualized return, better than a standard savings account.
2. Every month for the next {stp_duration} months, we will automatically transfer ₹{int(invest_amount/stp_duration):,} into high-growth equity funds.
3. **The Benefit:** This 'rupee-cost averages' your entry. If the market crashes next month, your subsequent transfers buy equity at cheaper prices, lowering your overall average cost and protecting your hard-earned wealth."""
        
        st.info(rationale)
        st.write(f"**Execution:** Source AMFI Code: {all_funds_db.get(custom_source if 'custom_source' in locals() else 'SBI Liquid Fund')} | Target AMFI Code: {all_funds_db.get(custom_target if 'custom_target' in locals() else 'Parag Parikh Flexi Cap Fund')}")
        
    else:
        st.markdown("#### 📝 Curated Fund Analytics")
        selected_fund = st.selectbox("Select a recommended scheme to generate rationale:", options=list(fund_database.keys()))
        if selected_fund:
            fund_data = fund_database[selected_fund]
            
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Alpha (Excess Return)", f"{fund_data['Alpha']}%")
            r2.metric("Beta (Volatility)", f"{fund_data['Beta']}")
            r3.metric("Sharpe Ratio", f"{fund_data['Sharpe']}")
            r4.metric("Expense Ratio", f"{fund_data['Expense Ratio']}%")
            
            rationale = ""
            if fund_data['Alpha'] > 4:
                rationale += f"**Outperformance:** The fund has an exceptional Alpha of {fund_data['Alpha']}%, proving the fund manager actively beats the benchmark.\n\n"
            if fund_data['Sharpe'] > 1.2:
                rationale += f"**Risk Management:** A strong Sharpe ratio of {fund_data['Sharpe']} delivers excellent risk-adjusted returns.\n\n"
                
            st.info(rationale + f"Given your {time_horizon}-year horizon and {risk_profile} profile, {selected_fund} perfectly balances your expectations with current market realities.")
