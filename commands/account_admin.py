"""
Staff commands for account management.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.accounts.accounts import AccountDB
from evennia import create_account, create_object
from evennia.utils import create
from django.conf import settings
from evennia.utils.utils import make_iter
from evennia.utils.evtable import EvTable
from evennia.utils.search import search_object
import random
import string


class CmdCreatePlayerAccount(MuxCommand):
    """
    Create a new player account and character.
    
    Usage:
        @createplayer <n> = <password>
        
    Creates a new player account and an associated character of the same name.
    This command is staff-only and is used to create pre-made characters for
    the roster system.
    
    The account and character will be created with the same name, and the
    character will be automatically linked to the account.
    """
    
    key = "@createplayer"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"
    
    def func(self):
        """
        Execute the command.
        """
        caller = self.caller
        
        if not self.args or "=" not in self.args:
            caller.msg("Usage: @createplayer <n> = <password>")
            return
            
        name, password = [part.strip() for part in self.args.split("=", 1)]
        
        # Validate the name
        if not name or len(name) < 3:
            caller.msg("Name must be at least 3 characters long.")
            return
            
        # Check if account already exists
        if AccountDB.objects.filter(username__iexact=name).exists():
            caller.msg(f"An account with the name '{name}' already exists.")
            return
            
        # Create the account
        try:
            account = create_account(
                name,
                email="",
                password=password,
                permissions=["Player"],
                typeclass=settings.BASE_ACCOUNT_TYPECLASS,
            )
            
            # Create the character
            char = create_object(
                settings.BASE_CHARACTER_TYPECLASS,
                key=name,
                location=settings.START_LOCATION,
                home=settings.START_LOCATION,
                permissions=["Player"],
            )
            
            # Link character to account
            account.db._playable_characters = [char]  # Set as the only character
            char.db.account = account
            
            # Set this as the default puppet for the account
            account.db._last_puppet = char
            
            # Put character in same state as after normal logout
            char.at_post_unpuppet()
            

            
            # Set proper locks for the character
            # This matches the format from the working character:
            # call:false(); control:perm(Developer); delete:id(X) or perm(Admin);
            # drop:holds(); edit:pid(X) or perm(Admin); examine:perm(Builder);
            # get:false(); puppet:id(Y) or pid(X) or perm(Developer) or pperm(Developer);
            # teleport:perm(Admin); teleport_here:perm(Admin); tell:perm(Admin); view:all()
            char.locks.add(
                f"call:false();"
                f"control:perm(Developer);"
                f"delete:perm(Developer);"
                f"drop:holds();"
                f"edit:perm(Admin);"
                f"examine:perm(Builder);"
                f"get:false();"
                f"puppet:id({char.id}) or pid({account.id}) or perm(Developer) or pperm(Developer);"
                f"teleport:perm(Admin);"
                f"teleport_here:perm(Admin);"
                f"tell:perm(Admin);"
                f"view:all()"
            )
            
            caller.msg(f"Created account and character '{name}'.")
            
        except Exception as e:
            caller.msg(f"Error creating account: {e}")
            # Clean up if character was created but account failed
            if 'char' in locals():
                char.delete()
            return 

class CmdSetPassword(MuxCommand):
    """
    Set a player account password.
    
    Usage:
        @setpassword <account> = <password>
        @setpassword/generate <account>    - Auto-generate and display password
        
    Sets the password for an existing account. Staff-only command for 
    account management. Use /generate to create a random secure password.
    """
    
    key = "@setpassword"
    locks = "cmd:perm(Developer)"
    help_category = "Admin"
    
    def func(self):
        """
        Execute the command.
        """
        caller = self.caller
        
        if not self.args:
            caller.msg("Usage: @setpassword <account> = <password> or @setpassword/generate <account>")
            return
            
        if "=" not in self.args and "generate" not in self.switches:
            caller.msg("Usage: @setpassword <account> = <password> or @setpassword/generate <account>")
            return
            
        # Determine account name
        if "generate" in self.switches:
            account_name = self.args.strip()
        else:
            if not self.lhs:
                caller.msg("Usage: @setpassword <account> = <password>")
                return
            account_name = self.lhs.strip()
            
        # Find the account
        try:
            account = AccountDB.objects.get(username__iexact=account_name)
        except AccountDB.DoesNotExist:
            caller.msg(f"Account '{account_name}' not found.")
            return
        except AccountDB.MultipleObjectsReturned:
            caller.msg(f"Multiple accounts found matching '{account_name}'.")
            return
            
        # Set the password
        if "generate" in self.switches:
            # Auto-generate secure password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        else:
            password = self.rhs.strip()
            if not password:
                caller.msg("Password cannot be empty.")
                return
                
        # Update the account
        account.set_password(password)
        account.save()
        
        if "generate" in self.switches:
            caller.msg(f"Password for account '{account.username}' has been set to: {password}")
            caller.msg("|yMake sure to securely communicate this password and then clear your screen.|n")
        else:
            caller.msg(f"Password for account '{account.username}' has been updated successfully.")


class CmdCheckEmails(MuxCommand):
    """
    Check application patterns for an email address and detect shared IPs.
    
    Usage:
        checkemails <email>           - Show application history and cross-IP analysis for email
    """
    
    key = "checkemails"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"
    
    def func(self):
        """
        Execute command.
        """
        if not self.args:
            self.caller.msg("Usage: checkemails <email>")
            return
            
        email = self.args.strip()
        
        # Find all applications for this email
        from evennia.scripts.models import ScriptDB
        all_apps = ScriptDB.objects.filter(
            db_typeclass_path="typeclasses.applications.Application"
        )
        
        user_apps = []
        user_ips = set()
        
        for app in all_apps:
            if app.db.email == email:
                user_apps.append(app)
                if app.db.ip_address:
                    user_ips.add(app.db.ip_address)
        
        if not user_apps:
            self.caller.msg(f"No applications found for {email}")
            return
            
        # Display email analysis
        self.caller.msg(f"|w=== Email Analysis: {email} ===|n")
        self.caller.msg(f"Total applications: {len(user_apps)}")
        
        # Show application history
        self.caller.msg(f"\n|wApplication History:|n")
        for app in sorted(user_apps, key=lambda x: x.id):
            status = app.db.status or "pending"
            char_name = app.db.char_name
            reviewer = ""
            if app.db.reviewer:
                reviewer = f" (by {app.db.reviewer.key})"
            date = ""
            if app.db.review_date:
                date = f" on {app.db.review_date.strftime('%Y-%m-%d')}"
            
            self.caller.msg(f"  #{app.id}: {char_name} - {status}{reviewer}{date}")
        
        # Show IP analysis
        if user_ips:
            self.caller.msg(f"\n|wIP Addresses Used:|n")
            for ip in user_ips:
                if ip != "Unknown":
                    self.caller.msg(f"  {ip}")
        
        # Cross-reference with other emails using same IPs
        shared_ip_users = {}
        for ip in user_ips:
            if ip == "Unknown":
                continue
                
            for app in all_apps:
                if (app.db.ip_address == ip and 
                    app.db.email != email and 
                    app.db.email):
                    if ip not in shared_ip_users:
                        shared_ip_users[ip] = set()
                    shared_ip_users[ip].add(app.db.email)
        
        # Display shared IP warnings
        if shared_ip_users:
            self.caller.msg(f"\n|y*** SHARED IP DETECTED ***|n")
            for ip, emails in shared_ip_users.items():
                self.caller.msg(f"  IP {ip} also used by:")
                for other_email in emails:
                    # Count applications for this other email
                    other_app_count = sum(1 for app in all_apps if app.db.email == other_email)
                    self.caller.msg(f"    - {other_email} ({other_app_count} applications)")
        else:
            self.caller.msg(f"\n|g** No shared IPs detected **|n") 