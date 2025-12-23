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

# --- FIX: ROBUST STATE GENERATION ---
if 'oauth_state' not in st.session_state:
    # Generate a random string of 16 characters
    st.session_state['oauth_state'] = secrets.token_urlsafe(16)

# Force the token to be a string to avoid errors
state_token = str(st.session_state['oauth_state'])

# 4. MAIN LOGIC
if 'access_token' not in st.session_state:
    # --- DEBUGGING LINE (Verify this is not empty!) ---
    st.caption(f"Security Token Generated: `{state_token}`") 
    
    # Create the link with the state
    auth_link = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=read:recovery read:cycles read:sleep"
        f"&state={state_token}"
    )
    
    # Use a clear, big button
    st.markdown(f"## [👉 Click Here to Login with Whoop]({auth_link})", unsafe_allow_html=True)

    # Handle the return from Whoop
    if "code" in st.query_params:
        code = st.query_params["code"]
        
        # Exchange code for token
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
            st.write("Troubleshooting: Check that your Redirect URI in Secrets matches Whoop Dashboard exactly.")

else:
    # 5. DASHBOARD (Logged In)
    st.success("✅ Connected to Whoop!")
    
    # Logout button
    if st.button("Logout"):
        del st.session_state['access_token']
        st.rerun()
        
    token = st.session_state['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get("https://api.prod.whoop.com/developer/v1/recovery?limit=30", headers=headers)
        
        if response.status_code == 200:
            data = response.json()['records']
            
            clean_data = []
            for item in data:
                clean_data.append({
                    "Date": item['date'],
                    "Recovery Score": item['score']['recovery_score'],
                    "HRV": item['score']['hrv_rmssd_milli'],
                    "RHR": item['score']['resting_heart_rate']
                })
            
            df = pd.DataFrame(clean_data)
            
            # KPI Row
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg Recovery", f"{df['Recovery Score'].mean():.0f}%")
            col2.metric("Avg HRV", f"{df['HRV'].mean():.0f}")
            col3.metric("Avg RHR", f"{df['RHR'].mean():.0f}")
            
            # Chart
            fig = px.bar(df, x="Date", y="Recovery Score", color="Recovery Score", 
                         title="Last 30 Days Recovery", color_continuous_scale=["red", "yellow", "green"])
            st.plotly_chart(fig)
            
        else:
            st.error(f"Whoop API Error: {response.text}")
            
    except Exception as e:
        st.error(f"App Error: {e}")
