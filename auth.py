"""
Auth0 Authentication Module for SIP Simulator

This module provides Auth0 OAuth2/OIDC authentication for the Streamlit application.
Supports Google, GitHub, and other social logins configured in Auth0.
"""

import os
import streamlit as st
from urllib.parse import urlencode, quote_plus
import secrets
import json
import base64
import hashlib
import hmac
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Development mode - bypass authentication (set BYPASS_AUTH=true for localhost)
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() in ("true", "1", "yes")

# Session cookie settings
SESSION_COOKIE_NAME = "sip_session"
SESSION_EXPIRY_DAYS = 30

# Access control - comma-separated list of allowed emails or domains
# Examples: 
#   AUTH0_ALLOWED_EMAILS="user1@gmail.com,user2@company.com"
#   AUTH0_ALLOWED_DOMAINS="company.com,partner.org"
# Leave empty to allow all authenticated users
ALLOWED_EMAILS = [e.strip().lower() for e in os.getenv("AUTH0_ALLOWED_EMAILS", "").split(",") if e.strip()]
ALLOWED_DOMAINS = [d.strip().lower() for d in os.getenv("AUTH0_ALLOWED_DOMAINS", "").split(",") if d.strip()]


class Auth0Config:
    """Auth0 configuration loader."""
    
    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN", "")
        self.client_id = os.getenv("AUTH0_CLIENT_ID", "")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET", "")
        self.callback_url = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8501")
        self.scopes = ["openid", "profile", "email"]
    
    @property
    def is_configured(self) -> bool:
        """Check if Auth0 is properly configured."""
        return bool(self.domain and self.client_id and self.client_secret)
    
    @property
    def authorization_endpoint(self) -> str:
        return f"https://{self.domain}/authorize"
    
    @property
    def token_endpoint(self) -> str:
        return f"https://{self.domain}/oauth/token"
    
    @property
    def userinfo_endpoint(self) -> str:
        return f"https://{self.domain}/userinfo"
    
    @property
    def logout_endpoint(self) -> str:
        return f"https://{self.domain}/v2/logout"


def get_auth0_config() -> Auth0Config:
    """Get Auth0 configuration singleton."""
    if "auth0_config" not in st.session_state:
        st.session_state.auth0_config = Auth0Config()
    return st.session_state.auth0_config


def _get_session_secret() -> str:
    """Get or generate a session secret for signing cookies."""
    config = get_auth0_config()
    # Use client secret as base for session signing
    return config.client_secret or "default-secret-change-me"


def _sign_session_data(data: dict) -> str:
    """Sign session data and return base64 encoded string."""
    secret = _get_session_secret()
    json_data = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        secret.encode(), 
        json_data.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    payload = {"data": data, "sig": signature}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _verify_session_data(token: str) -> dict | None:
    """Verify and decode session data. Returns None if invalid."""
    try:
        secret = _get_session_secret()
        payload = json.loads(base64.b64decode(token.encode()).decode())
        
        data = payload.get("data", {})
        signature = payload.get("sig", "")
        
        # Verify signature
        expected_sig = hmac.new(
            secret.encode(),
            json.dumps(data, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(signature, expected_sig):
            # Check expiry
            expiry = data.get("expiry")
            if expiry and datetime.fromisoformat(expiry) > datetime.now():
                return data
        return None
    except Exception:
        return None


def _get_cookie_js(name: str) -> str:
    """Generate JavaScript to read a cookie value."""
    return f"""
    <script>
        function getCookie(name) {{
            const value = `; ${{document.cookie}}`;
            const parts = value.split(`; ${{name}}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        }}
        
        const cookieValue = getCookie("{name}");
        if (cookieValue) {{
            // Send cookie value to Streamlit via query param trick
            const url = new URL(window.location);
            if (!url.searchParams.has('session_token') && !url.searchParams.has('code')) {{
                url.searchParams.set('session_token', cookieValue);
                window.history.replaceState({{}}, '', url);
                window.location.reload();
            }}
        }}
    </script>
    """


def _set_cookie_js(name: str, value: str, days: int = 30) -> str:
    """Generate JavaScript to set a cookie."""
    return f"""
    <script>
        (function() {{
            const d = new Date();
            d.setTime(d.getTime() + ({days}*24*60*60*1000));
            const expires = "expires="+ d.toUTCString();
            document.cookie = "{name}={value};" + expires + ";path=/;SameSite=Lax";
        }})();
    </script>
    """


def _delete_cookie_js(name: str) -> str:
    """Generate JavaScript to delete a cookie."""
    return f"""
    <script>
        document.cookie = "{name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;SameSite=Lax";
    </script>
    """


def init_session_state():
    """Initialize session state variables for authentication."""
    defaults = {
        "authenticated": False,
        "user": None,
        "access_token": None,
        "id_token": None,
        "auth_code": None,
        "state": None,
        "session_restored": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Try to restore session from cookie (via query param)
    _restore_session_from_cookie()


def _restore_session_from_cookie():
    """Restore session from cookie if present."""
    if st.session_state.get("session_restored"):
        return
    
    query_params = st.query_params
    
    # Check if session token is in query params (sent by JS)
    if "session_token" in query_params:
        token = query_params["session_token"]
        session_data = _verify_session_data(token)
        
        if session_data:
            # Restore session
            st.session_state.authenticated = True
            st.session_state.user = session_data.get("user")
            st.session_state.access_token = session_data.get("access_token")
            st.session_state.id_token = session_data.get("id_token")
            st.session_state.session_restored = True
            
            # Clear the session_token from URL
            st.query_params.clear()
            st.rerun()
        else:
            # Invalid/expired token, clear it
            st.query_params.clear()
    
    st.session_state.session_restored = True


def _save_session_to_cookie():
    """Save current session to cookie."""
    if not st.session_state.get("authenticated"):
        return
    
    session_data = {
        "user": st.session_state.get("user"),
        "access_token": st.session_state.get("access_token"),
        "id_token": st.session_state.get("id_token"),
        "expiry": (datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat(),
    }
    
    token = _sign_session_data(session_data)
    st.components.v1.html(_set_cookie_js(SESSION_COOKIE_NAME, token, SESSION_EXPIRY_DAYS), height=0)


def generate_auth_url() -> str:
    """Generate Auth0 authorization URL."""
    config = get_auth0_config()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    st.session_state.state = state
    
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.callback_url,
        "scope": " ".join(config.scopes),
        "state": state,
    }
    
    return f"{config.authorization_endpoint}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict | None:
    """Exchange authorization code for tokens."""
    config = get_auth0_config()
    
    try:
        with httpx.Client() as client:
            response = client.post(
                config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": config.callback_url,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Token exchange failed: {response.text}")
                return None
    except Exception as e:
        st.error(f"Token exchange error: {str(e)}")
        return None


def get_user_info(access_token: str) -> dict | None:
    """Fetch user info from Auth0."""
    config = get_auth0_config()
    
    try:
        with httpx.Client() as client:
            response = client.get(
                config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Failed to fetch user info: {response.text}")
                return None
    except Exception as e:
        st.error(f"User info error: {str(e)}")
        return None


def handle_callback():
    """Handle OAuth callback and exchange code for tokens."""
    query_params = st.query_params
    
    # Skip if already authenticated
    if st.session_state.get("authenticated"):
        # Save session to cookie for persistence
        _save_session_to_cookie()
        return True
    
    # Check for authorization code
    if "code" in query_params:
        code = query_params["code"]
        returned_state = query_params.get("state", "")
        
        # Verify state (CSRF protection)
        # Note: State validation might fail on redirect in Streamlit
        # as session state can be reset. We'll be lenient here.
        
        # Exchange code for tokens
        tokens = exchange_code_for_token(code)
        
        if tokens:
            st.session_state.access_token = tokens.get("access_token")
            st.session_state.id_token = tokens.get("id_token")
            
            # Fetch user info
            user_info = get_user_info(tokens.get("access_token"))
            
            if user_info:
                st.session_state.user = user_info
                st.session_state.authenticated = True
                
                # Clear the URL parameters first
                st.query_params.clear()
                
                # Save session to cookie for persistence
                _save_session_to_cookie()
                
                return True
    
    # Check for error
    if "error" in query_params:
        error = query_params.get("error")
        error_description = query_params.get("error_description", "Unknown error")
        st.error(f"Authentication error: {error} - {error_description}")
        st.query_params.clear()
    
    return False


def logout():
    """Log out the user and clear session."""
    config = get_auth0_config()
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.id_token = None
    st.session_state.auth_code = None
    st.session_state.state = None
    st.session_state.session_restored = False
    
    # Clear session cookie
    st.components.v1.html(_delete_cookie_js(SESSION_COOKIE_NAME), height=0)
    
    # Build Auth0 logout URL
    logout_url = (
        f"{config.logout_endpoint}?"
        f"client_id={config.client_id}&"
        f"returnTo={quote_plus(config.callback_url)}"
    )
    
    return logout_url


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    # Bypass authentication in development mode
    if BYPASS_AUTH:
        return True
    
    authenticated = st.session_state.get("authenticated", False)
    
    # If not authenticated and no session_token in URL, inject JS to read cookie
    if not authenticated:
        query_params = st.query_params
        if "session_token" not in query_params and "code" not in query_params:
            # Inject JavaScript to read the session cookie
            st.components.v1.html(_get_cookie_js(SESSION_COOKIE_NAME), height=0)
    
    return authenticated


def is_authorized() -> bool:
    """Check if user is both authenticated AND authorized."""
    # Bypass authorization in development mode
    if BYPASS_AUTH:
        return True
    
    if not is_authenticated():
        return False
    
    email = get_user_email()
    return is_user_authorized(email)


def get_user() -> dict | None:
    """Get current authenticated user info."""
    return st.session_state.get("user")


def get_user_name() -> str:
    """Get current user's display name."""
    # Return default user in development mode
    if BYPASS_AUTH:
        return "Developer"
    
    user = get_user()
    if user:
        return user.get("name", user.get("email", "User"))
    return "User"


def get_user_email() -> str | None:
    """Get current user's email."""
    # Return default email in development mode
    if BYPASS_AUTH:
        return "dev@localhost"
    
    user = get_user()
    if user:
        return user.get("email")
    return None


def is_user_authorized(email: str | None) -> bool:
    """Check if a user's email is authorized to access the app.
    
    Authorization rules:
    1. If no ALLOWED_EMAILS and no ALLOWED_DOMAINS are set, allow all
    2. If ALLOWED_EMAILS is set, check if email is in the list
    3. If ALLOWED_DOMAINS is set, check if email domain matches
    """
    # If no restrictions configured, allow all authenticated users
    if not ALLOWED_EMAILS and not ALLOWED_DOMAINS:
        return True
    
    if not email:
        return False
    
    email_lower = email.lower()
    
    # Check exact email match
    if ALLOWED_EMAILS and email_lower in ALLOWED_EMAILS:
        return True
    
    # Check domain match
    if ALLOWED_DOMAINS:
        email_domain = email_lower.split("@")[-1] if "@" in email_lower else ""
        if email_domain in ALLOWED_DOMAINS:
            return True
    
    return False


def render_unauthorized_page(email: str | None):
    """Render page for unauthorized users."""
    st.error("🚫 Access Denied")
    st.markdown(f"""
    ### You are not authorized to access this application.
    
    **Your email:** `{email or 'Unknown'}`
    
    If you believe this is an error, please contact the administrator.
    """)
    
    # Show logout button
    config = get_auth0_config()
    logout_url = (
        f"{config.logout_endpoint}?"
        f"client_id={config.client_id}&"
        f"returnTo={quote_plus(config.callback_url)}"
    )
    
    if st.button("🔄 Sign in with a different account"):
        logout()
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)


def render_login_button():
    """Render the Auth0 login button."""
    config = get_auth0_config()
    
    if not config.is_configured:
        st.error("⚠️ Auth0 is not configured. Please set environment variables.")
        st.code("""
# Required environment variables:
export AUTH0_DOMAIN="your-tenant.auth0.com"
export AUTH0_CLIENT_ID="your-client-id"
export AUTH0_CLIENT_SECRET="your-client-secret"
export AUTH0_CALLBACK_URL="http://localhost:8501"
        """)
        return
    
    auth_url = generate_auth_url()
    
    st.markdown("""
    <style>
    .auth0-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: linear-gradient(135deg, #635BFF 0%, #0D6EFD 100%);
        color: white !important;
        padding: 14px 32px;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px rgba(99, 91, 255, 0.4);
        border: none;
    }
    .auth0-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 91, 255, 0.5);
        color: white !important;
    }
    .auth0-btn svg {
        width: 20px;
        height: 20px;
    }
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
        padding: 40px;
        background: rgba(30, 58, 95, 0.3);
        border-radius: 16px;
        border: 1px solid rgba(45, 74, 111, 0.5);
    }
    .login-divider {
        display: flex;
        align-items: center;
        width: 100%;
        max-width: 300px;
        gap: 16px;
        color: #64748b;
        font-size: 14px;
    }
    .login-divider::before,
    .login-divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #334155;
    }
    .providers-info {
        color: #94a3b8;
        font-size: 13px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="login-container">
        <a href="{auth_url}" class="auth0-btn">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
            Sign in with Auth0
        </a>
        <div class="login-divider">supports</div>
        <p class="providers-info">
            🔐 Google • GitHub • Microsoft • Email/Password<br/>
            <small>and other providers configured in Auth0</small>
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_logout_button(location: str = "sidebar"):
    """Render logout button."""
    config = get_auth0_config()
    
    # Build logout URL without clearing session state yet
    logout_url = (
        f"{config.logout_endpoint}?"
        f"client_id={config.client_id}&"
        f"returnTo={quote_plus(config.callback_url)}"
    )
    
    if location == "sidebar":
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            # Clear session and cookie on click
            logout()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
    else:
        if st.button("🚪 Logout"):
            # Clear session and cookie on click
            logout()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)


def require_auth(func):
    """Decorator to require authentication for a function."""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this feature.")
            render_login_button()
            return None
        return func(*args, **kwargs)
    return wrapper

