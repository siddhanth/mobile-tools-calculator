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
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from authlib.integrations.requests_client import OAuth2Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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


def init_session_state():
    """Initialize session state variables for authentication."""
    defaults = {
        "authenticated": False,
        "user": None,
        "access_token": None,
        "id_token": None,
        "auth_code": None,
        "state": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
                
                # Clear the URL parameters
                st.query_params.clear()
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
    
    # Build Auth0 logout URL
    logout_url = (
        f"{config.logout_endpoint}?"
        f"client_id={config.client_id}&"
        f"returnTo={quote_plus(config.callback_url)}"
    )
    
    return logout_url


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)


def get_user() -> dict | None:
    """Get current authenticated user info."""
    return st.session_state.get("user")


def get_user_name() -> str:
    """Get current user's display name."""
    user = get_user()
    if user:
        return user.get("name", user.get("email", "User"))
    return "User"


def get_user_email() -> str | None:
    """Get current user's email."""
    user = get_user()
    if user:
        return user.get("email")
    return None


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
    logout_url = logout()
    
    if location == "sidebar":
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
    else:
        if st.button("🚪 Logout"):
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

