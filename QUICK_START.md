# Quick Start Guide - Authentication Bypass

## 🚀 Running the App on Localhost (No Auth)

```bash
make run
```

That's it! The app will now run without requiring Auth0 authentication.

## 📋 What Changed?

### Before
```bash
# Had to configure Auth0 every time
export AUTH0_DOMAIN=...
export AUTH0_CLIENT_ID=...
export AUTH0_CLIENT_SECRET=...
streamlit run app.py
# Then login through Auth0 UI
```

### After
```bash
# Just run it!
make run
# App loads immediately, no login required
```

## 🔧 Available Commands

| Command | Description | Auth Required? |
|---------|-------------|----------------|
| `make run` | Start app (default) | ❌ No |
| `make run-prod` | Start app (production) | ✅ Yes |
| `make stop` | Stop running app | N/A |
| `make restart` | Restart app | Same as `make run` |

## 🎯 How It Works

When you run `make run`, it sets `BYPASS_AUTH=true` automatically:

```bash
# Behind the scenes:
BYPASS_AUTH=true streamlit run app.py
```

This tells the auth system to:
- Skip Auth0 login
- Use default user: "Developer" (dev@localhost)
- Grant full access to all features

## 🔐 Testing with Authentication

If you want to test Auth0 authentication locally:

1. Set up your `.env` file with Auth0 credentials
2. Run: `make run-prod`
3. Login through Auth0 as normal

## 📝 Environment Variables

### Option 1: Using .env file (recommended)

Create `.env` in the project root:

```bash
# For local dev (no auth)
BYPASS_AUTH=true
```

### Option 2: Inline command

```bash
BYPASS_AUTH=true streamlit run app.py
```

### Option 3: Use Makefile (easiest)

```bash
make run  # Auth bypass enabled automatically
```

## ⚠️ Important Notes

1. **Security**: Never deploy with `BYPASS_AUTH=true` to production
2. **Default**: If `BYPASS_AUTH` is not set, authentication is required
3. **User Info**: When bypassed, you'll see "Developer" as the user name
4. **Access**: All tabs and features are accessible with bypass enabled

## 🎨 User Experience

### With Auth Bypass (make run)
```
App loads → No login screen → Direct access to all features
User shown as: "Developer" (dev@localhost)
```

### With Auth Required (make run-prod)
```
App loads → Login screen → Auth0 authentication → User info from Auth0
User shown as: [Your actual name/email from Auth0]
```

## 📚 More Information

- Full setup guide: See `ENV_SETUP.md`
- Change details: See `CHANGELOG_AUTH_BYPASS.md`
- Auth0 configuration: See `config/auth0_config.yaml`

## 🐛 Troubleshooting

### App still asking for login?
Check that `BYPASS_AUTH=true` is set:
```bash
echo $BYPASS_AUTH  # Should print: true
```

### Want to test both modes?
```bash
# Terminal 1: No auth
make run

# Terminal 2: With auth
make run-prod
```

### See what's running
```bash
make logs
```

