# Empire Improvements Todo

## High Priority (Before Launch)

### Email Automation
- **Current:** Manual password generation and emailing
- **Improvement:** Configure Gmail SMTP + Django password reset links
- **Benefit:** Eliminates manual work, more secure, professional experience
- **Time:** 30 minutes setup

### Application Audit Trail  
- **Current:** Delete application scripts after processing
- **Improvement:** Set `app.db.status = "approved"` instead of `app.delete()`
- **Benefit:** Prevents duplicate applications, provides history
- **Time:** 5 minutes

### Better Account Tracking
- **Current:** Store just email strings in applications
- **Improvement:** Store structured account info (account_id, username, email)
- **Benefit:** Better tracking even if accounts change hands
- **Time:** 10 minutes

## Medium Priority (Post-Launch)

### Basic Scene Logging
- **Add:** Simple RP logging to emit/pose commands using room attributes
- **Benefit:** Players can review recent RP, staff oversight
- **Implementation:** Hook existing commands, store in room.db.scene_log
- **Time:** 1-2 hours for basic version

### Web Application Form
- **Consider:** Web form with reCAPTCHA instead of guest applications  
- **Benefit:** Better mobile experience, reduces spam concerns
- **Time:** 2-3 hours

## Low Priority (Only If Requested)

### Enhanced Image Handling
- **Improvement:** Create multiple image sizes on upload (300px, 150px, 75px)
- **Benefit:** Better performance, more flexible display

### Better Error Messages
- **Improvement:** More specific validation and user feedback
- **Benefit:** Improved user experience

## Implementation Notes

- Focus on **simple, maintainable solutions**
- Stick to **Evennia conventions** where possible
- **Content creation** remains the top priority
- Only add complexity when players actually request features

## Launch Target: October 31, 2025
