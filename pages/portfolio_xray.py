import streamlit as st
import pandas as pd
import numpy as np
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
# --- PLATFORM BRANDING ---
# ==========================================
st.set_page_config(page_title="Moneyplan Portfolio X-Ray", layout="wide")
st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")

st.title("🔎 Portfolio X-Ray & Restructuring Engine")
st.write("Upload a client's existing portfolio to automatically generate Hold/Exit/Add recommendations based on their specific goals and risk profile.")

# ==========================================
# --- INTERNAL ANALYSIS DATABASE ---
# ==========================================
FUND_CATEGORIES = {
    "Small Cap": {"risk_score": 9, "min_horizon": 7, "type": "Equity"},
    "Mid Cap": {"risk_score": 7, "min_horizon": 5, "type": "Equity"},
    "Flexi Cap": {"risk_score": 6, "min_horizon": 5, "type": "Equity"},
    "Large Cap": {"risk_score": 5, "min_horizon": 3, "type": "Equity"},
    "Balanced Advantage": {"risk_score": 4, "min_horizon": 3, "type": "Hybrid"},
    "Corporate Bond": {"risk_score": 2, "min_horizon": 1, "type": "Debt"},
    "Liquid": {"risk_score": 1, "min_horizon": 0, "type": "Debt"},
}

disclaimer_text = """STANDARD MUTUAL FUND DISCLAIMERS & TERMS:
1. Mutual Fund investments are subject to market risks, read all scheme related documents carefully before investing.
2. Past performance of the schemes is neither an indicator nor a guarantee of future performance.
3. This restructuring diagnostic report is mathematically derived based on the inputs provided. It is strictly for illustrative planning purposes and does not constitute a promise or guarantee of minimum returns or loss prevention.
4. Moneyplan Financial Services (Sachin Thorat) is an AMFI Registered Mutual Fund Distributor and earns commissions from Asset Management Companies.
5. This report is an auto-generated strategy analysis and does not constitute binding legal or tax advice."""

# ==========================================
# --- TEXT CLEANERS FOR PDF ---
# ==========================================
def clean_paragraph(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'[^\x20-\x7E]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_name(text):
    text = clean_paragraph(text)
    if len(text) > 75: text = text[:72] + "..."
    return text

# ==========================================
# --- STEP 1: CLIENT PARAMETERS ---
# ==========================================
st.markdown("### 1. Client Goal Parameters")
col1, col2, col3 = st.columns(3)
with col1:
    client_name = st.text_input("Client Name", value="Client")
with col2:
    risk_profile = st.selectbox("Client Risk Profile", ["Conservative", "Moderate", "Aggressive"], index=1)
with col3:
    time_horizon = st.slider("Goal Horizon (Years)", 1, 30, 5)

ideal_equity = 50
if risk_profile == "Aggressive": ideal_equity += 25
if risk_profile == "Conservative": ideal_equity -= 25
if time_horizon < 3: ideal_equity = min(ideal_equity, 20)
elif time_horizon > 7: ideal_equity = min(ideal_equity + 15, 95)
ideal_debt = 100 - ideal_equity

# ==========================================
# --- STEP 2: DATA UPLOAD ---
# ==========================================
st.markdown("---")
st.markdown("### 2. Upload Portfolio Data")

template_data = {
    "Scheme Name": ["Nippon India Small Cap", "HDFC Balanced Advantage", "SBI Magnum Midcap"],
    "Category": ["Small Cap", "Balanced Advantage", "Mid Cap"],
    "Invested Value": [500000, 200000, 300000],
    "Current Value": [650000, 210000, 290000]
}
template_df = pd.DataFrame(template_data)

st.download_button(
    label="⬇️ Download Standard CSV Template",
    data=template_df.to_csv(index=False).encode('utf-8'),
    file_name="Moneyplan_Portfolio_Template.csv",
    mime="text/csv",
)

uploaded_file = st.file_uploader("Upload Client Portfolio (CSV)", type=["csv"])

# ==========================================
# --- STEP 3: THE X-RAY ENGINE & PDF ---
# ==========================================
if uploaded_file is not None:
    try:
        portfolio_df = pd.read_csv(uploaded_file)
        portfolio_df.columns = portfolio_df.columns.str.strip()
        
        st.markdown("---")
        st.markdown(f"### 3. Diagnostic Report for {client_name}")
        
        total_invested = portfolio_df["Invested Value"].sum()
        total_current = portfolio_df["Current Value"].sum()
        absolute_return = ((total_current - total_invested) / total_invested) * 100 if total_invested > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested", f"₹ {int(total_invested):,}")
        c2.metric("Current Market Value", f"₹ {int(total_current):,}")
        c3.metric("Absolute Return", f"{absolute_return:.2f}%")
        
        recommendations = []
        action_reasons = []
        
        for index, row in portfolio_df.iterrows():
            scheme = row["Scheme Name"]
            category = row.get("Category", "Flexi Cap") # Default to Flexi if missing
            current_val = row["Current Value"]
            invested_val = row["Invested Value"]
            
            cat_rules = FUND_CATEGORIES.get(category, {"risk_score": 5, "min_horizon": 5, "type": "Equity"})
            action = "✅ HOLD"
            reason = "Aligns with profile and horizon."
            
            if time_horizon < cat_rules["min_horizon"]:
                action = "🚨 EXIT / SWITCH"
                reason = f"Horizon too short ({time_horizon}y) for high-volatility {category} fund."
            elif risk_profile == "Conservative" and cat_rules["risk_score"] >= 7:
                action = "🚨 EXIT / REDUCE"
                reason = f"Too risky for a Conservative profile."
            elif current_val < (invested_val * 0.95) and time_horizon > 3:
                action = "⚠️ REVIEW"
                reason = "Capital erosion detected. Review fund fundamentals."
                
            recommendations.append(action)
            action_reasons.append(reason)
            
        portfolio_df["Advisor Action"] = recommendations
        portfolio_df["Rationale"] = action_reasons
        
        st.dataframe(
            portfolio_df.style.applymap(
                lambda x: 'background-color: #ffebee; color: #c62828' if 'EXIT' in str(x) else 
                          'background-color: #e8f5e9; color: #2e7d32' if 'HOLD' in str(x) else 
                          'background-color: #fff3e0; color: #ef6c00' if 'REVIEW' in str(x) else '',
                subset=['Advisor Action']
            ),
            use_container_width=True
        )
        
        st.markdown("### Suggested Rebalancing")
        st.info(f"Target Allocation for {time_horizon}Y / {risk_profile}: **{ideal_equity}% Equity | {ideal_debt}% Debt**")
        st.write("Funds marked as 'EXIT' should be systematically transferred into asset classes that match the target allocation above.")
        
        # --- PDF GENERATOR FUNCTION ---
        def generate_xray_pdf():
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # Header
            pdf.set_font("Helvetica", 'B', 16)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 10, "MONEYPLAN FINANCIAL SERVICES", ln=True, align='C')
            pdf.set_font("Helvetica", 'I', 11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, "Portfolio X-Ray & Restructuring Report", ln=True, align='C')
            pdf.ln(8)
            
            # Client Info
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", '', 11)
            pdf.cell(0, 6, f"Date: {date.today().strftime('%B %d, %Y')}", ln=True)
            pdf.cell(0, 6, clean_paragraph(f"Prepared For: {client_name}"), ln=True)
            pdf.cell(0, 6, f"Risk Profile: {risk_profile} | Goal Horizon: {time_horizon} Years", ln=True)
            
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_text_color(16, 185, 129)
            pdf.cell(0, 8, f"Target Rebalancing: {ideal_equity}% Equity | {ideal_debt}% Debt", ln=True)
            pdf.ln(4)
            
            # Summary Box
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, " 1. Portfolio Health Summary", ln=True, fill=True)
            pdf.set_font("Helvetica", '', 10)
            pdf.cell(0, 6, f"Total Invested: Rs. {int(total_invested):,}", ln=True)
            pdf.cell(0, 6, f"Current Market Value: Rs. {int(total_current):,}", ln=True)
            pdf.cell(0, 6, f"Absolute Return: {absolute_return:.2f}%", ln=True)
            pdf.ln(5)
            
            # Action Plan
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 10, " 2. Diagnostic Action Plan", ln=True, fill=True)
            pdf.ln(3)
            
            for index, row in portfolio_df.iterrows():
                pdf.set_font("Helvetica", 'B', 11)
                pdf.set_text_color(30, 58, 138)
                pdf.cell(0, 6, clean_name(row['Scheme Name']), ln=True)
                
                pdf.set_font("Helvetica", '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, f"Category: {row.get('Category', 'N/A')} | Invested: Rs. {int(row['Invested Value']):,} | Current: Rs. {int(row['Current Value']):,}", ln=True)
                
                action_clean = str(row['Advisor Action']).replace('✅', '').replace('🚨', '').replace('⚠️', '').strip()
                
                if "EXIT" in action_clean: pdf.set_text_color(200, 0, 0)
                elif "HOLD" in action_clean: pdf.set_text_color(0, 128, 0)
                else: pdf.set_text_color(200, 100, 0)
                
                pdf.set_font("Helvetica", 'B', 9)
                pdf.cell(0, 5, f"Action: {action_clean}", ln=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", 'I', 9)
                pdf.multi_cell(0, 5, clean_paragraph(f"Rationale: {row['Rationale']}"))
                pdf.ln(4)
                
            # Disclaimers
            pdf.ln(5)
            pdf.set_text_color(80, 80, 80)
            pdf.set_font("Helvetica", '', 8)
            pdf.multi_cell(0, 4, clean_paragraph(disclaimer_text))
            
            pdf.ln(5)
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(0, 6, "Moneyplan Financial Services | AMFI Registered Mutual Fund Distributor", ln=True)
            
            return bytes(pdf.output())

        st.markdown("---")
        st.download_button(
            label="📄 Download Restructuring Diagnostic PDF Report",
            data=generate_xray_pdf(),
            file_name=f"{clean_name(client_name)}_Portfolio_XRay.pdf",
            mime="application/pdf"
        )
        
        # Display Disclaimers at the bottom of the UI
        st.markdown("---")
        st.caption(disclaimer_text.replace('\n', '  \n'))

    except Exception as e:
        st.error(f"Error reading file. Please ensure it matches the exact format of the template. Details: {e}")
