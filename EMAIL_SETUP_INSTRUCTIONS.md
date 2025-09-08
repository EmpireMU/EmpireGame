# Email Automation Setup Instructions

## Mailgun Web API Configuration

### 1. Mailgun Account Setup

1. **Sign up at mailgun.com** (free tier: 100 emails/day, 3,000/month)

2. **Verify your email address**

3. **Get your API Key**:
   - Go to Settings → API Keys
   - Copy your "Private API key" (starts with `key-`)

4. **Get your domain**:
   - Go to Sending → Domains  
   - Use the sandbox domain (like `sandbox123.mailgun.org`) for free tier
   - Or add your own domain for production

### 2. Update Secret Settings

Add the following to your `server/conf/secret_settings.py` file:

```python
# Mailgun Web API Configuration
MAILGUN_API_KEY = 'key-your-actual-api-key-here'  # Replace with your Mailgun API key
MAILGUN_DOMAIN = 'sandbox123.mailgun.org'         # Replace with your Mailgun domain

# Update the from email addresses (use your Mailgun domain)
DEFAULT_FROM_EMAIL = 'Empire MUSH <noreply@sandbox123.mailgun.org>'
SERVER_EMAIL = 'Empire MUSH <noreply@sandbox123.mailgun.org>'
```

### 3. No Extra Packages Needed

Mailgun uses standard HTTP requests (via the `requests` library), which is already in your requirements.txt.

### 4. Test the Configuration

1. Start your server with production settings:
   ```
   evennia start --settings=production_settings
   ```

2. Test by approving an actual application to see if the email is sent

### 4. Application Workflow

The new automated workflow works as follows:

**For Approved Applications:**
1. `application/approve <id>` 
2. System finds existing account for that character (created with @createplayer)
3. System sends email with password reset link
4. Player clicks link to set their password
5. Player can then log in normally

**For Declined Applications:**
1. `application/decline <id>`
2. System sends polite decline email

### 5. Development vs Production

- **Development**: Emails are printed to console (no real sending)
- **Production**: Emails are sent via Outlook SMTP

### 6. Security Notes

- Your Outlook password should be kept secret
- Consider using a dedicated Outlook account rather than your personal one
- 2FA is recommended but not required for SMTP to work

### 7. Troubleshooting

**"Authentication failed" errors:**
- Verify you're using the correct Outlook password
- Check that the email address in settings matches exactly
- Make sure the account isn't locked or suspended

**Emails not being received:**
- Check spam/junk folders
- Use the test command to verify configuration
- Check server logs for error messages

**Password reset links not working:**
- Verify `WEB_PROFILE_DOMAIN` is set correctly in settings
- Ensure your web server is configured for HTTPS
- Check that Django's password reset URLs are properly configured
