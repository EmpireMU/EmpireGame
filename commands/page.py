"""
Custom page command implementation.

This module contains a modified version of the default page command
that removes the "Account" prefix and keeps all recipients on one line.
"""

from evennia.commands.default.comms import CmdPage as DefaultCmdPage
from evennia.utils.search import search_account


class CmdPage(DefaultCmdPage):
    """
    send a private message to another account

    Usage:
      page[/switches] [<account>,<account>,... = <message>]
      page[/switches] [<account> <message>]

    Switch:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no
    argument is given, you will get a list of your latest messages.
    """
    def format_message(self, message, recipients):
        """
        Format the message for sending.
        """
        # Get the name to display for sender
        sender_name = f"|c{self.caller.key}|n"
        
        # For a single recipient
        if len(recipients) == 1:
            # If we're sending to the message to the recipient
            if recipients[0] != self.caller:
                return f"{sender_name} pages you: {message}"
            # If we're sending the message to the sender
            return f"You page |c{recipients[0].key}|n: {message}"
        
        # For multiple recipients
        recipient_names = []
        for obj in recipients:
            if obj == self.caller:
                continue  # Skip the sender
            # If we're formatting for this specific recipient
            if obj == self.msg_receiver:
                recipient_names.append("you")
            else:
                recipient_names.append(f"|c{obj.key}|n")
        
        recipient_list = ", ".join(recipient_names)
        
        # If we're sending to the sender
        if self.msg_receiver == self.caller:
            return f"You page {recipient_list}: {message}"
        # If we're sending to a recipient
        return f"{sender_name} pages {recipient_list}: {message}"

    def func(self):
        """
        Override func to use our custom message formatting.
        """
        # First check if we're displaying last messages
        if "last" in self.switches:
            super().func()
            return
        if "list" in self.switches or not self.args:
            super().func()
            return
        
        # Parse the message
        if self.rhs:
            # We have a = separator, so we're using page person = message format
            recipients = self.lhslist
            message = self.rhs.strip()
        else:
            # We're using the page person message format
            args = self.args.strip().split(" ", 1)
            if len(args) < 2:
                self.caller.msg("Usage: page <account> <message>")
                return
            recipients = [args[0]]
            message = args[1]
        
        # Get the recipient account objects
        recipient_objs = []
        for recipient in recipients:
            # Search specifically for accounts, not general objects
            account = search_account(recipient)
            if not account:
                self.caller.msg(f"No account found with the name '{recipient}'.")
                continue
            # search_account returns a list or QuerySet - always convert to list
            if not isinstance(account, list):
                account = list(account)
            
            if len(account) == 0:
                self.caller.msg(f"No account found with the name '{recipient}'.")
                continue
            if len(account) > 1:
                self.caller.msg(f"Multiple accounts match '{recipient}'. Please be more specific.")
                continue
            recipient_objs.append(account[0])
        
        if not recipient_objs:
            return
        
        # Check which recipients are online and send the message
        online_recipients = []
        for recipient in recipient_objs:
            # Check if the recipient has any active sessions (is online)
            if hasattr(recipient, 'sessions') and recipient.sessions.all():
                online_recipients.append(recipient)
            else:
                # Notify sender that recipient is offline
                self.caller.msg(f"|c{recipient.key}|n is not online. Message not sent.")
        
        # If no recipients were online, return early
        if not online_recipients:
            return
        
        # Send the message to online recipients only
        for recipient in online_recipients:
            self.msg_receiver = recipient
            formatted_msg = self.format_message(message, online_recipients)
            recipient.msg(formatted_msg, from_obj=self.caller)
        
        # Send a copy to the sender (only if they weren't already a recipient)
        if self.caller not in online_recipients:
            self.msg_receiver = self.caller
            sender_msg = self.format_message(message, online_recipients)
            self.caller.msg(sender_msg) 