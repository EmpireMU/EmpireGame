# Empire Improvements Todo

## High Priority (Before Launch)

### ✅ Email Automation - COMPLETED  
- **Was:** Manual password generation and emailing
- **Now:** Automated approval/decline emails with Django password reset links
- **Features:** Mailgun API integration, automated password reset, zero manual work
- **Benefit:** Professional email delivery, secure password reset, staff efficiency

### ✅ Application Audit Trail - COMPLETED
- **Was:** Delete application scripts after processing
- **Now:** Applications marked as "approved"/"rejected" with full audit trail
- **Benefit:** Prevents duplicate applications, provides history, eliminates ID waste
- **Added:** Smart filtering (pending/approved/declined/all) for performance

### ✅ Better Account Tracking - COMPLETED (Analysis Phase)
- **Was:** Store just email strings in applications with no cross-reference capability
- **Now:** `checkemails` command provides cross-email IP analysis and application pattern detection
- **Benefit:** Multi-accounting detection, shared IP warnings, complete application history
- **Added:** ASCII-friendly output compatible with all MUD clients
- **Note:** Still uses email-based tracking; true account linking could be post-launch enhancement

## Medium Priority (Post-Launch)

### True Account Linking
- **Current:** Applications track emails, analysis via `checkemails` command
- **Enhancement:** Link applications directly to Account objects (account_id, username)
- **Benefit:** Robust tracking across email changes, account transfers
- **Time:** 15-20 minutes to modify application creation

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
