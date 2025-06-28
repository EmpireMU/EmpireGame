"""
Manager class for handling request workflow logic.
"""

from evennia.scripts.models import ScriptDB
from evennia import create_script
from datetime import datetime, timedelta
from typeclasses.requests import Request, VALID_STATUSES, DEFAULT_CATEGORIES

class RequestManager:
    """Handles request workflow logic."""
    
    @classmethod
    def notify_update(cls, request, message, exclude_account=None):
        """Send a notification about a request update.
        
        Args:
            request (Request): The request being updated
            message (str): The message to send
            exclude_account (AccountDB, optional): Account to exclude from notification
        """
        # Get participants (submitter and assigned staff if different)
        participants = []
        if request.db.submitter:
            participants.append((request.db.submitter, request.db.submitter.is_connected))
        if request.db.assigned_to and request.db.assigned_to != request.db.submitter:
            participants.append((request.db.assigned_to, request.db.assigned_to.is_connected))
            
        # Send notifications
        for account, is_connected in participants:
            if account == exclude_account:
                continue
                
            if is_connected:
                account.msg(f"[Request #{request.db.id}] {message}")
            else:
                # Store offline notification
                notifications = account.db.offline_request_notifications or []
                notifications.append(f"[Request #{request.db.id}] {message}")
                account.db.offline_request_notifications = notifications
    
    @classmethod
    def create(cls, title, text, submitter):
        """Create a new request.
        
        Args:
            title (str): Request title
            text (str): Request text
            submitter (AccountDB): Account creating the request
            
        Returns:
            Request: The created request
        
        Raises:
            ValueError: If title or text is empty
        """
        if not title.strip():
            raise ValueError("Request title cannot be empty")
        if not text.strip():
            raise ValueError("Request text cannot be empty")
            
        request = create_script(
            "typeclasses.requests.Request",
            key=f"Request-{cls.get_next_id()}"
        )
        
        if not request:
            raise RuntimeError("Failed to create request")
            
        request.db.id = cls.get_next_id()
        request.db.title = title.strip()
        request.db.text = text.strip()
        request.db.submitter = submitter
        
        cls.notify_update(request, f"New request created: {title[:50]}{'...' if len(title) > 50 else ''}")
        return request
        
    @classmethod
    def get_next_id(cls):
        """Get the next available request ID."""
        requests = ScriptDB.objects.filter(db_typeclass_path__contains="requests.Request")
        if not requests.exists():
            return 1
            
        max_id = 0
        for request in requests:
            try:
                if request.db.id and request.db.id > max_id:
                    max_id = request.db.id
            except AttributeError:
                continue
                
        return max_id + 1
        
    @classmethod
    def add_comment(cls, request, author, text):
        """Add a comment to a request.
        
        Args:
            request (Request): The request to comment on
            author (AccountDB): The account adding the comment
            text (str): The comment text
            
        Raises:
            ValueError: If text is empty
        """
        if not text.strip():
            raise ValueError("Comment text cannot be empty")
            
        comment = {
            "author": author,
            "text": text.strip(),
            "date": datetime.now()
        }
        
        if not request.db.comments:
            request.db.comments = []
            
        request.db.comments.append(comment)
        request.db.date_modified = datetime.now()
        
        cls.notify_update(request, f"New comment by {author.name}")
        
    @classmethod
    def assign(cls, request, staff_account):
        """Assign a request to staff.
        
        Args:
            request (Request): The request to assign
            staff_account (AccountDB): Staff account to assign to
        """
        old_assigned = request.db.assigned_to
        request.db.assigned_to = staff_account
        request.db.date_modified = datetime.now()
        
        msg = f"Assigned to {staff_account.name}"
        if old_assigned:
            msg = f"Reassigned from {old_assigned.name} to {staff_account.name}"
        cls.notify_update(request, msg)
        
    @classmethod
    def set_status(cls, request, new_status):
        """Change request status.
        
        Args:
            request (Request): The request to update
            new_status (str): The new status
            
        Raises:
            ValueError: If status is invalid
        """
        # Case-insensitive status matching
        status_match = next((valid for valid in VALID_STATUSES if valid.lower() == new_status.lower()), None)
        if not status_match:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
            
        old_status = request.status
        request.db.status = status_match  # Use the correctly-cased status
        request.db.date_modified = datetime.now()
        
        if status_match == "Closed":
            request.db.date_closed = datetime.now()
            # Automatically archive closed requests
            request.db.date_archived = datetime.now()
            cls.notify_update(request, f"Status changed from {old_status} to {status_match} and request has been archived")
        else:
            cls.notify_update(request, f"Status changed from {old_status} to {status_match}")
        
    @classmethod
    def set_category(cls, request, new_category):
        """Change request category.
        
        Args:
            request (Request): The request to update
            new_category (str): The new category
            
        Raises:
            ValueError: If category is invalid
        """
        if new_category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(DEFAULT_CATEGORIES)}")
            
        old_category = request.category
        request.db.category = new_category
        request.db.date_modified = datetime.now()
        
        cls.notify_update(request, f"Category changed from {old_category} to {new_category}")
        
    @classmethod
    def set_archived(cls, request, archived=True):
        """Set request archived status.
        
        Args:
            request (Request): The request to update
            archived (bool): Whether to archive or unarchive
            
        Raises:
            ValueError: If already in requested state
        """
        if archived and request.is_archived:
            raise ValueError("Request is already archived")
        if not archived and not request.is_archived:
            raise ValueError("Request is not archived")
            
        request.db.date_archived = datetime.now() if archived else None
        request.db.date_modified = datetime.now()
        
        msg = "Request has been archived" if archived else "Request has been unarchived"
        cls.notify_update(request, msg)
        
    @classmethod
    def set_resolution(cls, request, text):
        """Set request resolution.
        
        Args:
            request (Request): The request to update
            text (str): The resolution text
            
        Raises:
            ValueError: If text is empty
        """
        if not text.strip():
            raise ValueError("Resolution text cannot be empty")
            
        request.db.resolution = text.strip()
        request.db.date_modified = datetime.now()
        cls.notify_update(request, "Resolution added to request")
        
    @classmethod
    def get_participants(cls, request):
        """Get request participants.
        
        Args:
            request (Request): The request to check
            
        Returns:
            list: List of (account, is_connected) tuples
        """
        participants = []
        
        if request.db.submitter:
            participants.append((request.db.submitter, request.db.submitter.is_connected))
            
        if request.db.assigned_to and request.db.assigned_to != request.db.submitter:
            participants.append((request.db.assigned_to, request.db.assigned_to.is_connected))
            
        return participants 