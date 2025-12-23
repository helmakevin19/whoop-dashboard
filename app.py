import streamlit as st
import requests
import secrets

# --- DEBUGGING DASHBOARD ---
st.set_page_config(page_title="Whoop Debugger", layout="wide")
st.title("🛠️ Whoop Connection Debugger")

# 1. CHECK SECRETS
st.write("### 1. Checking Configuration")
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    st.success(f"✅ Secrets found. Redirect URI: `{REDIRECT_URI}`")
except:
    st.error("❌ Secrets missing! Check Streamlit Settings.")
    st.stop()

# 2. AUTHENTICATION
if 'oauth_state' not in st.session_state:
    st.session_state['oauth_state'] = secrets.token_urlsafe(16)

if 'access_token' not in st.session_state:
    st.write("### 2. Authentication Needed")
    
    # We use the standard V1 endpoints
    auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
    token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
    
    scopes = "read:recovery%20read:cycles%20read:sleep%20read:profile"
    state = st.session_state['oauth_state']
    
    link = f"{auth_url}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={scopes}&state={state}"
    
    st.markdown(f'<a href="{link}" target="_blank" style="background-color:#E34935;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">👉 Login to Whoop (New Tab)</a>', unsafe_allow_html=True)
    
    if "code" in st.query_params:
        code = st.query_params["code"]
        st.write("🔄 exchanging code for token...")
        
        payload = {
            "grant_type": "authorization_code", 
            "code": code, 
            "client_id": CLIENT_ID, 
            "client_secret": CLIENT_SECRET, 
            "redirect_uri": REDIRECT_URI
        }
        
        res = requests.post(token_url, data=payload)
        st.write(f"Token Status: {res.status_code}")
        
        if res.status_code == 200:
            st.session_state['access_token'] = res.json()['access_token']
            st.rerun()
        else:
            st.error(f"❌ Auth Failed: {res.text}")

else:
    # 3. DIAGNOSTIC TESTS
    st.success("✅ Authenticated! Running connectivity tests...")
    
    if st.button("Logout"):
        del st.session_state['access_token']
        st.rerun()

    token = st.session_state['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # TEST A: THE USER PROFILE (Simplest Endpoint)
    st.subheader("Test A: User Profile")
    url_profile = "https://api.prod.whoop.com/developer/v1/user/profile"
    st.code(f"GET {url_profile}")
    
    res_prof = requests.get(url_profile, headers=headers)
    if res_prof.status_code == 200:
        st.success(f"SUCCESS (200): Found user {res_prof.json().get('first_name', 'Unknown')}")
    else:
        st.error(f"FAILED ({res_prof.status_code}): {res_prof.text}")

    # TEST B: RECOVERY (The Problematic One)
    st.subheader("Test B: Recovery Data")
    # Trying without limit first to see if base URL works
    url_recovery = "https://api.prod.whoop.com/developer/v1/recovery?limit=10"
    st.code(f"GET {url_recovery}")
    
    res_rec = requests.get(url_recovery, headers=headers)
    
    st.write("**Raw Server Response:**")
    st.json({
        "status_code": res_rec.status_code,
        "url_requested": res_rec.url,
        "response_body": res_rec.text[:500] # Show first 500 chars
    })
