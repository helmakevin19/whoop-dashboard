import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import secrets

# 1. PAGE SETUP
st.set_page_config(page_title="Whoop 5.0 Lifestyle Engine", layout="wide")
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

# 4. MAIN LOGIC
if 'access_token' not in st.session_state:
    
    # URL ENCODING
    scopes = "read:cycles read:recovery read:sleep read:profile" 
    
    auth_link = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={st.session_state['oauth_state']}"
    )
    
    st.markdown("### 🔐 Authentication Required")
    st.markdown(f'<a href="{auth_link}" target="_blank" style="background-color:#E34935;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;">👉 Login with Whoop (New Tab)</a>', unsafe_allow_html=True)
    st.info("Note: This will open a new tab. After you log in, your dashboard will appear in that NEW tab.")

    if "code" in st.query_params:
        code = st.query_params["code"]
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }
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
        # --- THE WORKING ENDPOINT: CYCLE ---
        # We use the endpoint that your screenshot proved was working
        url = "https://api.prod.whoop.com/developer/v1/cycle?limit=20"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()['records']
            
            clean_data = []
            for item in data:
                # CYCLE PARSING LOGIC
                # Cycles contain Strain and Calories
                score = item.get('score', {})
                
                clean_data.append({
                    "Date": item['start_time'][:10], # Grab just the date part
                    "Strain": score.get('strain', 0),
                    "Calories": score.get('kilojoule', 0) / 4.184, # Convert kJ to Kcal
                    "Avg Heart Rate": score.get('average_heart_rate', 0),
                    "Max Heart Rate": score.get('max_heart_rate', 0)
                })
            
            if clean_data:
                df = pd.DataFrame(clean_data)
                df = df.sort_values(by="Date") # Ensure timeline is correct
                
                # KPI Row
                col1, col2, col3 = st.columns(3)
                col1.metric("Avg Daily Strain", f"{df['Strain'].mean():.1f}")
                col2.metric("Avg Calories", f"{df['Calories'].mean():.0f} kcal")
                col3.metric("Max HR (Peak)", f"{df['Max Heart Rate'].max():.0f} bpm")
                
                # CHART 1: STRAIN (Work Load)
                fig_strain = px.bar(df, x="Date", y="Strain", 
                             title="Daily Strain (Work Load)", 
                             color="Strain",
                             color_continuous_scale=["lightblue", "blue", "purple"])
                st.plotly_chart(fig_strain, use_container_width=True)

                # CHART 2: CARDIO EFFICIENCY
                # (Comparing Strain vs Avg Heart Rate)
                st.subheader("Cardiovascular Efficiency")
                fig_scatter = px.scatter(df, x="Avg Heart Rate", y="Strain",
                                       size="Calories", color="Strain",
                                       title="Are you working harder with less heart effort?")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                with st.expander("View Raw Cycle Data"):
                    st.dataframe(df)
            else:
                st.warning("No cycle records found.")
            
        else:
            st.error(f"Whoop API Error: {response.status_code}")
            st.code(response.text)
            
    except Exception as e:
        st.error(f"App Error: {e}")
