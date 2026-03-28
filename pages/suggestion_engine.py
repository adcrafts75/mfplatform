import streamlit as st
import pandas as pd
import numpy_financial as npf
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
# --- PLATFORM BRANDING ---
# ==========================================
st.set_page_config(page_title="Moneyplan Suggestion Engine", layout="wide")
st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")

st.title("Intelligent Mutual Fund Suggestion Engine")

# ==========================================
# --- INTERNAL MASTER DATABASE (Fundamentals) ---
# ==========================================
# Update these ratios quarterly based on free data from ValueResearch/Morningstar
fund_database = {
    "Parag Parikh Flexi Cap Fund": {"Category": "Flexi Cap", "Alpha": 4.52, "Beta": 0.81, "Sharpe": 1.65, "Expense Ratio": 0.60, "1Y Return": 36.5, "3Y Return": 20.6},
    "Nippon India Small Cap Fund": {"Category": "Small Cap", "Alpha": 7.43, "Beta": 0.92, "Sharpe": 1.88, "Expense Ratio": 0.68, "1Y Return": 52.4, "3Y Return": 28.2},
    "Quant Multi Asset Allocation": {"Category": "Hybrid", "Alpha": 6.67, "Beta": 1.05, "Sharpe": 1.51, "Expense Ratio": 0.58, "1Y Return": 41.2, "3Y Return": 26.2},
    "HDFC Balanced Advantage": {"Category": "BAF", "Alpha": 3.85, "Beta": 0.75, "Sharpe": 1.45, "Expense Ratio": 0.77, "1Y Return": 24.5, "3Y Return": 16.2},
    "SBI Magnum Midcap": {"Category": "Mid Cap", "Alpha": 5.12, "Beta": 0.88, "Sharpe": 1.55, "Expense Ratio": 0.82, "1Y Return": 45.1, "3Y Return": 24.5},
    "ICICI Pru Corporate Bond": {"Category": "Debt", "Alpha": 1.05, "Beta": 0.45, "Sharpe": 0.95, "Expense Ratio": 0.35, "1Y Return": 7.4, "3Y Return": 6.8},
}

# --- UI TABS (THE 3 TOOLS) ---
tab1, tab2, tab3 = st.tabs([
    "🎯 Tool 1: Goal & Profile Allocator", 
    "📈 Tool 2: Macro & Scheme Engine", 
    "🔍 Tool 3: Fundamental Rationale"
])

# ==========================================
# TOOL 1: GOAL-BASED ALLOCATOR
# ==========================================
with tab1:
    st.markdown("### Client Profile & Requirement Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        client_age = st.number_input("Client Age", value=35, min_value=18, max_value=80)
        risk_profile = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"], index=1)
    with col2:
        investment_type = st.radio("Investment Mode", ["SIP", "Lumpsum"])
        invest_amount = st.number_input("Amount (₹)", value=10000, step=1000)
    with col3:
        time_horizon = st.slider("Investment Horizon (Years)", 1, 30, 10)
        expected_return = st.number_input("Client's Expected Return (%)", value=12.0, step=0.5)

    st.markdown("---")
    
    # Logic: 100-Age Rule modified by Risk Profile and Time Horizon
    base_equity = 100 - client_age
    
    if risk_profile == "Aggressive":
        base_equity += 15
    elif risk_profile == "Conservative":
        base_equity -= 15
        
    if time_horizon < 3:
        base_equity = min(base_equity, 20) # Cap equity if time is short
    elif time_horizon > 10:
        base_equity = min(base_equity + 10, 95) # Boost equity if time is long
        
    base_equity = max(10, min(base_equity, 95)) # Keep between 10% and 95%
    base_debt = 100 - base_equity

    st.markdown("#### Baseline Asset Allocation (Pre-Market Adjustments)")
    st.progress(int(base_equity))
    st.write(f"**Equity:** {int(base_equity)}% | **Debt/Gold/Cash:** {int(base_debt)}%")

# ==========================================
# TOOL 2: MACRO-ECONOMIC OVERLAY & SCHEME SELECTOR
# ==========================================
with tab2:
    st.markdown("### Macro-Adjusted Scheme Selection")
    st.write("Adjusts the client's baseline allocation based on current market valuations.")
    
    mc1, mc2 = st.columns(2)
    with mc1:
        # March 2026 Nifty PE is roughly 20 (Fair Value)
        nifty_pe = st.number_input("Current Nifty 50 P/E Ratio", value=20.0, step=0.5)
    with mc2:
        macro_trend = st.selectbox("Broader Economy Trend", ["Expanding (Bullish)", "Neutral", "Slowing (Bearish)"], index=1)
        
    st.markdown("---")
    
    # Macro Engine Logic
    final_equity = base_equity
    scheme_recommendations = {}
    
    if nifty_pe > 24:
        st.error("🚨 Market is Overvalued. Shifting 15% from pure Equity to Multi-Asset/Debt to protect downside.")
        final_equity = max(10, base_equity - 15)
        scheme_recommendations = {
            "Quant Multi Asset Allocation": final_equity * 0.5,
            "HDFC Balanced Advantage": final_equity * 0.5,
            "ICICI Pru Corporate Bond": 100 - final_equity
        }
    elif nifty_pe < 18 and macro_trend == "Expanding (Bullish)":
        st.success("🟢 Market is Undervalued. Increasing Mid/Small Cap exposure to capture growth.")
        final_equity = min(95, base_equity + 10)
        scheme_recommendations = {
            "Parag Flexi Cap": final_equity * 0.4,
            "SBI Magnum Midcap": final_equity * 0.3,
            "Nippon India Small Cap Fund": final_equity * 0.3,
            "ICICI Pru Corporate Bond": 100 - final_equity
        }
    else:
        st.info("🟡 Market is Fairly Valued. Proceeding with standard diversified allocation.")
        scheme_recommendations = {
            "Parag Parikh Flexi Cap Fund": final_equity * 0.6,
            "SBI Magnum Midcap": final_equity * 0.4,
            "ICICI Pru Corporate Bond": 100 - final_equity
        }
        
    st.markdown("#### Recommended Scheme Allocation")
    for fund, pct in scheme_recommendations.items():
        if pct > 0:
            alloc_amt = (pct / 100) * invest_amount
            st.metric(label=f"{fund} ({int(pct)}%)", value=f"₹ {int(alloc_amt):,}")

# ==========================================
# TOOL 3: FUNDAMENTAL RATIONALE & CLIENT REPORT
# ==========================================
with tab3:
    st.markdown("### Scheme Analytics & Advisory Rationale")
    
    selected_fund = st.selectbox("Select a recommended scheme to generate rationale:", options=list(fund_database.keys()))
    
    if selected_fund:
        fund_data = fund_database[selected_fund]
        
        # Displaying Fundamental Ratios
        st.markdown("#### Fundamental Ratios")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Alpha (Excess Return)", f"{fund_data['Alpha']}%", "Higher is better")
        r2.metric("Beta (Volatility)", f"{fund_data['Beta']}", "1.0 = Market Avg")
        r3.metric("Sharpe Ratio", f"{fund_data['Sharpe']}", "Risk-adjusted return")
        r4.metric("Expense Ratio", f"{fund_data['Expense Ratio']}%", "Lower is better")
        
        st.markdown("---")
        
        # Automated Pitch Generator
        rationale = ""
        if fund_data['Alpha'] > 4:
            rationale += f"**Outperformance:** The fund has an exceptional Alpha of {fund_data['Alpha']}%, proving the fund manager is actively beating the benchmark, justifying the {fund_data['Expense Ratio']}% expense ratio.\n\n"
        if fund_data['Sharpe'] > 1.2:
            rationale += f"**Risk Management:** With a strong Sharpe ratio of {fund_data['Sharpe']}, this scheme delivers excellent returns without taking reckless risks with your capital.\n\n"
        if fund_data['Beta'] < 0.9:
            rationale += f"**Downside Protection:** The Beta of {fund_data['Beta']} indicates that this fund is less volatile than the broader market, offering you a smoother ride during market corrections.\n\n"
            
        st.markdown("#### 📝 Why Moneyplan Recommends This Fund:")
        st.info(rationale + f"Given your {time_horizon}-year time horizon and {risk_profile} risk profile, {selected_fund} perfectly balances your expectation of {expected_return}% returns with current market realities.")
