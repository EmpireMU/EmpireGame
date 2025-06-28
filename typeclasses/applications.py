"""
Application script for handling character applications.
"""
from evennia import DefaultScript

class Application(DefaultScript):
    """
    This script handles character applications.
    It stores the application data and provides methods for staff to review.
    """
    
    def at_script_creation(self):
        """
        Setup the script
        """
        self.key = "application_unnamed"
        self.desc = "Character application"
        self.interval = None  # Not a repeating script
        self.persistent = True
        
        # Initialize storage attributes
        self.db.email = ""
        self.db.char_name = ""
        self.db.app_text = ""
        self.db.ip_address = ""
        self.db.status = "pending"  # pending, approved, rejected
        self.db.reviewer = None
        self.db.review_notes = ""
        self.db.review_date = None
        
    def approve(self, reviewer, notes=""):
        """
        Approve the application
        
        Args:
            reviewer (Account): The staff member approving
            notes (str, optional): Any notes about the approval
        """
        from django.utils import timezone
        self.db.status = "approved"
        self.db.reviewer = reviewer
        self.db.review_notes = notes
        self.db.review_date = timezone.now()
        
    def reject(self, reviewer, notes=""):
        """
        Reject the application
        
        Args:
            reviewer (Account): The staff member rejecting
            notes (str, optional): Reason for rejection
        """
        from django.utils import timezone
        self.db.status = "rejected"
        self.db.reviewer = reviewer
        self.db.review_notes = notes
        self.db.review_date = timezone.now()

    def get_display_name(self, looker=None, **kwargs):
        """
        Returns the display name of the application - used in listings.
        """
        return f"Application #{self.id}: {self.db.char_name}" 