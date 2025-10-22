"""Custom OOC communication command."""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default import account as default_account


class CmdOOC(MuxCommand):
    """Send an out-of-character message to the current room.

    Usage:
        ooc <message>
        ooc :<action>
        ooc ;<action>

    This mirrors the feel of `say`, but marks the output as OOC so
    everyone present can tell the chatter is out-of-character.
    
    Starting your message with : or ; will format it as an emote:
        ooc ;waves hello
        -> (OOC) YourName waves hello
    """

    key = "ooc"
    locks = "cmd:all()"
    help_category = "Communication"

    def func(self):
        """Run the command."""

        caller = self.caller

        if not self.args:
            caller.msg("Usage: ooc <message>")
            return

        message = self.args.strip()
        
        # Check if message starts with ; or : for emote-style OOC
        if message.startswith((";", ":")):
            # Remove the prefix and format as an emote
            emote_text = message[1:].strip()
            caller_output = f'|y(OOC)|n {caller.name} {emote_text}'
            room_output = f'|y(OOC)|n {caller.name} {emote_text}'
        else:
            # Regular say-style OOC
            caller_output = f'|y(OOC)|n You say, "{message}"'
            room_output = f'|y(OOC)|n {caller.name} says, "{message}"'

        caller.msg(caller_output)

        location = getattr(caller, "location", None)
        if not location:
            return

        location.msg_contents(room_output, exclude=caller)


class CmdUnpuppet(default_account.CmdOOC):
    """Unpuppet command without reserving the `ooc` keyword."""

    key = "unpuppet"
    aliases = []


