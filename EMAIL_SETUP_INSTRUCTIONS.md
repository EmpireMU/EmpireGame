# Email Automation Setup Instructions

## Outlook SMTP Configuration

### 1. Outlook Account Setup

1. **Create or use an Outlook/Hotmail account** for your MUD (recommended: something like `empiremush@outlook.com`)

2. **Enable 2-Factor Authentication** (recommended for security):
   - Go to Microsoft account security settings
   - Turn on two-step verification

3. **No app passwords needed** - just use your regular Outlook password!

### 2. Update Secret Settings

Add the following to your `server/conf/secret_settings.py` file:

```python
# Outlook SMTP Configuration
EMAIL_HOST_USER = 'your-outlook@outlook.com'  # Replace with your Outlook address
EMAIL_HOST_PASSWORD = 'your-outlook-password'  # Replace with your regular Outlook password

# Update the from email addresses
DEFAULT_FROM_EMAIL = 'Empire MUSH <your-outlook@outlook.com>'
SERVER_EMAIL = 'Empire MUSH <your-outlook@outlook.com>'
```

### 3. Test the Configuration

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
