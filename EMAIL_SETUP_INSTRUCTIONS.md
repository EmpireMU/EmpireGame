# Email Automation Setup Instructions

## Gmail SMTP Configuration

### 1. Gmail Account Setup

1. **Create or use a dedicated Gmail account** for your MUD (recommended: something like `empiremush@gmail.com`)

2. **Enable 2-Factor Authentication** on the Gmail account:
   - Go to Google Account settings → Security
   - Turn on 2-Step Verification

3. **Generate an App Password**:
   - Go to Google Account settings → Security → App passwords
   - Select "Mail" and "Other (custom name)"
   - Enter "Empire MUSH" as the name
   - Google will generate a 16-character app password
   - **Save this password** - you'll need it for the configuration

### 2. Update Secret Settings

Add the following to your `server/conf/secret_settings.py` file:

```python
# Gmail SMTP Configuration
EMAIL_HOST_USER = 'your-gmail@gmail.com'  # Replace with your Gmail address
EMAIL_HOST_PASSWORD = 'your-app-password'  # Replace with the 16-character app password

# Update the from email addresses
DEFAULT_FROM_EMAIL = 'Empire MUSH <your-gmail@gmail.com>'
SERVER_EMAIL = 'Empire MUSH <your-gmail@gmail.com>'
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
- **Production**: Emails are sent via Gmail SMTP

### 6. Security Notes

- The Gmail app password should be kept secret
- App passwords are specific to the application and can be revoked if needed
- Regular Gmail passwords won't work with SMTP - you must use an app password
- Consider using a dedicated Gmail account rather than your personal one

### 7. Troubleshooting

**"Authentication failed" errors:**
- Check that 2FA is enabled on the Gmail account
- Verify you're using the app password, not the regular password
- Check that the email address in settings matches exactly

**Emails not being received:**
- Check spam/junk folders
- Use the test command to verify configuration
- Check server logs for error messages

**Password reset links not working:**
- Verify `WEB_PROFILE_DOMAIN` is set correctly in settings
- Ensure your web server is configured for HTTPS
- Check that Django's password reset URLs are properly configured
