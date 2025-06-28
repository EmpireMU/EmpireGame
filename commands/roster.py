"""
Roster system commands.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.utils import make_iter
from evennia.utils.evtable import EvTable
from evennia.utils.search import search_object, search_script
from django.conf import settings
from typeclasses.applications import Application
from evennia import create_object, create_script
from typeclasses.characters import STATUS_AVAILABLE, STATUS_ACTIVE, STATUS_GONE, Character
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.accounts.models import AccountDB
import re

# Email validation regex
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

class CmdApplication(MuxCommand):
    """
    Manage character applications.
    
    Usage:
        application              - List all applications
        application/view <id>    - View application details
        application/approve <id> - Approve application
        application/decline <id> - Decline application
    """
    
    key = "application"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"
    
    # def _send_email(self, email_address, subject, body):
    #     """
    #     Send an email using the configured email system.
    #     """
    #     from django.core.mail import send_mail
    #     try:
    #         send_mail(
    #             subject,
    #             body,
    #             settings.DEFAULT_FROM_EMAIL,
    #             [email_address],
    #             fail_silently=False,
    #         )
    #         return True
    #     except Exception as e:
    #         self.caller.msg(f"Error sending email: {e}")
    #         return False
    
    def func(self):
        """
        Execute command.
        """
        if not self.switches:
            # List all applications
            apps = ScriptDB.objects.filter(db_typeclass_path="typeclasses.applications.Application")
            if not apps:
                self.caller.msg("No pending applications.")
                return
                
            table = EvTable("|wID|n", "|wCharacter|n", border="header")
            for app in apps:
                table.add_row(app.id, app.db.char_name)
            self.caller.msg(str(table))
            return
            
        if "view" in self.switches:
            if not self.args:
                self.caller.msg("Usage: application/view <id>")
                return
                
            apps = search_script("#" + self.args)
            if not apps:
                self.caller.msg(f"Application {self.args} not found.")
                return
            app = apps[0]
            
            self.caller.msg(f"|wApplication for {app.db.char_name}|n")
            self.caller.msg(f"Email: {app.db.email}")
            self.caller.msg(f"IP: {app.db.ip_address}")
            self.caller.msg("\nApplication Text:")
            self.caller.msg(app.db.app_text)
            return
            
        if "approve" in self.switches or "decline" in self.switches:
            if not self.args:
                self.caller.msg(f"Usage: application/{self.switches[0]} <id>")
                return
                
            apps = search_script("#" + self.args)
            if not apps:
                self.caller.msg(f"Application {self.args} not found.")
                return
            app = apps[0]
            
            # Get the character
            char = search_object(app.db.char_name, typeclass=settings.BASE_CHARACTER_TYPECLASS)
            if not char:
                self.caller.msg(f"Character {app.db.char_name} not found.")
                return
            char = char[0]
            
            if "approve" in self.switches:
                # Check if character is still available
                if char.db.status != STATUS_AVAILABLE:
                    self.caller.msg(f"Character {char.key} is no longer available.")
                    return
                    
                # Set character to active
                char.db.status = STATUS_ACTIVE
                
                # Store email before deleting application
                email = app.db.email
                    
            else:  # decline
                # Store email before deleting application
                email = app.db.email
                pass
                    
            # Delete the application
            app.delete()
            self.caller.msg(f"Application for {char.key} has been {'approved' if 'approve' in self.switches else 'declined'}.")
            self.caller.msg(f"Remember to contact the player at: {email}")

class CmdRoster(MuxCommand):
    """
    View and manage the character roster.
    
    Usage:
        roster               - Show available characters
        roster/active       - Show active characters
        roster/gone        - Show gone characters
        roster <n>       - Filter available characters by name
        roster/gender <gender> - Filter available characters by gender
        roster/gender <gender>/<n> - Filter by gender and name
        roster/apply <character>/<email>=<application text>
        
    Staff only:
        roster/setavailable <character>  - Set character as Available
        roster/setactive <character>     - Set character as Active
        roster/setgone <character>       - Set character as Gone
    """
    
    key = "roster"
    aliases = ["roster/active", "roster/gone"]
    locks = "cmd:all()"  # Base command available to all
    help_category = "General"
    
    def _get_characters(self, status):
        """
        Get all characters with a given status.
        Args:
            status (str): One of STATUS_AVAILABLE, STATUS_ACTIVE, or STATUS_GONE
        Returns:
            list: List of character objects with matching status
        """
        chars = list(Character.objects.all())
        result = []
        for char in chars:
            # If character has no status, set it to available
            if not char.db.status:
                char.db.status = STATUS_AVAILABLE
            if char.db.status == status:
                result.append(char)
        return result
        
    def _format_char_line(self, char):
        """
        Format a character for display in the roster.
        Args:
            char (Character): The character to format
        Returns:
            tuple: (name, concept, gender, age, realm)
        """
        name = char.db.full_name or char.key
        concept = char.db.concept or "No concept set"
        gender = char.db.gender or "Not set"
        age = char.db.age or "Not set"
        realm = char.db.realm or "Not set"
        return (name, concept, gender, str(age), realm)
        
    def _filter_chars(self, chars, name=None, gender=None):
        """
        Filter characters by name and/or gender.
        """
        if name:
            name = name.lower()
            chars = [c for c in chars if name in (c.db.full_name or c.key).lower()]
        if gender:
            gender = gender.lower()
            chars = [c for c in chars if gender == (c.db.gender or "").lower()]
        return chars
        
    def _notify_staff(self, message):
        """
        Send a text notification to all online staff members.
        """
        staff = [account for account in AccountDB.objects.filter(db_is_connected=True) 
                if account.check_permstring("Admin")]
        for account in staff:
            # Send to their first session
            if account.sessions.all():
                account.sessions.all()[0].msg(message)

    def _handle_apply(self):
        """
        Handle the roster/apply command.
        """
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: roster/apply <character>/<email>=<application text>")
            return
            
        char_email, app_text = self.args.split("=", 1)
        if "/" not in char_email:
            self.caller.msg("You must provide both character name and email, separated by /")
            return
            
        char_name, email = char_email.split("/", 1)
        char_name = char_name.strip()
        email = email.strip()
        
        # Validate email format
        if not EMAIL_REGEX.match(email):
            self.caller.msg("Invalid email format.")
            return
            
        # Find the character
        char = search_object(char_name, typeclass=settings.BASE_CHARACTER_TYPECLASS)
        if not char:
            self.caller.msg(f"Character '{char_name}' not found.")
            return
        char = char[0]  # Get the first match
        
        # Check character is available
        if char.db.status != STATUS_AVAILABLE:
            self.caller.msg(f"Character '{char_name}' is not available for applications.")
            return
            
        # Create the application
        try:
            app = create_script(
                "typeclasses.applications.Application",
                key=f"Application for {char_name}",
                persistent=True
            )
            app.db.char_name = char_name
            app.db.email = email
            app.db.app_text = app_text
            
            # Get client address from session
            sessions = self.caller.sessions.all()
            if sessions:
                app.db.ip_address = sessions[0].address if hasattr(sessions[0], 'address') else "Unknown"
            else:
                app.db.ip_address = "Unknown"
            
            self.caller.msg("Your application has been submitted successfully.")
            
            # Notify online staff
            self._notify_staff(f"|w[Application]|n New application received for character |w{char_name}|n. "
                             f"Use |wapplication/view {app.id}|n to review it.")
            
        except Exception as e:
            self.caller.msg(f"Error submitting application: {str(e)}")
            if 'app' in locals():
                app.delete()
            return
            
    def _handle_admin_command(self):
        """
        Handle the admin-only roster commands.
        """
        if not self.caller.check_permstring("Admin"):
            self.caller.msg("You don't have permission to use this command.")
            return
            
        if not self.args:
            self.caller.msg(f"Usage: {self.cmdstring} <character>")
            return
            
        char = search_object(self.args, typeclass=settings.BASE_CHARACTER_TYPECLASS)
        if not char:
            self.caller.msg(f"Character '{self.args}' not found.")
            return
        char = char[0]
        
        if "setavailable" in self.switches:
            char.db.status = STATUS_AVAILABLE
            status = "Available"
        elif "setactive" in self.switches:
            char.db.status = STATUS_ACTIVE
            status = "Active"
        elif "setgone" in self.switches:
            char.db.status = STATUS_GONE
            status = "Gone"
            
        self.caller.msg(f"Set {char.key}'s status to {status}.")
        
    def func(self):
        """
        Execute command.
        """
        # Handle admin commands first
        if any(switch in ["setavailable", "setactive", "setgone"] for switch in self.switches):
            self._handle_admin_command()
            return
            
        # Handle application submission
        if "apply" in self.switches:
            self._handle_apply()
            return
            
        # Handle roster display
        caller = self.caller
        
        # Determine which status to show
        if "roster/active" in self.cmdstring:
            status = STATUS_ACTIVE
            status_text = "Active"
        elif "roster/gone" in self.cmdstring:
            status = STATUS_GONE
            status_text = "Gone"
        else:
            status = STATUS_AVAILABLE
            status_text = "Available"
            
        # Get initial character list
        chars = self._get_characters(status)
        
        # Handle filtering
        if "gender" in self.switches:
            if "/" in self.args:
                gender, name = self.args.split("/", 1)
            else:
                gender, name = self.args, None
            chars = self._filter_chars(chars, name=name, gender=gender)
        elif self.args:
            chars = self._filter_chars(chars, name=self.args)
            
        # Sort characters by base name (stripping titles)
        chars.sort(key=lambda x: (x.key.lower()))
        
        if not chars:
            caller.msg(f"No {status_text.lower()} characters found.")
            return
            
        # Create table
        table = EvTable(
            "|wName|n",
            "|wConcept|n",
            "|wGender|n",
            "|wAge|n",
            "|wRealm|n",
            border="header"
        )
        
        # Add characters to table
        for char in chars:
            table.add_row(*self._format_char_line(char))
            
        # Send output
        caller.msg(f"|w{status_text} Characters:|n")
        caller.msg(str(table)) 