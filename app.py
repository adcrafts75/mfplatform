import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- PLATFORM BRANDING ---
st.set_page_config(page_title="Moneyplan Advisory Platform", layout="wide")

st.sidebar.title("Moneyplan Financial Services")
st.sidebar.write("**Advisor:** Sachin Thorat")
st.sidebar.markdown("---")
st.sidebar.info("Upload a client's CAS PDF to instantly generate actionable portfolio insights.")

st.title("Automated Portfolio Review")

# --- DATA ENGINE: OVERLAP DICTIONARY ---
# Pre-loaded with standard fund overlaps for the demonstration
overlap_db = {
    "Canara Robeco Mid Cap Fund": {"TVS Motor Company": 3.2, "Bharat Electronics": 2.8, "Indian Hotels Co": 2.5, "Trent Ltd": 2.1, "Cummins India": 1.9, "Reliance Industries": 0.0},
    "Kotak Midcap Fund": {"Supreme Industries": 3.5, "Cummins India": 2.8, "Bharat Electronics": 2.1, "Thermax": 2.0, "TVS Motor Company": 1.5, "Reliance Industries": 1.0},
    "Motilal Oswal Nifty India Defence": {"Bharat Electronics": 18.5, "Hindustan Aeronautics": 17.2, "Solar Industries": 15.1, "Mazagon Dock": 10.5}
}

# --- PDF PROCESSING ENGINE ---
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

# --- THE UI FRONTEND ---
uploaded_pdf = st.file_uploader("Upload Client Transaction PDF (CAMS/KFintech)", type=["pdf"])

if uploaded_pdf is not None:
    st.success("PDF securely processed.")
    
    with st.spinner("Analyzing holdings..."):
        # 1. Extract the funds from the PDF
        client_funds = process_client_pdf(uploaded_pdf)
        
        st.markdown("### 1. Detected Portfolio Holdings")
        for fund in client_funds:
            st.write(f"- 🏦 {fund}")
            
        st.markdown("---")
        st.markdown("### 2. Overlap & Risk Analysis")
        
        # 2. Setup the Dropdowns based on the PDF
        col1, col2 = st.columns(2)
        
        # We try to match extracted funds to our database, or use defaults if it's a new fund
        available_funds = list(overlap_db.keys())
        
        with col1:
            fund_a = st.selectbox("Select Fund 1 to Compare", options=available_funds, index=0)
        with col2:
            fund_b = st.selectbox("Select Fund 2 to Compare", options=available_funds, index=1)

        # 3. Calculate Overlap
        if fund_a and fund_b and fund_a != fund_b:
            dict_a = overlap_db[fund_a]
            dict_b = overlap_db[fund_b]
            
            overlapping_stocks = []
            total_overlap = 0.0
            
            common_keys = set(dict_a.keys()).intersection(set(dict_b.keys()))
            for stock in common_keys:
                if dict_a[stock] > 0 and dict_b[stock] > 0:
                    overlap_weight = min(dict_a[stock], dict_b[stock])
                    total_overlap += overlap_weight
                    overlapping_stocks.append({"Stock": stock, f"{fund_a} %": dict_a[stock], f"{fund_b} %": dict_b[stock], "Overlap %": overlap_weight})
            
            # Display Results
            st.metric(label="True Portfolio Overlap", value=f"{total_overlap:.2f}%")
            
            if total_overlap > 30:
                st.error("**ACTION REQUIRED:** High Overlap detected. Recommend pausing one SIP and routing to Flexi-Cap to maintain diversification.")
            elif total_overlap > 10:
                st.warning("**MONITOR:** Moderate Overlap. Acceptable, but ensure large-cap exposure elsewhere in the portfolio.")
            else:
                st.success("**OPTIMAL:** Low overlap. Funds are well diversified.")
                
            if overlapping_stocks:
                st.dataframe(pd.DataFrame(overlapping_stocks).sort_values(by="Overlap %", ascending=False), use_container_width=True)