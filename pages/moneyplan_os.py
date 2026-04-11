import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
from fpdf import FPDF
from datetime import date

# ==========================================
# --- SECURITY GATEKEEPER ---
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False): return True
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

if not check_password(): st.stop()

# ==========================================
# --- PLATFORM BRANDING ---
# ==========================================
st.set_page_config(page_title="Moneyplan Advisor OS", layout="wide", page_icon="📈")

# ==========================================
# --- TRIPLE-ENGINE LIVE DATA FETCHER ---
# ==========================================
@st.cache_data(ttl=86400)
def sync_mutual_fund_database_master():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'application/json'}
    
    try:
        resp1 = requests.get("https://api.mfapi.in/mf", headers=headers, timeout=10)
        if resp1.status_code == 200:
            data = resp1.json()
            if len(data) > 1000:
                fund_dict = {str(item['schemeName']): str(item['schemeCode']) for item in data}
                return dict(sorted(fund_dict.items()))
    except Exception: pass

    try:
        resp2 = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", headers=headers, timeout=10)
        if resp2.status_code == 200 and "Scheme Name" in resp2.text:
            fund_dict = {}
            for line in resp2.text.split('\n'):
                parts = line.split(';')
                if len(parts) >= 4 and parts[0].strip().isdigit(): fund_dict[parts[3].strip()] = parts[0].strip()
            if len(fund_dict) > 1000: return dict(sorted(fund_dict.items()))
    except Exception: pass

    return {
        "⚠️ Error: Live Sync Blocked. Showing core portfolio.": 0,
        "Edelweiss Flexi Cap Fund - Regular Plan - Growth": 1,
        "Edelweiss Small Cap Fund - Regular Growth": 2,
        "HDFC Balanced Advantage Fund - Regular Growth": 3,
        "SBI Liquid Fund - Regular Growth": 4,
        "SBI Magnum Midcap Fund - Regular Growth": 5,
        "Quant Multi Asset Allocation Fund": 6
    }

with st.spinner("Syncing Live AMFI Database (40,000+ Schemes)..."):
    all_funds_db = sync_mutual_fund_database_master()
    all_fund_names = list(all_funds_db.keys())

# --- INTERNAL MASTER DATABASE ---
fund_database = {
    "Edelweiss Flexi Cap Fund - Regular Plan - Growth": {"Alpha": 3.8, "Beta": 0.85, "Sharpe": 1.5, "10Y_Return": 18.5},
    "Edelweiss Small Cap Fund - Regular Growth": {"Alpha": 6.5, "Beta": 0.90, "Sharpe": 1.7, "10Y_Return": 24.0},
    "HDFC Balanced Advantage Fund - Regular Growth": {"Alpha": 3.85, "Beta": 0.75, "Sharpe": 1.45, "10Y_Return": 15.2},
    "SBI Magnum Midcap Fund - Regular Growth": {"Alpha": 5.12, "Beta": 0.88, "Sharpe": 1.55, "10Y_Return": 20.4},
    "Quant Multi Asset Allocation Fund": {"Alpha": 6.67, "Beta": 1.05, "Sharpe": 1.51, "10Y_Return": 16.8},
}

FUND_CATEGORIES = {
    "Small Cap": {"risk_score": 9, "min_horizon": 7, "type": "Equity"},
    "Mid Cap": {"risk_score": 7, "min_horizon": 5, "type": "Equity"},
    "Flexi Cap": {"risk_score": 6, "min_horizon": 5, "type": "Equity"},
    "Large Cap": {"risk_score": 5, "min_horizon": 3, "type": "Equity"},
    "Balanced Advantage": {"risk_score": 4, "min_horizon": 3, "type": "Hybrid"},
    "Corporate Bond": {"risk_score": 2, "min_horizon": 1, "type": "Debt"},
    "Liquid": {"risk_score": 1, "min_horizon": 0, "type": "Debt"},
}

def safe_merge_lists(*lists):
    merged = []
    seen = set()
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged

def clean_paragraph(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'[^\x20-\x7E]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def clean_name(text):
    text = clean_paragraph(text)
    return text[:72] + "..." if len(text) > 75 else text

# ==========================================
# --- MASTER SIDEBAR NAVIGATION ---
# ==========================================
st.sidebar.title("Moneyplan Advisor OS")
st.sidebar.write("**Consultant:** Sachin Thorat")
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("Navigation Menu", [
    "1. Portfolio X-Ray & Restructuring",
    "2. SIP & Goal Allocator",
    "3. Multi-AMC STP Engine",
    "4. UPS/NPS vs MF Retirement Planner",
    "5. Viral Calculators (Lead Magnets)"
])
st.sidebar.markdown("---")
st.sidebar.caption("AMFI Registered Mutual Fund Distributor\nNashik & Pune")

disclaimer_text = """STANDARD MUTUAL FUND DISCLAIMERS & TERMS:
1. Mutual Fund investments are subject to market risks, read all scheme related documents carefully before investing.
2. Past performance is strictly for illustrative planning purposes and does not constitute a promise or guarantee of returns.
3. Moneyplan Financial Services is an AMFI Registered Mutual Fund Distributor.
4. This report is an auto-generated strategy analysis and does not constitute binding legal or tax advice."""

# ==========================================
# --- MODULE 1: PORTFOLIO X-RAY ---
# ==========================================
if app_mode == "1. Portfolio X-Ray & Restructuring":
    st.title("🔎 Portfolio X-Ray & Restructuring Engine")
    
    col1, col2, col3 = st.columns(3)
    with col1: client_name = st.text_input("Client Name", "Client")
    with col2: risk_profile = st.selectbox("Risk Profile", ["Conservative", "Moderate", "Aggressive"], index=1)
    with col3: time_horizon = st.slider("Goal Horizon (Years)", 1, 30, 5)

    ideal_equity = 50
    if risk_profile == "Aggressive": ideal_equity += 25
    if risk_profile == "Conservative": ideal_equity -= 25
    if time_horizon < 3: ideal_equity = min(ideal_equity, 20)
    elif time_horizon > 7: ideal_equity = min(ideal_equity + 15, 95)
    ideal_debt = 100 - ideal_equity

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload Client Portfolio (CSV)", type=["csv"])
    
    template_df = pd.DataFrame({"Scheme Name": ["Example Small Cap", "Example Balanced"], "Category": ["Small Cap", "Balanced Advantage"], "Invested Value": [500000, 200000], "Current Value": [650000, 210000]})
    st.download_button("⬇️ Download CSV Template", data=template_df.to_csv(index=False).encode('utf-8'), file_name="Portfolio_Template.csv", mime="text/csv")

    if uploaded_file is not None:
        try:
            portfolio_df = pd.read_csv(uploaded_file)
            portfolio_df.columns = portfolio_df.columns.str.strip()
            
            total_invested = portfolio_df["Invested Value"].sum()
            total_current = portfolio_df["Current Value"].sum()
            absolute_return = ((total_current - total_invested) / total_invested) * 100 if total_invested > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Invested", f"₹ {int(total_invested):,}")
            c2.metric("Current Market Value", f"₹ {int(total_current):,}")
            c3.metric("Absolute Return", f"{absolute_return:.2f}%")
            
            recs, reasons = [], []
            for _, row in portfolio_df.iterrows():
                cat = row.get("Category", "Flexi Cap")
                cat_rules = FUND_CATEGORIES.get(cat, {"risk_score": 5, "min_horizon": 5, "type": "Equity"})
                action, reason = "✅ HOLD", "Aligns with profile."
                
                if time_horizon < cat_rules["min_horizon"]: action, reason = "🚨 EXIT", f"Horizon too short for {cat}."
                elif risk_profile == "Conservative" and cat_rules["risk_score"] >= 7: action, reason = "🚨 EXIT", "Too risky for Conservative profile."
                elif row["Current Value"] < (row["Invested Value"] * 0.95) and time_horizon > 3: action, reason = "⚠️ REVIEW", "Capital erosion detected."
                    
                recs.append(action); reasons.append(reason)
                
            portfolio_df["Advisor Action"] = recs
            portfolio_df["Rationale"] = reasons
            
            st.dataframe(portfolio_df.style.map(lambda x: 'background-color: #ffebee; color: #c62828' if 'EXIT' in str(x) else 'background-color: #e8f5e9; color: #2e7d32' if 'HOLD' in str(x) else 'background-color: #fff3e0; color: #ef6c00' if 'REVIEW' in str(x) else '', subset=['Advisor Action']), use_container_width=True)
            st.info(f"**Target Rebalancing:** {ideal_equity}% Equity | {ideal_debt}% Debt. Funds marked 'EXIT' should be systematically transferred.")

            def generate_xray_pdf():
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
                pdf.set_font("Helvetica", 'B', 16); pdf.set_text_color(30, 58, 138); pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
                pdf.set_font("Helvetica", 'I', 11); pdf.set_text_color(100, 100, 100); pdf.cell(0, 8, "Portfolio X-Ray & Restructuring Report", ln=True, align='C'); pdf.ln(8)
                pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", '', 11)
                pdf.cell(0, 6, f"Prepared For: {clean_paragraph(client_name)} | Date: {date.today().strftime('%B %d, %Y')}", ln=True)
                pdf.cell(0, 6, f"Total Invested: Rs. {int(total_invested):,} | Current Value: Rs. {int(total_current):,} | Return: {absolute_return:.2f}%", ln=True); pdf.ln(5)
                pdf.set_font("Helvetica", 'B', 12); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 10, " Diagnostic Action Plan", ln=True, fill=True); pdf.ln(3)
                
                for _, row in portfolio_df.iterrows():
                    pdf.set_font("Helvetica", 'B', 11); pdf.set_text_color(30, 58, 138); pdf.cell(0, 6, clean_name(row['Scheme Name']), ln=True)
                    pdf.set_font("Helvetica", '', 9); pdf.set_text_color(0, 0, 0); pdf.cell(0, 5, f"Invested: Rs. {int(row['Invested Value']):,} | Current: Rs. {int(row['Current Value']):,} | Action: {clean_paragraph(row['Advisor Action'])}", ln=True)
                    pdf.set_font("Helvetica", 'I', 9); pdf.multi_cell(0, 5, clean_paragraph(f"Rationale: {row['Rationale']}")); pdf.ln(3)
                
                pdf.ln(5); pdf.set_text_color(80, 80, 80); pdf.set_font("Helvetica", '', 8); pdf.multi_cell(0, 4, clean_paragraph(disclaimer_text))
                return bytes(pdf.output())

            st.download_button("📄 Download Restructuring PDF", data=generate_xray_pdf(), file_name=f"{clean_name(client_name)}_XRay.pdf", mime="application/pdf")

        except Exception as e: st.error(f"Error reading file. Ensure it matches the template. Details: {e}")

# ==========================================
# --- MODULE 2: SIP & GOAL ALLOCATOR ---
# ==========================================
elif app_mode == "2. SIP & Goal Allocator":
    st.title("🎯 Standard SIP & Goal Allocator")
    
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Client Name", "Client")
        invest_amount = st.number_input("Monthly SIP (₹)", value=10000, step=1000)
    with col2:
        time_horizon = st.slider("Investment Horizon (Years)", 1, 30, 10)
        nifty_pe = st.number_input("Current Nifty 50 P/E Ratio", value=22.5, step=0.5)

    final_equity = 100 if time_horizon > 7 else 60
    if nifty_pe > 24: final_equity = max(10, final_equity - 20)
    
    st.markdown("#### Curated Scheme Recommendations")
    scheme_recs = {
        "Edelweiss Flexi Cap Fund - Regular Plan - Growth": final_equity * 0.5,
        "Edelweiss Small Cap Fund - Regular Growth": final_equity * 0.3 if time_horizon > 7 else 0,
        "HDFC Balanced Advantage Fund - Regular Growth": 100 - final_equity if final_equity < 100 else final_equity * 0.2,
    }
    
    weighted_return = 0.0
    for fund, pct in scheme_recs.items():
        if pct > 0:
            amt = (pct / 100) * invest_amount
            hist_ret = fund_database.get(fund, {}).get("10Y_Return", 15.0)
            weighted_return += (pct / 100) * hist_ret
            st.metric(f"{fund} ({int(pct)}%)", f"₹ {int(amt):,}/mo", f"{hist_ret}% Hist. CAGR")

    st.info(f"**Overall Expected Portfolio CAGR:** {weighted_return:.2f}%")

    def generate_sip_pdf():
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16); pdf.set_text_color(30, 58, 138); pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
        pdf.set_font("Helvetica", 'I', 11); pdf.set_text_color(100, 100, 100); pdf.cell(0, 8, "SIP Advisory Report", ln=True, align='C'); pdf.ln(8)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 6, f"Prepared For: {clean_paragraph(client_name)} | Total SIP: Rs. {int(invest_amount):,}/mo", ln=True)
        pdf.cell(0, 6, f"Expected Target CAGR: {weighted_return:.2f}%", ln=True); pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 12); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 10, " Scheme Allocation", ln=True, fill=True); pdf.ln(3)
        for fund, pct in scheme_recs.items():
            if pct > 0:
                amt = (pct / 100) * invest_amount
                pdf.set_font("Helvetica", 'B', 11); pdf.set_text_color(30, 58, 138); pdf.cell(0, 6, clean_name(fund), ln=True)
                pdf.set_font("Helvetica", '', 10); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, f"Allocation: {int(pct)}% (Rs. {int(amt):,})", ln=True); pdf.ln(3)
        
        pdf.ln(5); pdf.set_text_color(80, 80, 80); pdf.set_font("Helvetica", '', 8); pdf.multi_cell(0, 4, clean_paragraph(disclaimer_text))
        return bytes(pdf.output())

    st.download_button("📄 Download SIP Plan PDF", data=generate_sip_pdf(), file_name=f"{clean_name(client_name)}_SIP.pdf", mime="application/pdf")

# ==========================================
# --- MODULE 3: MULTI-AMC STP ENGINE ---
# ==========================================
elif app_mode == "3. Multi-AMC STP Engine":
    st.title("🏛️ Multi-AMC STP Configurator")
    
    col1, col2 = st.columns(2)
    with col1: client_name = st.text_input("Client Name", "Client")
    with col2: invest_amount = st.number_input("Total Lumpsum (₹)", value=2000000, step=100000)
    
    c1, c2 = st.columns(2)
    with c1: num_amcs = st.slider("Number of AMCs", 1, 5, 3)
    with c2: stp_duration = st.slider("STP Duration (Months)", 3, 36, 12)
    
    per_amc_lumpsum = invest_amount / num_amcs
    monthly_stp_per_amc = per_amc_lumpsum / stp_duration
    st.info(f"**Math:** ₹{int(invest_amount):,} split across {num_amcs} AMCs = **₹{int(per_amc_lumpsum):,} per AMC.** (Transferring ₹{int(monthly_stp_per_amc):,}/mo)")
    
    amc_choices = ["Edelweiss", "HDFC", "SBI", "ICICI", "Nippon India", "Kotak", "Axis", "Quant", "Parag Parikh", "Tata"]
    stp_configs = []
    
    for i in range(num_amcs):
        with st.expander(f"⚙️ AMC Slot {i+1} Configuration", expanded=True):
            selected_amc = st.selectbox(f"Fund House {i+1}", options=amc_choices, key=f"amc_{i}")
            amc_funds = [f for f in all_fund_names if selected_amc.lower() in f.lower()]
            if not amc_funds: amc_funds = ["Manually search..."] + all_fund_names
            liquid = [f for f in amc_funds if "liquid" in f.lower() or "arbitrage" in f.lower()]
            equity = [f for f in amc_funds if "equity" in f.lower() or "flexi" in f.lower() or "midcap" in f.lower() or "small cap" in f.lower()]
            
            src_options = safe_merge_lists(liquid, amc_funds, all_fund_names)
            tgt_options = safe_merge_lists(equity, amc_funds, all_fund_names)

            c_src, c_tgt = st.columns(2)
            with c_src: source_fund = st.selectbox("Source Fund (Park Lumpsum):", options=src_options, key=f"src_{i}")
            with c_tgt: target_fund = st.selectbox("Target Fund (Transfer To):", options=tgt_options, key=f"tgt_{i}")
            stp_configs.append({"amc": selected_amc, "source": source_fund, "target": target_fund, "lumpsum": per_amc_lumpsum, "monthly": monthly_stp_per_amc})

    def generate_stp_pdf():
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16); pdf.set_text_color(30, 58, 138); pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
        pdf.set_font("Helvetica", 'I', 11); pdf.set_text_color(100, 100, 100); pdf.cell(0, 8, "Multi-AMC STP Plan", ln=True, align='C'); pdf.ln(8)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 6, f"Prepared For: {clean_paragraph(client_name)} | Total Capital: Rs. {int(invest_amount):,}", ln=True); pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 12); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 10, " Execution Plan", ln=True, fill=True); pdf.ln(3)
        for i, config in enumerate(stp_configs):
            pdf.set_font("Helvetica", 'B', 11); pdf.set_text_color(30, 58, 138); pdf.cell(0, 8, f"SLOT {i+1}: {config['amc']} (Rs. {int(config['lumpsum']):,})", ln=True)
            pdf.set_font("Helvetica", '', 10); pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, f"From: {clean_name(config['source'])}", ln=True)
            pdf.cell(0, 6, f"To: {clean_name(config['target'])}", ln=True)
            pdf.cell(0, 6, f"Transfer: Rs. {int(config['monthly']):,}/mo", ln=True); pdf.ln(4)
        
        pdf.ln(5); pdf.set_text_color(80, 80, 80); pdf.set_font("Helvetica", '', 8); pdf.multi_cell(0, 4, clean_paragraph(disclaimer_text))
        return bytes(pdf.output())

    st.download_button("📄 Download STP Plan PDF", data=generate_stp_pdf(), file_name=f"{clean_name(client_name)}_STP.pdf", mime="application/pdf")

# ==========================================
# --- MODULE 4: RETIREMENT & UPS PLANNER ---
# ==========================================
elif app_mode == "4. UPS/NPS vs MF Retirement Planner":
    st.title("⚖️ Unified Pension (UPS) vs Equity MF Planner")
    st.write("Compare standard government/corporate pension trajectories against high-alpha Equity Mutual Fund wealth creation.")

    col1, col2, col3 = st.columns(3)
    with col1:
        current_age = st.number_input("Current Age", 25, 60, 35)
        retirement_age = st.number_input("Retirement Age", 50, 70, 60)
    with col2:
        current_salary = st.number_input("Current Basic Salary (₹/mo)", 10000, 500000, 50000)
        salary_growth = st.number_input("Expected Salary Growth (%)", 0.0, 15.0, 6.0)
    with col3:
        mf_return = st.number_input("Expected MF Portfolio Return (%)", 8.0, 20.0, 15.0)
        mf_contribution = st.number_input("Monthly MF SIP (₹)", 1000, 200000, 10000)

    years_to_retire = retirement_age - current_age
    last_drawn_salary = current_salary * ((1 + (salary_growth/100)) ** years_to_retire)
    est_ups_pension = last_drawn_salary * 0.5
    
    n = years_to_retire * 12
    r = (mf_return / 100) / 12
    mf_corpus = mf_contribution * (((1 + r)**n - 1) / r) * (1 + r)
    est_mf_pension = (mf_corpus * 0.06) / 12

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Est. Last Drawn Salary", f"₹ {int(last_drawn_salary):,}/mo")
    c2.metric("Est. Traditional Pension (UPS)", f"₹ {int(est_ups_pension):,}/mo", "Based on 50% basic")
    c3.metric(f"MF Corpus at {retirement_age}", f"₹ {int(mf_corpus):,}", f"Generates ₹{int(est_mf_pension):,}/mo SWP")

    st.info(f"**Consultant Insight:** While traditional pensions offer base security, a dedicated Equity SIP of ₹{int(mf_contribution):,} can independently build a **₹{int(mf_corpus/10000000):,} Crore** corpus, providing ultimate financial freedom.")

# ==========================================
# --- MODULE 5: VIRAL CALCULATORS (LEAD MAGNETS) ---
# ==========================================
elif app_mode == "5. Viral Calculators (Lead Magnets)":
    st.title("📱 Viral Social Media Calculators")
    st.write("Generate instant math for your Instagram Reels and WhatsApp Broadcasts to drive client urgency.")

    calc_type = st.radio("Select Content Tool:", ["The '1 Crore' Blueprint", "The Cost of Delay", "SWP: The 'Salary Replacement' Engine"], horizontal=True)
    st.markdown("---")

    if calc_type == "The '1 Crore' Blueprint":
        col1, col2 = st.columns(2)
        with col1: target_amount = st.number_input("Target Corpus (₹)", value=10000000, step=1000000)
        with col2: years = st.slider("Timeframe (Years)", 5, 30, 10)
        r = 15.0 / 100 / 12
        n = years * 12
        required_sip = (target_amount * r) / (((1 + r)**n - 1) * (1 + r))
        
        st.success(f"### Required Monthly SIP: **₹ {int(required_sip):,}** (Assuming 15% CAGR)")
        
        st.text_area("📋 Copy for WhatsApp / Instagram Caption:", f"Want to build ₹{int(target_amount/100000):,} Lakhs in exactly {years} years?\n\nYou don't need a massive salary, you just need discipline. A monthly SIP of just ₹{int(required_sip):,} in high-growth Equity Mutual Funds can get you there.\n\nTime is your biggest asset. DM me 'SIP' to start your wealth journey today! 🚀\n\n- Sachin Thorat, Moneyplan Financial Services", height=150)

    elif calc_type == "The Cost of Delay":
        col1, col2 = st.columns(2)
        with col1: sip_amount = st.number_input("Planned SIP Amount (₹)", value=10000, step=1000)
        with col2: delay_years = st.slider("Delaying By (Years)", 1, 10, 5)
        
        r = 15.0 / 100 / 12
        val_no_delay = sip_amount * (((1 + r)**(20*12) - 1) / r) * (1 + r)
        val_with_delay = sip_amount * (((1 + r)**((20-delay_years)*12) - 1) / r) * (1 + r)
        wealth_lost = val_no_delay - val_with_delay
        
        st.error(f"### Wealth Lost Due to {delay_years} Year Delay: **₹ {int(wealth_lost):,}**")
        
        st.text_area("📋 Copy for WhatsApp / Instagram Caption:", f"Thinking of starting your SIP 'later'? Here is the brutal truth about the Cost of Delay.\n\nIf you plan to invest ₹{int(sip_amount):,}/month, but you wait just {delay_years} years to start, you aren't just losing {delay_years} years of contributions...\n\nYou are losing ₹{int(wealth_lost/100000):,} LAKHS in compounding wealth! 🤯\n\nThe best time to plant a tree was 20 years ago. The second best time is today. Message me to map your portfolio.\n\n- Sachin Thorat, Moneyplan Financial Services", height=150)

    elif calc_type == "SWP: The 'Salary Replacement' Engine":
        col1, col2 = st.columns(2)
        with col1: corpus = st.number_input("Retirement Corpus (₹)", value=10000000, step=1000000)
        with col2: withdrawal_rate = st.slider("Annual Withdrawal Rate (%)", 4.0, 10.0, 6.0, step=0.5)
        
        monthly_income = (corpus * (withdrawal_rate/100)) / 12
        st.success(f"### Monthly Passive Income: **₹ {int(monthly_income):,}**")
        st.info("Assuming a conservative 10-12% post-retirement return, a 6% withdrawal rate ensures your principal corpus never depletes.")
        
        st.text_area("📋 Copy for WhatsApp / Instagram Caption:", f"Retirement isn't an age, it's a financial number.\n\nIf you build a corpus of ₹{int(corpus/10000000):,} Crore, you can set up a Systematic Withdrawal Plan (SWP) to pay yourself a 'Salary' of ₹{int(monthly_income):,} EVERY SINGLE MONTH. \n\nThe best part? Because your money stays invested in balanced funds, your original corpus doesn't deplete. You live off the growth.\n\nWant to know your exact retirement number? Send me a DM.\n\n- Sachin Thorat, Moneyplan Financial Services", height=150)
