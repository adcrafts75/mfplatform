import streamlit as st
import pandas as pd
import pdfplumber
import requests

st.set_page_config(page_title="Moneyplan Advisory Platform", layout="wide")
st.title("Moneyplan Advisory | Live Market Connect")

# --- THE LIVE DATA ENGINE ---
# This function contacts the free Indian Mutual Fund API to get EVERY fund name.
# We use @st.cache_data so it only downloads the massive list once per day, keeping your app fast.
@st.cache_data
def get_all_indian_mutual_funds():
    try:
        response = requests.get("https://api.mfapi.in/mf")
        data = response.json()
        
        # The API returns thousands of funds. We extract just the names for your dropdown.
        # We also create a dictionary linking the Name to its official Scheme Code.
        fund_dict = {item['schemeName']: item['schemeCode'] for item in data}
        return fund_dict
    except Exception as e:
        return {"Error loading live funds. Please check connection.": 0}

# Fetch the massive list of funds
with st.spinner("Connecting to AMFI Live Database... fetching 40,000+ schemes..."):
    all_funds_db = get_all_indian_mutual_funds()
    fund_names_list = list(all_funds_db.keys())

st.success(f"Successfully loaded {len(fund_names_list):,} Indian Mutual Fund schemes into the platform.")

# --- THE UI (Using the Live List) ---
st.markdown("### Search Any Mutual Fund in India")

# Streamlit's selectbox acts as a search bar automatically. 
# You can type "Parag Parikh" and it will instantly filter the 40,000 funds.
selected_fund = st.selectbox("Search and Select a Fund:", options=fund_names_list)

if selected_fund:
    scheme_code = all_funds_db[selected_fund]
    st.write(f"**Official AMFI Scheme Code:** {scheme_code}")
    
    # Example: Fetching live performance data for the selected fund
    if st.button(f"Fetch Live Performance for {selected_fund}"):
        with st.spinner("Fetching historical NAV data..."):
            nav_response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}")
            nav_data = nav_response.json()
            
            st.markdown(f"#### Fund House: {nav_data['meta']['fund_house']}")
            st.markdown(f"#### Category: {nav_data['meta']['scheme_category']}")
            
            # Show the latest NAV
            latest_nav = nav_data['data'][0]
            st.metric(label=f"Latest NAV ({latest_nav['date']})", value=f"₹ {latest_nav['nav']}")
