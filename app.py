import streamlit as st
import requests
import secrets
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Whoop URL Hunter", layout="wide")
st.title("🕵️ Whoop API 'URL Hunter'")
st.markdown("This tool will force-test multiple API paths to find the one that works.")

# --- 1. SECRETS ---
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
except:
    st.error("Secrets missing. Check Streamlit settings.")
    st.stop()

# --- 2. AUTHENTICATION ---
if 'oauth_state' not in st.session_state:
    st.session_state['oauth_state'] = secrets.token_urlsafe(16)

# AUTH URL (We know this works because you got the green box)
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

if 'access_token' not in st.session_state:
    # Login Flow
    scopes = "read:recovery read:cycles read:sleep read:profile" # No %20 here, we let requests handle it
    auth_link = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={st.session_state['oauth_state']}"
    
    st.info("Step 1: Authenticate to get a fresh token.")
    st.markdown(f'<a href="{auth_link}" target="_blank" style="background-color:#E34935;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">👉 Login (New Tab)</a>', unsafe_allow_html=True)

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
            st.error(f"Auth Failed: {res.text}")

else:
    # --- 3. THE HUNT ---
    st.success("✅ Token Acquired! Starting URL Hunt...")
    token = st.session_state['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # These are the 4 most likely URL patterns for Whoop
    candidates = [
        # Option A: The "Standard" (worked once for you)
        "https://api.prod.whoop.com/developer/v1/recovery?limit=10",
        
        # Option B: The "Short" (common alternate)
        "https://api.prod.whoop.com/v1/recovery?limit=10",
        
        # Option C: The "User Profile" (simplest check)
        "https://api.prod.whoop.com/developer/v1/user/profile",
        
        # Option D: The "Cycle" endpoint
        "https://api.prod.whoop.com/developer/v1/cycle?limit=5"
    ]
    
    results = []
    
    for url in candidates:
        try:
            r = requests.get(url, headers=headers)
            status = r.status_code
            
            # Label the result
            if status == 200:
                outcome = "✅ SUCCESS"
            elif status == 404:
                outcome = "❌ 404 NOT FOUND"
            elif status == 401:
                outcome = "🚫 401 UNAUTHORIZED (Token Bad)"
            else:
                outcome = f"⚠️ {status} ERROR"
                
            results.append({
                "URL Tested": url,
                "Outcome": outcome,
                "Response Sample": r.text[:100] # First 100 chars
            })
            
        except Exception as e:
            results.append({"URL Tested": url, "Outcome": "CRASH", "Response Sample": str(e)})

    # Display Results Table
    st.table(pd.DataFrame(results))
    
    # Logout to try again
    if st.button("Logout / Try Again"):
        del st.session_state['access_token']
        st.rerun()
