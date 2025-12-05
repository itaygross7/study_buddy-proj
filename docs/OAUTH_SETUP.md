# OAuth Setup Guide (Google & Apple Sign-In)

This guide will help you set up Google and Apple OAuth for StudyBuddy.

## Table of Contents
- [Google Sign-In Setup](#google-sign-in-setup)
- [Apple Sign-In Setup](#apple-sign-in-setup)
- [Common Issues](#common-issues)
- [Testing OAuth](#testing-oauth)

---

## Google Sign-In Setup

### Prerequisites
- A Google account
- Access to Google Cloud Console

### Step-by-Step Instructions

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top
3. Click "New Project"
4. Enter project name (e.g., "StudyBuddy")
5. Click "Create"

#### 2. Enable Google+ API

1. In the sidebar, go to **APIs & Services** > **Library**
2. Search for "Google+ API"
3. Click on it and press "Enable"

#### 3. Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: External (or Internal for workspace)
   - App name: StudyBuddy
   - User support email: your email
   - Developer contact: your email
   - Click **Save and Continue** through the scopes and test users

4. Back in **Create OAuth client ID**:
   - Application type: **Web application**
   - Name: StudyBuddy Web Client
   
5. **Add Authorized redirect URIs** - THIS IS CRITICAL:
   
   **For Production:**
   ```
   https://yourdomain.com/oauth/google/callback
   ```
   
   **For Development (localhost):**
   ```
   http://localhost:5000/oauth/google/callback
   ```
   
   **For Development (custom port):**
   ```
   http://localhost:PORT/oauth/google/callback
   ```
   
   **For Development (network access):**
   ```
   http://192.168.x.x:5000/oauth/google/callback
   ```
   
   ⚠️ **IMPORTANT:** The redirect URI must EXACTLY match your `BASE_URL` + `/oauth/google/callback`

6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

#### 4. Configure StudyBuddy

1. Open your `.env` file (or create from `.env.example`)

2. Set your domain and base URL:
   ```bash
   DOMAIN="yourdomain.com"
   BASE_URL="https://yourdomain.com"  # Must match EXACTLY how users access your site
   ```
   
   For development:
   ```bash
   DOMAIN="localhost"
   BASE_URL="http://localhost:5000"
   ```

3. Add your Google credentials:
   ```bash
   GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-client-secret-here"
   ```

4. Restart the application:
   ```bash
   # For Docker:
   docker compose restart app
   
   # For systemd:
   sudo systemctl restart studybuddy
   
   # For development:
   # Stop and restart your Flask app
   ```

---

## Apple Sign-In Setup

### Prerequisites
- Apple Developer Account ($99/year)
- Access to Apple Developer Portal

### Step-by-Step Instructions

#### 1. Create App ID

1. Go to [Apple Developer Portal](https://developer.apple.com/)
2. Navigate to **Certificates, Identifiers & Profiles**
3. Click **Identifiers** > **+** (to add new)
4. Select **App IDs** > Continue
5. Select **App** > Continue
6. Configure:
   - Description: StudyBuddy
   - Bundle ID: com.yourdomain.studybuddy (Explicit)
   - Capabilities: Check **Sign in with Apple**
7. Click **Continue** > **Register**

#### 2. Create Services ID

1. Click **Identifiers** > **+** (to add new)
2. Select **Services IDs** > Continue
3. Configure:
   - Description: StudyBuddy Web
   - Identifier: com.yourdomain.studybuddy.web
4. Check **Sign in with Apple**
5. Click **Configure**
6. Add domains and redirect URLs:
   - Domains: yourdomain.com
   - Return URLs: https://yourdomain.com/oauth/apple/callback
7. Click **Save** > **Continue** > **Register**

#### 3. Create Key

1. Click **Keys** > **+** (to add new)
2. Key Name: StudyBuddy Sign in with Apple Key
3. Check **Sign in with Apple**
4. Click **Configure** > Select your App ID
5. Click **Save** > **Continue** > **Register**
6. **Download the key file** (.p8) - you can only download it once!
7. Note the **Key ID** shown on screen

#### 4. Get Team ID

1. In Apple Developer Portal, click your account name at the top right
2. Note your **Team ID** (e.g., ABCD123456)

#### 5. Configure StudyBuddy

1. Open your `.env` file

2. Add Apple credentials:
   ```bash
   APPLE_CLIENT_ID="com.yourdomain.studybuddy.web"  # Your Services ID
   APPLE_TEAM_ID="ABCD123456"  # Your Team ID
   APPLE_KEY_ID="ABC123XYZ"  # The Key ID from step 3
   APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
   MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
   -----END PRIVATE KEY-----"  # Contents of the .p8 file
   ```
   
   Note: For `APPLE_PRIVATE_KEY`, paste the entire contents of the .p8 file

3. Restart the application

---

## Common Issues

### Error 400: redirect_uri_mismatch (Google)

This is the most common error. It means the redirect URI doesn't match.

**Solution:**

1. Check your `BASE_URL` in `.env`:
   ```bash
   BASE_URL="https://yourdomain.com"  # Make sure this is EXACT
   ```

2. Verify Google Console has the exact redirect URI:
   - Go to Google Cloud Console > Credentials
   - Edit your OAuth Client ID
   - Check Authorized redirect URIs contains:
     ```
     https://yourdomain.com/oauth/google/callback
     ```
   - Make sure there are no typos, extra slashes, or http vs https mismatches

3. Common mistakes:
   - ❌ `BASE_URL="https://yourdomain.com/"` (trailing slash)
   - ✅ `BASE_URL="https://yourdomain.com"` (no trailing slash)
   
   - ❌ Google Console: `http://yourdomain.com/oauth/google/callback` (http)
   - ✅ Google Console: `https://yourdomain.com/oauth/google/callback` (https)
   
   - ❌ `BASE_URL="http://localhost"` but accessing via `http://localhost:5000`
   - ✅ `BASE_URL="http://localhost:5000"` (include port)

4. After fixing, restart the app:
   ```bash
   docker compose restart app
   # OR
   sudo systemctl restart studybuddy
   ```

### Error: OAuth not configured

**Symptoms:** Error message about OAuth not being configured

**Solution:**

1. Verify your `.env` file has the credentials:
   ```bash
   GOOGLE_CLIENT_ID="your-actual-client-id"
   GOOGLE_CLIENT_SECRET="your-actual-secret"
   ```

2. Make sure there are no extra quotes or spaces

3. Restart the application

### Google Sign-In button not showing

**Solution:**

1. Check that credentials are set in `.env`
2. Restart the application
3. Clear browser cache
4. Check browser console for JavaScript errors

### Apple Sign-In not working

**Common issues:**

1. **Invalid client_id:**
   - Make sure `APPLE_CLIENT_ID` matches your Services ID exactly

2. **Invalid key:**
   - Verify the `.p8` file contents are copied correctly into `APPLE_PRIVATE_KEY`
   - Make sure to include the BEGIN and END lines

3. **Domain not verified:**
   - Verify your domain is added in Apple Developer Console

---

## Testing OAuth

### Test Google Sign-In

1. Start your application
2. Go to the login page
3. You should see a "התחבר עם Google" (Sign in with Google) button
4. Click it
5. You should be redirected to Google's sign-in page
6. After signing in, you should be redirected back to StudyBuddy

### Test Apple Sign-In

1. Similar to Google, but click "התחבר עם Apple"
2. Note: Apple Sign-In only works with HTTPS in production

### Debugging

Enable debug logging to see OAuth flow details:

```bash
# In .env
LOG_LEVEL="DEBUG"
```

Check logs:
```bash
# Docker:
docker compose logs app | grep -i oauth

# Systemd:
sudo journalctl -u studybuddy | grep -i oauth
```

---

## Security Notes

1. **Never commit `.env` file** - it contains secrets
2. **Use HTTPS in production** - OAuth requires secure connections
3. **Restrict OAuth scopes** - only request what you need (email, profile)
4. **Rotate secrets regularly** - especially if exposed

---

## Support

If you're still having issues:

1. Check the main [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
2. Review application logs
3. Verify all steps were followed exactly
4. Try with a fresh Google Cloud project if stuck

For redirect_uri_mismatch specifically, 99% of the time it's a mismatch between:
- The `BASE_URL` in your `.env` file
- The Authorized redirect URIs in Google Console

Make absolutely sure these match character-by-character!
