import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import secrets

# 1. PAGE SETUP
st.set_page_config(page_title="My Whoop Dashboard", layout="wide")
st.title("Whoop 5.0 Lifestyle Engine")

# 2. GET SECRETS
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
except:
    st.error("Secrets not found! Please set them in Streamlit Cloud.")
    st.stop()

# 3. AUTHENTICATION URLS
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

# --- SECURITY: STATE GENERATION ---
if 'oauth_state' not in st.session_state:
    st.session_state['oauth_state'] = secrets.token_urlsafe(16)

state_token = str(st.session_state['oauth_state'])

# 4. MAIN LOGIC
if 'access_token' not in st.session_state:
    
    # URL ENCODING
    scopes = "read:recovery%20read:cycles%20read:sleep" 
    
    auth_link = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={state_token}"
    )
    
    st.markdown("### 🔐 Authentication Required")
    st.markdown(f"To see your data, please authorize the app with Whoop:")
    
    # Open in New Tab for security
    st.markdown(f'<a href="{auth_link}" target="_blank" style="background-color:#E34935;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;">👉 Login with Whoop (New Tab)</a>', unsafe_allow_html=True)
    st.info("Note: This will open a new tab. After you log in, your dashboard will appear in that NEW tab.")

    # Handle the return
    if "code" in st.query_params:
        code = st.query_params["code"]
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }
        
        with st.spinner("Logging in..."):
            res = requests.post(TOKEN_URL, data=payload)
            
        if res.status_code == 200:
            st.session_state['access_token'] = res.json()['access_token']
            st.rerun()
        else:
            st.error(f"Login failed: {res.text}")

else:
    # 5. DASHBOARD (Logged In)
    st.success("✅ Connected to Whoop!")
    
    if st.button("Logout"):
        del st.session_state['access_token']
        st.rerun()
        
    token = st.session_state['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # --- FIX 1: UPDATE URL TO V2 ---
        # We changed 'v1' to 'v2' in the URL below
        response = requests.get("https://api.prod.whoop.com/developer/v2/recovery?limit=25", headers=headers)
        
        if response.status_code == 200:
            data = response.json()['records']
            
            clean_data = []
            for item in data:
                # --- FIX 2: ROBUST DATA PARSING (V1 vs V2 Support) ---
                # V2 data is "flat" (e.g. item['recovery_score']), V1 was nested (item['score']['recovery_score'])
                # This logic checks both locations so it never crashes.
                
                # Check for Score (Try V2 location first, then V1 location)
                rec_score = item.get('recovery_score')
                if rec_score is None:
                    rec_score = item.get('score', {}).get('recovery_score', 0)

                # Check for HRV
                hrv = item.get('hrv_rmssd_milli')
                if hrv is None:
                    hrv = item.get('score', {}).get('hrv_rmssd_milli', 0)

                # Check for RHR
                rhr = item.get('resting_heart_rate')
                if rhr is None:
                    rhr = item.get('score', {}).get('resting_heart_rate', 0)

                clean_data.append({
                    "Date": item['date'], # or item['created_at']
                    "Recovery Score": rec_score,
                    "HRV": hrv,
                    "RHR": rhr
                })
            
            if clean_data:
                df = pd.DataFrame(clean_data)
                
                # KPI Row
                col1, col2, col3 = st.columns(3)
                col1.metric("Avg Recovery", f"{df['Recovery Score'].mean():.0f}%")
                col2.metric("Avg HRV", f"{df['HRV'].mean():.0f}")
                col3.metric("Avg RHR", f"{df['RHR'].mean():.0f}")
                
                # Chart
                fig = px.bar(df, x="Date", y="Recovery Score", color="Recovery Score", 
                             title="Last 25 Days Recovery", color_continuous_scale=["red", "yellow", "green"])
                st.plotly_chart(fig)
                
                with st.expander("View Raw Data"):
                    st.dataframe(df)
            else:
                st.warning("No recovery records found. Make sure you have worn your Whoop recently!")
            
        else:
            # Print the error clearly if it fails again
            st.error(f"Whoop API Error: {response.status_code}")
            st.code(response.text)
            
    except Exception as e:
        st.error(f"App Error: {e}")
