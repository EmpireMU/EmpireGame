"""
Tests for the request system.
"""

from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from evennia.scripts.scripts import DefaultScript
from commands.requests import CmdRequest
from typeclasses.requests import Request, VALID_STATUSES, DEFAULT_CATEGORIES
from datetime import datetime, timedelta
from evennia import create_script

class TestRequest(EvenniaTest):
    """Test cases for request functionality."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Set up command
        self.cmd = CmdRequest()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        
        # Set up message mocking
        self.caller = self.char1
        self.caller.msg = MagicMock()
        self.cmd.msg = self.caller.msg
        
        # Create a test request
        self.request = create_script(
            "typeclasses.requests.Request",
            key=f"Request-1",  # Use consistent key format
            desc="A test request"
        )
        
        # Initialize request properties
        self.request.db.id = 1
        self.request.db.title = "Test Request"
        self.request.db.text = "This is a test request."
        self.request.db.submitter = self.account
        self.request.db.date_created = datetime.now()
        self.request.db.date_modified = datetime.now()
        self.request.db.status = "Open"
        self.request.db.category = "General"
        self.request.db.comments = []
        self.request.db.resolution = ""
        self.request.db.date_closed = None
        self.request.db.date_archived = None
        self.request.db.assigned_to = None
        
        # Initialize command properties
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.lhs = ""
        self.cmd.rhs = ""
        
        # Give admin permissions for staff-only actions
        self.caller.permissions.add("Admin")
        
    def test_request_creation(self):
        """Test creating a new request."""
        # Set up command arguments
        self.cmd.switches = ["new"]
        self.cmd.args = "New Request=This is a new request."
        self.cmd.lhs = "New Request"
        self.cmd.rhs = "This is a new request."
        
        # Run the command
        self.cmd.func()
        
        # Verify request was created
        requests = Request.objects.filter(db_key__startswith="Request-")
        self.assertTrue(len(requests) > 0)
        
        # Get the latest request
        request = requests.latest('id')
        
        # Verify request properties
        self.assertEqual(request.db.title, "New Request")
        self.assertEqual(request.db.text, "This is a new request.")
        self.assertEqual(request.db.submitter, self.account)
        self.assertEqual(request.db.status, "Open")
        self.assertEqual(request.db.category, "General")
        
    def test_request_creation_validation(self):
        """Test request creation validation."""
        # Test missing text (empty rhs)
        self.cmd.switches = ["new"]
        self.cmd.args = "Test Title="
        self.cmd.lhs = "Test Title"
        self.cmd.rhs = ""
        self.cmd.func()
        self.caller.msg.assert_called_with("Usage: request/new <title>=<text>")
        
        # Test missing title (empty lhs)
        self.caller.msg.reset_mock()
        self.cmd.args = "=Test text"
        self.cmd.lhs = ""
        self.cmd.rhs = "Test text"
        self.cmd.func()
        self.caller.msg.assert_called_with("Request title cannot be empty")
        
        # Test whitespace-only title
        self.caller.msg.reset_mock()
        self.cmd.args = "   =Test text"
        self.cmd.lhs = "   "
        self.cmd.rhs = "Test text"
        self.cmd.func()
        self.caller.msg.assert_called_with("Request title cannot be empty")
        
        # Test whitespace-only text
        self.caller.msg.reset_mock()
        self.cmd.args = "Test Title=   "
        self.cmd.lhs = "Test Title"
        self.cmd.rhs = "   "
        self.cmd.func()
        self.caller.msg.assert_called_with("Request text cannot be empty")
        
    def test_status_changes(self):
        """Test changing request status."""
        # Set up command arguments
        self.cmd.switches = ["status"]
        self.cmd.args = "1=In Progress"
        self.cmd.lhs = "1"  # Request ID
        self.cmd.rhs = "In Progress"  # New status
        
        # Run the command
        self.cmd.func()
        
        # Verify status change
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(request.db.status, "In Progress")
        
    def test_status_workflow(self):
        """Test complete status workflow and restrictions."""
        # Test invalid status
        self.cmd.switches = ["status"]
        self.cmd.args = "1=Invalid Status"
        self.cmd.lhs = "1"
        self.cmd.rhs = "Invalid Status"
        self.cmd.func()
        self.caller.msg.assert_called_with(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        
        # Create a request owned by another user
        other_request = create_script(
            "typeclasses.requests.Request",
            key="Request-2"
        )
        other_request.db.id = 2
        other_request.db.submitter = self.account2
        other_request.db.title = "Other Request"
        other_request.db.text = "Another test request"
        other_request.db.status = "Open"
        other_request.db.category = "General"
        other_request.db.date_created = datetime.now()
        other_request.db.date_modified = datetime.now()
        other_request.db.comments = []
        other_request.db.resolution = ""
        other_request.db.date_closed = None
        other_request.db.date_archived = None
        other_request.db.assigned_to = None
        
        # Reset mock and set up non-staff user
        self.caller.msg.reset_mock()
        # Remove all staff permissions
        for perm in self.caller.permissions.all():
            self.caller.permissions.remove(perm)
        self.caller.account = self.account2  # Set the caller's account to match other_request's submitter
        
        # Test non-staff trying to set status on another user's request (Request-1)
        self.cmd.args = "1=In Progress"
        self.cmd.lhs = "1"
        self.cmd.rhs = "In Progress"
        self.cmd.func()
        self.caller.msg.assert_called_with("You don't have permission to change request status.")
        
        # Reset mock and set up for own request
        self.caller.msg.reset_mock()
        self.caller.account = self.account  # Set back to original account
        
        # Make sure request is still open and owned by the current account
        request = Request.objects.get(db_key="Request-1")
        request.db.status = "Open"
        request.db.submitter = self.account
        
        # Test non-staff trying to set non-closed status on own request
        self.cmd.args = "1=In Progress"
        self.cmd.lhs = "1"
        self.cmd.rhs = "In Progress"
        self.cmd.func()
        self.caller.msg.assert_called_with("You can only close your own requests.")
        
        # Reset mock
        self.caller.msg.reset_mock()
        
        # Test non-staff closing their own request
        self.cmd.args = "1=Closed"
        self.cmd.lhs = "1"
        self.cmd.rhs = "Closed"
        self.cmd.func()
        # Should succeed since it's their own request
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(request.db.status, "Closed")
        self.assertIsNotNone(request.db.date_archived)  # Should be auto-archived
        
        # Clean up
        other_request.delete()
        
        # Reset permissions for other tests
        self.caller.permissions.add("Admin")
        
    def test_comments(self):
        """Test adding and retrieving comments."""
        # Set up command arguments
        self.cmd.switches = ["comment"]
        self.cmd.args = "1=Test comment"
        self.cmd.lhs = "1"  # Request ID
        self.cmd.rhs = "Test comment"
        
        # Run the command
        self.cmd.func()
        
        # Verify comment was added
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(len(request.db.comments), 1)
        self.assertEqual(request.db.comments[0]["text"], "Test comment")
        self.assertEqual(request.db.comments[0]["author"], self.account)
        
    def test_assignment(self):
        """Test assigning requests."""
        # Set up command arguments
        self.cmd.switches = ["assign"]
        self.cmd.args = f"1={self.account.username}"  # Use username instead of ID
        self.cmd.lhs = "1"  # Request ID
        self.cmd.rhs = self.account.username
        
        # Run the command
        self.cmd.func()
        
        # Verify assignment
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(request.db.assigned_to, self.account)
        
    def test_archiving(self):
        """Test archiving and unarchiving requests."""
        # First verify request starts unarchived
        self.assertIsNone(self.request.db.date_archived)
        
        # Close the request which should auto-archive it
        self.cmd.switches = ["close"]
        self.cmd.args = "1=Test resolution"
        self.cmd.lhs = "1"
        self.cmd.rhs = "Test resolution"
        self.cmd.func()
        
        # Verify request is closed and archived
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(request.db.status, "Closed")
        self.assertIsNotNone(request.db.date_archived)
        
        # Test viewing archived requests
        self.cmd.switches = ["archive"]
        self.cmd.args = ""
        self.cmd.func()
        
        # Verify message was sent (list of archived requests)
        self.assertTrue(self.caller.msg.called)
        
    def test_permissions(self):
        """Test permission checks."""
        # Create a request owned by another user
        other_request = create_script(
            "typeclasses.requests.Request",
            key="Request-2"
        )
        other_request.db.id = 2
        other_request.db.submitter = self.account2
        other_request.db.status = "Open"
        
        # Remove admin permissions
        self.caller.permissions.remove("Admin")
        
        # Store original status
        original_status = other_request.db.status
        
        # Try to close someone else's request
        self.cmd.switches = ["status"]
        self.cmd.args = "2=Closed"
        self.cmd.func()
        
        # Verify request was not modified
        self.assertEqual(other_request.db.status, original_status)
        
        # Clean up
        self.caller.permissions.add("Admin")  # Add back permission for cleanup
        other_request.delete()
        self.caller.permissions.remove("Admin")  # Remove again
        
    def test_viewing(self):
        """Test viewing requests."""
        # Set up command arguments
        self.cmd.switches = []
        self.cmd.args = "1"  # Request ID
        
        # Run the command
        self.cmd.func()
        
        # Verify output was sent to caller
        self.assertTrue(self.caller.msg.called)
        
    def test_request_listing(self):
        """Test request listing functionality."""
        # Create a second request owned by another user
        other_request = create_script(
            "typeclasses.requests.Request",
            key="Request-2"
        )
        other_request.db.id = 2
        other_request.db.submitter = self.account2
        other_request.db.title = "Other Request"
        other_request.db.text = "Another test request"
        
        # Test personal listing (should only see own request)
        self.caller.permissions.remove("Admin")
        self.cmd.switches = []
        self.cmd.args = ""
        self.cmd.func()
        # Should only see Request-1 in output
        output = str(self.caller.msg.call_args_list[-1])  # Get last call
        self.assertIn("Test Request", output)
        self.assertNotIn("Other Request", output)
        
        # Reset mock
        self.caller.msg.reset_mock()
        
        # Test staff listing all requests
        self.caller.permissions.add("Admin")
        self.cmd.switches = ["all"]
        self.cmd.func()
        # Should see both requests
        output = str(self.caller.msg.call_args_list[-1])  # Get last call
        self.assertIn("Test Request", output)
        self.assertIn("Other Request", output)
        
        # Clean up
        other_request.delete()
        
        # Reset permissions for other tests
        self.caller.permissions.add("Admin")
        
    def test_activity_tracking(self):
        """Test new activity tracking and viewing."""
        # Should start with new activity since it was just created
        self.assertTrue(self.request.has_new_activity(self.account))
        
        # View request
        self.cmd.switches = []
        self.cmd.args = "1"
        self.cmd.func()
        
        # Should no longer have new activity
        self.assertFalse(self.request.has_new_activity(self.account))
        
        # Add comment
        self.cmd.switches = ["comment"]
        self.cmd.args = "1=New comment"
        self.cmd.lhs = "1"
        self.cmd.rhs = "New comment"
        self.cmd.func()
        
        # Should have new activity again
        self.assertTrue(self.request.has_new_activity(self.account))
        
        # Test activity for other users
        other_account = self.account2
        self.assertTrue(self.request.has_new_activity(other_account))  # Never viewed
        
        # Assign to other user
        self.cmd.switches = ["assign"]
        self.cmd.args = f"1={other_account.username}"
        self.cmd.lhs = "1"
        self.cmd.rhs = other_account.username
        self.cmd.func()
        
        # Should show as new activity for assigned user
        self.assertTrue(self.request.has_new_activity(other_account))
        
    def test_categories(self):
        """Test request categories."""
        # Set up command arguments
        self.cmd.switches = ["cat"]
        self.cmd.args = "1=Bug"
        self.cmd.lhs = "1"  # Request ID
        self.cmd.rhs = "Bug"  # New category
        
        # Run the command
        self.cmd.func()
        
        # Verify category change
        request = Request.objects.get(db_key="Request-1")
        self.assertEqual(request.db.category, "Bug")
        
    def test_notifications(self):
        """Test request notifications."""
        # Mock the submitter's msg method
        self.account.msg = MagicMock()
        
        # Test notification on status change
        self.request.set_status("In Progress")
        self.account.msg.assert_called_with("[Request #1] Status changed from Open to In Progress")
        
        # Test notification on comment
        self.request.add_comment(self.account, "Test comment")  # Pass account object
        self.account.msg.assert_called_with("[Request #1] New comment by TestAccount")
        
        # Test offline notifications
        self.account.is_connected = False
        self.request.notify_all("Test notification")
        
        notifications = self.account.db.offline_request_notifications or []
        self.assertIn("[Request #1] Test notification", notifications) 