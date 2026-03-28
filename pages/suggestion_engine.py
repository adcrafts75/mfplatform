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

# --- INTERNAL MASTER DATABASE (Curated Fundamentals) ---
fund_database = {
    "Parag Parikh Flexi Cap Fund": {"Alpha": 4.52, "Beta": 0.81, "Sharpe": 1.65},
    "Nippon India Small Cap Fund": {"Alpha": 7.43, "Beta": 0.92, "Sharpe": 1.88},
    "Quant Multi Asset Allocation": {"Alpha": 6.67, "Beta": 1.05, "Sharpe": 1.51},
    "HDFC Balanced Advantage": {"Alpha": 3.85, "Beta": 0.75, "Sharpe": 1.45},
    "SBI Magnum Midcap": {"Alpha": 5.12, "Beta": 0.88, "Sharpe": 1.55},
    "ICICI Pru Corporate Bond": {"Alpha": 1.05, "Beta": 0.45, "Sharpe": 0.95},
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
        expected_return = st.number_input("Expected Return (%)", value=12.0, step=0.5)
        
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
    
    st.success("👉 **Profile saved! Click on 'Tab 2: Scheme Engine' above to see the specific fund recommendations.**")

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
                    
                stp_configs.append({
                    "amc": selected_amc, "lumpsum": per_amc_lumpsum, "monthly": monthly_stp_per_amc,
                    "source": source_fund, "target": target_fund
                })
        st.session_state['stp_configs'] = stp_configs

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
        for fund, pct in scheme_recommendations.items():
            if pct > 0:
                alloc_amt = (pct / 100) * invest_amount
                mode_text = "/ month" if investment_type == "SIP" else ""
                st.metric(label=f"{fund} ({int(pct)}%)", value=f"₹ {int(alloc_amt):,}{mode_text}")
                
        st.session_state['standard_configs'] = scheme_recommendations
        st.session_state['nifty_pe'] = nifty_pe

# ==========================================
# TOOL 3: RATIONALE & PDF GENERATOR
# ==========================================
with tab3:
    st.markdown("### Client Presentation & Automated PDF")
    
    # Text Sanitizer to prevent PDF crashes
    def sanitize_text(text):
        if not text: return ""
        text = str(text)
        text = re.sub(r'[^\x20-\x7E]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 75: text = text[:72] + "..."
        return text

    # --- PDF SCENARIO A: STP ---
    if investment_type == "Multi-AMC STP (HNI)" and 'stp_configs' in st.session_state:
        rationale = f"""Based on your goal to invest Rs. {int(invest_amount):,}, taking a lumpsum approach into equity carries 'timing risk' given current valuations. We recommend a Multi-AMC Systematic Transfer Plan (STP).

1. Capital Protection: Split your Rs. {int(invest_amount):,} across {num_amcs} top-tier AMCs to diversify risk.
2. Immediate Yield: Funds are parked in low-risk Liquid funds, generating debt-level yields.
3. Averaging: Over {stp_duration} months, Rs. {int(monthly_stp_per_amc):,} automatically transfers into high-growth Equity funds."""

        st.info(rationale)
        
        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
            pdf.set_font("Helvetica", 'I', 11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, "Multi-AMC Systematic Transfer Plan (STP) Advisory", ln=True, align='C')
            pdf.ln(8)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", '', 11)
            pdf.cell(0, 6, f"Date: {date.today().strftime('%B %d, %Y')}", ln=True)
            pdf.cell(0, 6, sanitize_text(f"Prepared For: {client_name}"), ln=True)
            pdf.cell(0, 6, f"Total Capital: Rs. {int(invest_amount):,}", ln=True)
            pdf.cell(0, 6, f"STP Duration: {stp_duration} Months", ln=True)
            pdf.ln(8)
            
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, " 1. Strategic Rationale", ln=True, fill=True)
            pdf.set_font("Helvetica", '', 10)
            pdf.multi_cell(0, 6, sanitize_text(rationale))
            pdf.ln(5)
            
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 10, " 2. Execution Plan (AMC Allocation)", ln=True, fill=True)
            pdf.ln(3)
            
            for i, config in enumerate(st.session_state['stp_configs']):
                pdf.set_font("Helvetica", 'B', 11)
                pdf.set_text_color(30, 58, 138)
                pdf.cell(0, 8, sanitize_text(f"AMC SLOT {i+1}: {config['amc']} (Rs. {int(config['lumpsum']):,})"), ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", '', 10)
                pdf.cell(0, 6, "SOURCE FUND (Lumpsum Parked Here):", ln=True)
                pdf.cell(0, 6, sanitize_text(config['source']), ln=True)
                pdf.cell(0, 6, "TARGET FUND (Equity Destination):", ln=True)
                pdf.cell(0, 6, sanitize_text(config['target']), ln=True)
                pdf.cell(0, 6, f"MONTHLY TRANSFER: Rs. {int(config['monthly']):,}", ln=True)
                pdf.ln(5)
            return bytes(pdf.output())

        st.download_button("📄 Download Multi-AMC STP PDF Report", data=generate_pdf(), file_name=f"{sanitize_text(client_name)}_STP_Plan.pdf", mime="application/pdf")

    # --- PDF SCENARIO B: STANDARD SIP/LUMPSUM ---
    elif investment_type in ["SIP", "Lumpsum"] and 'standard_configs' in st.session_state:
        rationale = f"Based on your {risk_profile} risk profile and {time_horizon}-year horizon, we have constructed a portfolio targeting {int(base_equity)}% Equity. Given the current Nifty valuation (P/E: {st.session_state.get('nifty_pe', 22)}), the engine has selected the following curated schemes to optimize your returns."
        st.info(rationale)
        
        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
            pdf.set_font("Helvetica", 'I', 11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, f"Automated {investment_type} Advisory Report", ln=True, align='C')
            pdf.ln(8)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", '', 11)
            pdf.cell(0, 6, f"Date: {date.today().strftime('%B %d, %Y')}", ln=True)
            pdf.cell(0, 6, sanitize_text(f"Prepared For: {client_name}"), ln=True)
            mode_text = "Monthly SIP" if investment_type == "SIP" else "Lumpsum Capital"
            pdf.cell(0, 6, f"Total {mode_text}: Rs. {int(invest_amount):,}", ln=True)
            pdf.ln(8)
            
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, " 1. Strategic Rationale", ln=True, fill=True)
            pdf.set_font("Helvetica", '', 10)
            pdf.multi_cell(0, 6, sanitize_text(rationale))
            pdf.ln(5)
            
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 10, " 2. Scheme Allocation & Analytics", ln=True, fill=True)
            pdf.ln(3)
            
            for fund, pct in st.session_state['standard_configs'].items():
                if pct > 0:
                    amt = (pct / 100) * invest_amount
                    pdf.set_font("Helvetica", 'B', 11)
                    pdf.set_text_color(30, 58, 138)
                    pdf.cell(0, 6, sanitize_text(fund), ln=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", '', 10)
                    pdf.cell(0, 6, f"Allocation: {int(pct)}% (Rs. {int(amt):,})", ln=True)
                    
                    if fund in fund_database:
                        stats = fund_database[fund]
                        pdf.cell(0, 6, f"Alpha: {stats['Alpha']} | Beta: {stats['Beta']} | Sharpe: {stats['Sharpe']}", ln=True)
                    pdf.ln(3)
                    
            pdf.ln(10)
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(0, 6, "Moneyplan Financial Services", ln=True)
            return bytes(pdf.output())

        st.download_button(f"📄 Download {investment_type} Strategy PDF Report", data=generate_pdf(), file_name=f"{sanitize_text(client_name)}_{investment_type}_Plan.pdf", mime="application/pdf")
