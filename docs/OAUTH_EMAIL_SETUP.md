# OAuth and Email Configuration Guide

This guide explains how to set up Google/Apple Sign-In and email verification for StudyBuddy.

## Email Configuration (SMTP)

Email is required for:
- User email verification
- Password reset
- Admin notifications

### Using Gmail (Recommended)

1. **Enable 2-Factor Authentication** on your Google account

2. **Generate an App Password**:
   - Go to https://myaccount.google.com/security
   - Select "2-Step Verification"
   - Scroll to "App passwords"
   - Generate a new app password for "Mail"
   - Copy the 16-character password

3. **Update `.env` file**:
   ```bash
   MAIL_SERVER="smtp.gmail.com"
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME="your_email@gmail.com"
   MAIL_PASSWORD="your_16_char_app_password"
   MAIL_DEFAULT_SENDER="StudyBuddy <your_email@gmail.com>"
   ```

### Using Other SMTP Providers

**SendGrid:**
```bash
MAIL_SERVER="smtp.sendgrid.net"
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME="apikey"
MAIL_PASSWORD="your_sendgrid_api_key"
```

**Mailgun:**
```bash
MAIL_SERVER="smtp.mailgun.org"
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME="your_mailgun_username"
MAIL_PASSWORD="your_mailgun_password"
```

## Google OAuth Configuration

Google Sign-In allows users to log in with their Google account without creating a password.

### Setup Steps

1. **Create a Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create a new project or select an existing one

2. **Enable Google+ API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     ```
     https://yourdomain.com/oauth/google/callback
     http://localhost:5000/oauth/google/callback  (for development)
     ```
   - Save and copy the Client ID and Client Secret

4. **Update `.env` file**:
   ```bash
   GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your_client_secret"
   BASE_URL="https://yourdomain.com"
   ```

5. **Test the integration**:
   - Restart the application
   - Go to the login page
   - Click "Sign in with Google"

### Important Notes

- The `BASE_URL` in `.env` must match your actual domain
- For production, always use HTTPS
- Users who sign in with Google don't need email verification

## Apple Sign-In Configuration (Optional)

Apple Sign-In allows users to log in with their Apple ID.

### Setup Steps

1. **Enroll in Apple Developer Program** (required):
   - Go to https://developer.apple.com/programs/
   - Enroll ($99/year)

2. **Create an App ID**:
   - Go to https://developer.apple.com/account/resources/identifiers/list
   - Click "+" to create a new identifier
   - Select "App IDs" and continue
   - Enter description and Bundle ID (e.g., `com.yourcompany.studybuddy`)
   - Enable "Sign in with Apple"
   - Save

3. **Create a Services ID** (this is your Client ID):
   - Go back to identifiers list
   - Click "+" to create a new identifier
   - Select "Services IDs" and continue
   - Enter identifier (e.g., `com.yourcompany.studybuddy.service`)
   - Enable "Sign in with Apple"
   - Configure:
     - Primary App ID: Select the App ID you created
     - Domains: `yourdomain.com`
     - Return URLs: `https://yourdomain.com/oauth/apple/callback`
   - Save

4. **Create a Private Key**:
   - Go to "Keys" section
   - Click "+" to create a new key
   - Enter key name
   - Enable "Sign in with Apple"
   - Configure: Select your primary App ID
   - Download the `.p8` file (keep it safe!)
   - Note the Key ID shown

5. **Get your Team ID**:
   - Go to https://developer.apple.com/account/
   - Your Team ID is shown in the top right

6. **Update `.env` file**:
   ```bash
   APPLE_CLIENT_ID="com.yourcompany.studybuddy.service"
   APPLE_TEAM_ID="YOUR_TEAM_ID"
   APPLE_KEY_ID="YOUR_KEY_ID"
   APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
   [contents of your .p8 file]
   -----END PRIVATE KEY-----"
   BASE_URL="https://yourdomain.com"
   ```

7. **Test the integration**:
   - Restart the application
   - Go to the login page
   - Click "Sign in with Apple"

### Important Notes

- Apple Sign-In requires HTTPS in production
- Apple may provide a relay email instead of the user's real email
- The private key should be kept secure and never committed to git

## Testing Email and OAuth

### Test Email Verification

1. Sign up with a new email address
2. Check your inbox for verification email
3. Click the verification link
4. You should be able to log in

### Test Google Sign-In

1. Go to login page
2. Click "Sign in with Google"
3. Select your Google account
4. You should be logged in automatically

### Test Apple Sign-In

1. Go to login page
2. Click "Sign in with Apple"
3. Authenticate with Face ID/Touch ID/Password
4. You should be logged in automatically

## Troubleshooting

### Email Not Sending

1. Check `.env` configuration
2. Verify SMTP credentials are correct
3. Check application logs: `docker compose logs app`
4. For Gmail, ensure app password is used, not regular password
5. Check firewall allows outbound SMTP connections

### Google OAuth Not Working

1. Verify redirect URI matches exactly
2. Check `BASE_URL` in `.env` is correct
3. Ensure HTTPS is enabled in production
4. Check browser console for JavaScript errors
5. Verify Google+ API is enabled

### Apple Sign-In Not Working

1. Verify all identifiers are correct
2. Check private key is properly formatted in `.env`
3. Ensure HTTPS is enabled
4. Check return URL matches exactly
5. Verify Apple Developer subscription is active

## Security Best Practices

1. **Never commit credentials**:
   - Add `.env` to `.gitignore`
   - Use environment variables in production

2. **Use HTTPS in production**:
   - Required for OAuth
   - Protects user credentials

3. **Rotate secrets regularly**:
   - Change SMTP passwords periodically
   - Regenerate OAuth secrets if compromised

4. **Monitor login attempts**:
   - Check logs for suspicious activity
   - Set up alerts for failed logins

5. **Keep dependencies updated**:
   - Update `authlib` and security packages
   - Monitor for security advisories

## Need Help?

- Check application logs: `docker compose logs -f app`
- Test with curl: `curl -v https://yourdomain.com/health`
- Verify DNS: `dig yourdomain.com`
- Check firewall: `sudo ufw status`

For more help, open an issue on GitHub.
