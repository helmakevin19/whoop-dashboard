import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# 1. PAGE SETUP
st.set_page_config(page_title="My Whoop Dashboard", layout="wide")
st.title("Whoop 5.0 Lifestyle Engine")

# 2. GET SECRETS (We will set these in the Streamlit Cloud settings later)
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
except:
    st.error("Secrets not found! Please set them in Streamlit Cloud.")
    st.stop()

# 3. AUTHENTICATION (The "Login with Whoop" logic)
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

if 'access_token' not in st.session_state:
    # Step A: Show the Login Button
    auth_link = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=read:recovery read:cycles read:sleep"
    st.link_button("🔐 Login with Whoop", auth_link)

    # Step B: Catch the return signal from Whoop
    if "code" in st.query_params:
        code = st.query_params["code"]
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }
        # Step C: Exchange the code for a key (Token)
        res = requests.post(TOKEN_URL, data=payload)
        if res.status_code == 200:
            st.session_state['access_token'] = res.json()['access_token']
            st.rerun() # Refresh the page
        else:
            st.error("Login failed. Check your credentials.")
else:
    # 4. IF LOGGED IN: FETCH DATA
    st.success("Connected to Whoop!")
    token = st.session_state['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get last 30 days of Recovery Data
    try:
        response = requests.get("https://api.prod.whoop.com/developer/v1/recovery?limit=30", headers=headers)
        data = response.json()['records']
        
        # Clean the data
        clean_data = []
        for item in data:
            clean_data.append({
                "Date": item['date'],
                "Recovery Score": item['score']['recovery_score'],
                "HRV": item['score']['hrv_rmssd_milli'],
                "RHR": item['score']['resting_heart_rate']
            })
        
        df = pd.DataFrame(clean_data)
        
        # 5. VISUALIZATION
        # Metric Cards
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Recovery", f"{df['Recovery Score'].mean():.0f}%")
        c2.metric("Avg HRV", f"{df['HRV'].mean():.0f}")
        c3.metric("Avg RHR", f"{df['RHR'].mean():.0f}")
        
        # Simple Chart
        fig = px.bar(df, x="Date", y="Recovery Score", color="Recovery Score", 
                     title="Last 30 Days Recovery", color_continuous_scale=["red", "yellow", "green"])
        st.plotly_chart(fig)
        
        st.dataframe(df) # Show raw data table
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
