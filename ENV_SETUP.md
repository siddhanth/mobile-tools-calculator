# Environment Setup Guide

## Authentication Bypass for Local Development

The application now supports bypassing Auth0 authentication when running on localhost for easier local development.

### Quick Start (Local Development)

To run the app without authentication:

```bash
make run
```

This automatically sets `BYPASS_AUTH=true` and starts the app.

### Running with Authentication

To test with authentication enabled:

```bash
make run-prod
```

### Environment Variables

#### Development Mode

Create a `.env` file in the project root:

```bash
# Bypass authentication for localhost
BYPASS_AUTH=true
```

#### Production Mode

For production or to test authentication locally:

```bash
# Auth0 Configuration
BYPASS_AUTH=false
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=http://localhost:8501

# Optional: Access Control
AUTH0_ALLOWED_EMAILS=user1@gmail.com,user2@company.com
AUTH0_ALLOWED_DOMAINS=company.com,partner.org
```

### Manual Run (with auth bypass)

If you prefer to run manually without make:

```bash
source venv/bin/activate
BYPASS_AUTH=true streamlit run app.py
```

### Manual Run (with authentication)

```bash
source venv/bin/activate
streamlit run app.py
```

### Makefile Commands

- `make run` - Start app with auth bypass (default for local dev)
- `make run-prod` - Start app with authentication required
- `make stop` - Stop the running app
- `make restart` - Restart the app
- `make install` - Install dependencies
- `make clean` - Remove cache files
- `make logs` - Show recent app logs

### How It Works

When `BYPASS_AUTH=true`:
- The app skips Auth0 authentication
- Returns default user: "Developer" (dev@localhost)
- All protected routes are accessible
- No Auth0 credentials required

When `BYPASS_AUTH=false` (or not set):
- Full Auth0 authentication is required
- Users must log in with configured providers (Google, GitHub, etc.)
- Access can be restricted by email/domain
- Proper OAuth2 flow is enforced

### Security Note

**⚠️ Never deploy to production with `BYPASS_AUTH=true`**

The bypass feature is intended only for local development. Always use proper authentication in production environments.

