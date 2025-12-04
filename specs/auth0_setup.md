# Auth0 Authentication Setup Guide

This document explains how to set up Auth0 authentication for the SIP Simulator application.

## Overview

The application uses Auth0 for OAuth2/OIDC authentication, which enables:
- **Google Sign-In** - Sign in with Google accounts
- **GitHub Sign-In** - Sign in with GitHub accounts  
- **Microsoft Sign-In** - Sign in with Microsoft/Azure AD accounts
- **Email/Password** - Traditional username/password authentication
- **Other Social Providers** - Any provider supported by Auth0

## Prerequisites

- An Auth0 account (free tier available at https://auth0.com)
- Python environment with dependencies installed

## Step 1: Create Auth0 Account & Application

1. Go to [Auth0](https://auth0.com) and create an account
2. In your Auth0 dashboard, go to **Applications > Applications**
3. Click **Create Application**
4. Choose:
   - **Name**: `SIP Simulator` (or your preferred name)
   - **Type**: `Regular Web Application`
5. Click **Create**

## Step 2: Configure Auth0 Application Settings

In your Auth0 application settings, configure the following:

### Application URIs

| Setting | Development Value | Production Value |
|---------|------------------|------------------|
| **Allowed Callback URLs** | `http://localhost:8501` | `https://your-app.streamlit.app` |
| **Allowed Logout URLs** | `http://localhost:8501` | `https://your-app.streamlit.app` |
| **Allowed Web Origins** | `http://localhost:8501` | `https://your-app.streamlit.app` |

### Save Your Credentials

Note down these values from the **Basic Information** section:
- **Domain** (e.g., `dev-xxxxx.us.auth0.com`)
- **Client ID**
- **Client Secret**

## Step 3: Enable Social Connections (Optional)

To enable Google, GitHub, or other social sign-ins:

1. Go to **Authentication > Social** in Auth0 dashboard
2. Click on the provider you want to enable (e.g., Google)
3. Toggle the connection **ON**
4. For Google:
   - You can use Auth0's dev keys for testing
   - For production, create your own Google OAuth credentials at [Google Cloud Console](https://console.cloud.google.com)
5. Go to the **Applications** tab and enable the connection for your app

## Step 4: Configure Environment Variables

Create a `.env` file in the `sip_simulator` directory with your Auth0 credentials:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=http://localhost:8501
```

### Environment Variable Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AUTH0_DOMAIN` | Your Auth0 tenant domain | `dev-abc123.us.auth0.com` |
| `AUTH0_CLIENT_ID` | Application Client ID | `abc123...` |
| `AUTH0_CLIENT_SECRET` | Application Client Secret | `xyz789...` |
| `AUTH0_CALLBACK_URL` | OAuth callback URL | `http://localhost:8501` |

## Step 5: Install Dependencies

Make sure you have the required packages installed:

```bash
pip install -r requirements.txt
```

This includes:
- `authlib>=1.3.0` - OAuth2/OIDC library
- `python-dotenv>=1.0.0` - Environment variable loading
- `httpx>=0.25.0` - HTTP client

## Step 6: Run the Application

```bash
streamlit run app.py
```

Visit `http://localhost:8501` and click "Sign in with Auth0" to authenticate.

## Production Deployment

### Streamlit Cloud

1. Go to your app settings in Streamlit Cloud
2. Add secrets in **Settings > Secrets**:

```toml
AUTH0_DOMAIN = "your-tenant.auth0.com"
AUTH0_CLIENT_ID = "your-client-id"
AUTH0_CLIENT_SECRET = "your-client-secret"
AUTH0_CALLBACK_URL = "https://your-app.streamlit.app"
```

3. Update your Auth0 application settings with the production URLs

### Other Hosting Platforms

Set the environment variables according to your platform's documentation:
- Heroku: Config Vars
- AWS: Environment Variables or Secrets Manager
- Docker: Environment variables or `.env` file

## Troubleshooting

### "Auth0 is not configured" Error

Make sure all environment variables are set correctly:
```bash
echo $AUTH0_DOMAIN
echo $AUTH0_CLIENT_ID
echo $AUTH0_CLIENT_SECRET
```

### Callback URL Mismatch

Ensure the `AUTH0_CALLBACK_URL` exactly matches what's configured in your Auth0 dashboard. Common issues:
- Missing trailing slash
- HTTP vs HTTPS mismatch
- Wrong port number

### Social Login Not Working

1. Check that the social connection is enabled in Auth0
2. Verify the connection is enabled for your application
3. For Google: ensure you're not in incognito mode during testing

## Security Notes

- **Never commit `.env` files** to version control
- Add `.env` to your `.gitignore`
- Use different Auth0 applications for development and production
- Rotate secrets periodically
- Enable MFA for your Auth0 account

## Migration from streamlit-authenticator

If you're migrating from the previous `streamlit-authenticator` setup:

1. The old `config/auth_config.yaml` file is no longer needed for authentication
2. User credentials were previously stored in YAML; Auth0 now manages all users
3. Users will need to create Auth0 accounts or use social login
4. Session handling is now managed by Auth0 tokens

## Files Changed

- `app.py` - Updated to use Auth0 authentication
- `auth.py` - New Auth0 authentication module
- `requirements.txt` - Added authlib, python-dotenv, httpx
- `config/auth0_config.yaml` - Auth0 configuration reference

