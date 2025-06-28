"""
Request system for player-staff communication.

This module implements a ticket/request system allowing players to create
requests that staff can review and respond to.
"""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.utils import datetime_format
from evennia.utils.search import search_script
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Valid request statuses
VALID_STATUSES = ["Open", "In Progress", "Closed"]

# Default request categories
DEFAULT_CATEGORIES = ["Bug", "Feature", "Question", "Character", "General"]

class Request(DefaultScript):
    """
    A request/ticket in the request system.
    
    This typeclass defines the basic properties and data storage for requests.
    All workflow logic is handled by RequestManager.
    """
    
    def at_script_creation(self):
        """Set up the basic properties of the request."""
        super().at_script_creation()
        
        now = datetime.now()
        
        # Basic properties using Evennia's attribute system
        self.db.id = None  # Set by manager
        self.db.title = ""
        self.db.text = ""
        self.db.submitter = None
        self.db.assigned_to = None
        self.db.date_created = now
        self.db.date_modified = now
        self.db.comments = []
        self.db.resolution = ""
        self.db.date_closed = None
        self.db.date_archived = None
        self.db.status = "Open"
        self.db.category = "General"
        self.db.last_viewed_by = {}  # Dict mapping account -> timestamp
        
        # Make sure this script never repeats or times out
        self.interval = -1
        self.persistent = True

    @property
    def status(self):
        """Get the current status."""
        return self.db.status
        
    @property
    def category(self):
        """Get the current category."""
        return self.db.category
        
    @property
    def is_closed(self):
        """Check if the request is closed."""
        return self.status == "Closed"
        
    @property
    def is_archived(self):
        """Check if the request is archived."""
        return bool(self.db.date_archived)
        
    def set_status(self, new_status):
        """Change the request status.
        
        Args:
            new_status (str): The new status to set
        Raises:
            ValueError: If status is not valid
        """
        # Case-insensitive status matching
        status_match = next((valid for valid in VALID_STATUSES if valid.lower() == new_status.lower()), None)
        if not status_match:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
            
        old_status = self.status
        self.db.status = status_match  # Use the correctly-cased status
        self.db.date_modified = datetime.now()
        if status_match == "Closed":
            self.db.date_closed = datetime.now()
            
        self.notify_all(f"Status changed from {old_status} to {status_match}")
        
    def set_category(self, new_category):
        """Change the request category.
        
        Args:
            new_category (str): The new category
        Raises:
            ValueError: If category is not valid
        """
        if new_category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(DEFAULT_CATEGORIES)}")
            
        old_category = self.category
        self.db.category = new_category
        self.db.date_modified = datetime.now()
        self.notify_all(f"Category changed from {old_category} to {new_category}")
        
    def assign_to(self, staff_account):
        """Assign the request to a staff member.
        
        Args:
            staff_account (AccountDB): The staff account to assign to
        """
        old_assigned = self.db.assigned_to
        self.db.assigned_to = staff_account
        self.db.date_modified = datetime.now()
        
        msg = f"Assigned to {staff_account.name}"
        if old_assigned:
            msg = f"Reassigned from {old_assigned.name} to {staff_account.name}"
        self.notify_all(msg)
        
    def add_comment(self, author, text):
        """Add a comment to the request.
        
        Args:
            author (AccountDB): The account adding the comment
            text (str): The comment text
        """
        if not text.strip():
            raise ValueError("Comment text cannot be empty")
            
        comment = {
            "author": author,
            "text": text.strip(),
            "date": datetime.now()
        }
        
        if not self.db.comments:
            self.db.comments = []
            
        self.db.comments.append(comment)
        self.db.date_modified = datetime.now()
        self.notify_all(f"New comment by {author.name}")
        
    def get_comments(self):
        """Get all comments on this request."""
        return self.db.comments or []
        
    def archive(self):
        """Archive this request."""
        if self.is_archived:
            raise ValueError("Request is already archived")
            
        self.db.date_archived = datetime.now()
        self.db.date_modified = datetime.now()
        self.notify_all("This request has been archived.")
        
    def unarchive(self):
        """Unarchive this request."""
        if not self.is_archived:
            raise ValueError("Request is not archived")
            
        self.db.date_archived = None
        self.db.date_modified = datetime.now()
        self.notify_all("This request has been unarchived.")
        
    def notify_all(self, message, exclude_account=None):
        """
        Send a notification to all relevant parties.
        
        Args:
            message (str): The message to send
            exclude_account (AccountDB, optional): Account to exclude from notification
        """
        # Notify submitter if not excluded
        if self.db.submitter and self.db.submitter != exclude_account:
            if self.db.submitter.is_connected:
                self.db.submitter.msg(f"[Request #{self.db.id}] {message}")
            else:
                self.store_offline_notification(self.db.submitter, message)
                
        # Notify assigned staff member if different from submitter
        if self.db.assigned_to and self.db.assigned_to != self.db.submitter and self.db.assigned_to != exclude_account:
            if self.db.assigned_to.is_connected:
                self.db.assigned_to.msg(f"[Request #{self.db.id}] {message}")
            else:
                self.store_offline_notification(self.db.assigned_to, message)
                
    def store_offline_notification(self, account, message):
        """Store a notification for an offline user."""
        if not account:
            return
            
        notifications = account.db.offline_request_notifications or []
        notifications.append(f"[Request #{self.db.id}] {message}")
        account.db.offline_request_notifications = notifications
        
    @classmethod
    def get_or_create_handler(cls):
        """Get the request handler object."""
        # This is a compatibility method for the old system
        # It's not needed anymore since we're using objects directly
        return None 

    def migrate_category(self):
        """
        Migrate the request's category to a valid one if it's no longer valid.
        Returns True if migration was needed, False otherwise.
        """
        if self.db.category not in DEFAULT_CATEGORIES:
            old_category = self.db.category
            self.db.category = "General"
            self.db.date_modified = datetime.now()
            self.notify_all(f"Category migrated from {old_category} to General (old category no longer valid)")
            return True
        return False

    @classmethod
    def migrate_all_categories(cls):
        """
        Migrate all requests with invalid categories to use valid ones.
        Returns the number of requests that were migrated.
        """
        count = 0
        for request in search_script("typeclasses.requests.Request"):
            if request.migrate_category():
                count += 1
        return count 

    def set_resolution(self, text):
        """Set the resolution text for this request.
        
        Args:
            text (str): The resolution text
        Raises:
            ValueError: If text is empty
        """
        if not text.strip():
            raise ValueError("Resolution text cannot be empty")
            
        self.db.resolution = text.strip()
        self.db.date_modified = datetime.now()
        self.notify_all("Resolution added to request")

    def store_comment(self, author, text, date=None):
        """Store a comment in the request.
        
        Args:
            author (AccountDB): The account adding the comment
            text (str): The comment text
            date (datetime, optional): Comment date, defaults to now
        Raises:
            ValueError: If text is empty
        """
        if not text.strip():
            raise ValueError("Comment text cannot be empty")
            
        comment = {
            "author": author,
            "text": text.strip(),
            "date": date or datetime.now()
        }
        
        if not self.db.comments:
            self.db.comments = []
            
        self.db.comments.append(comment)
        self.db.date_modified = datetime.now()
        return comment
        
    def store_assignment(self, staff_account):
        """Store staff assignment.
        
        Args:
            staff_account (AccountDB): The staff account to assign
        Returns:
            tuple: (old_assigned, new_assigned) for notification purposes
        """
        old_assigned = self.db.assigned_to
        self.db.assigned_to = staff_account
        self.db.date_modified = datetime.now()
        return (old_assigned, staff_account)
        
    def set_archived(self, archived=True):
        """Set the archived status.
        
        Args:
            archived (bool): Whether to archive (True) or unarchive (False)
        Raises:
            ValueError: If already in requested state
        """
        if archived and self.is_archived:
            raise ValueError("Request is already archived")
        if not archived and not self.is_archived:
            raise ValueError("Request is not archived")
            
        self.db.date_archived = datetime.now() if archived else None
        self.db.date_modified = datetime.now()
        
    @property
    def participants(self):
        """Get all participants who should receive notifications.
        
        Returns:
            list: List of (account, is_connected) tuples
        """
        participants = []
        
        # Add submitter
        if self.db.submitter:
            participants.append((self.db.submitter, self.db.submitter.is_connected))
            
        # Add assigned staff if different from submitter
        if self.db.assigned_to and self.db.assigned_to != self.db.submitter:
            participants.append((self.db.assigned_to, self.db.assigned_to.is_connected))
            
        return participants 

    def has_new_activity(self, account):
        """Check if there has been new activity since last viewed.
        
        Args:
            account (AccountDB): The account to check for
            
        Returns:
            bool: True if there has been new activity, False otherwise
        """
        if not account:
            return False
            
        # Get the last_viewed_by dict, creating an empty one if it doesn't exist
        last_viewed_by = self.attributes.get('last_viewed_by', default={})
        
        # Use account.id as the key
        last_viewed = last_viewed_by.get(str(account.id))
        if not last_viewed:
            return True
            
        return self.db.date_modified > last_viewed

    def mark_viewed(self, account):
        """Mark the request as viewed by an account.
        
        Args:
            account (AccountDB): The account that viewed the request
        """
        if account:
            # Get current dict or create new one
            last_viewed_by = self.attributes.get('last_viewed_by', default={})
            # Update the timestamp
            last_viewed_by[str(account.id)] = datetime.now()
            # Save back to attributes
            self.attributes.add('last_viewed_by', last_viewed_by)

    @classmethod
    def cleanup_old_requests(cls, days=30):
        """Delete archived requests older than specified days.
        
        Args:
            days (int): Number of days after which to delete archived requests
            
        Returns:
            int: Number of requests deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        count = 0
        
        # Search for all requests
        for request in search_script("typeclasses.requests.Request"):
            # Only delete if:
            # 1. Request is archived
            # 2. Archive date is older than cutoff
            # 3. Request is closed (safety check)
            if (request.is_archived and 
                request.db.date_archived and 
                request.db.date_archived < cutoff_date and
                request.is_closed):
                request.delete()
                count += 1
                
        return count 