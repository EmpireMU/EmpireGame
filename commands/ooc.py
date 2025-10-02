"""Custom OOC communication command."""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default import account as default_account


class CmdOOC(MuxCommand):
    """Send an out-of-character message to the current room.

    Usage:
        ooc <message>

    This mirrors the feel of `say`, but marks the output as OOC so
    everyone present can tell the chatter is out-of-character.
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
        caller_output = f'(OOC) You say, "{message}"'
        room_output = f'(OOC) {caller.name} says, "{message}"'

        caller.msg(caller_output)

        location = getattr(caller, "location", None)
        if not location:
            return

        location.msg_contents(room_output, exclude=caller)


class CmdUnpuppet(default_account.CmdOOC):
    """Unpuppet command without reserving the `ooc` keyword."""

    key = "unpuppet"
    aliases = []


