# Email Automation Setup Instructions

## SendGrid SMTP Configuration

### 1. SendGrid Account Setup

1. **Sign up at sendgrid.com** (free tier: 100 emails/day)

2. **Verify your email address**

3. **Create an API Key**:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Choose "Restricted Access"
   - Enable only "Mail Send" permissions
   - Copy the API key (starts with `SG.`)

4. **Verify your sender email**:
   - Go to Settings → Sender Authentication
   - Use "Single Sender Verification"
   - Verify an email address you control (this will be your "from" address)

### 2. Update Secret Settings

Add the following to your `server/conf/secret_settings.py` file:

```python
# SendGrid Web API Configuration
SENDGRID_API_KEY = 'SG.your-actual-api-key-here'  # Replace with your SendGrid API key

# Update the from email addresses (must be verified in SendGrid)
DEFAULT_FROM_EMAIL = 'Empire MUSH <your-verified-email@yourdomain.com>'
SERVER_EMAIL = 'Empire MUSH <your-verified-email@yourdomain.com>'
```

### 3. Install SendGrid Package

```bash
pip install sendgrid
```

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
