"""
Custom mail commands for the game.
"""

from evennia.contrib.game_systems.mail import CmdMailCharacter

class CmdMailCharacterOOC(CmdMailCharacter):
    """
    Send mail to other characters in the game.

    Usage:
        mail                            - List all messages
        mail <character> = <title>/<message>    - Send a new message
        mail/read <number>             - Read message <number>
        mail/delete <number>           - Delete message <number>
        mail/forward <number> = <target> - Forward message <number> to <target>
        mail/reply <number> = <title>/<message> - Reply to message <number>
        mail/ooc <character> = <title>/<message> - Send an OOC message (marked in yellow)

    The mail system allows you to send messages to other characters,
    even when they are offline. Each message includes a sender, 
    recipient, subject and message body.

    Adding /ooc to your mail will mark it as out-of-character 
    communication.
    """

    key = "mail"

    def parse(self):
        """
        Initialize the command
        """
        # Call parent parse first to initialize switches, args, etc.
        super().parse()

    def func(self):
        """
        Implement the OOC switch
        """
        if "ooc" in self.switches:
            # Remove ooc from switches so parent class doesn't see it
            self.switches.remove("ooc")
            # If sending a message, modify the header
            if self.args and not self.switches and self.rhs and "/" in self.rhs:
                header, message = self.rhs.split("/", 1)
                self.rhs = f"|y(OOC)|n {header}/{message}"

        # Let parent class handle everything else and return its result
        return super().func()