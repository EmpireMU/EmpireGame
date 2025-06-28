"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from commands.charsheet import CharSheetCmdSet
from commands.charsheet_editor import CharSheetEditorCmdSet
from commands.charsheet_admin import CharSheetAdminCmdSet
from commands.plot_points import PlotPointCmdSet
from commands.cortex_roll import CortexCmdSet
from commands.organisations import OrgCmdSet
from commands.temporary_assets import TemporaryAssetCmdSet
from commands.complications import ComplicationCmdSet
from commands.requests import CmdRequest
from commands.board import CmdBoard
from commands.room_management import CmdRoomManagement
from commands import home
from commands.page import CmdPage
from commands.mail import CmdMailCharacterOOC
from commands import where
from commands.account_admin import CmdCreatePlayerAccount
from commands.roster import CmdRoster, CmdApplication


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CharSheetCmdSet)
        self.add(CharSheetEditorCmdSet)
        self.add(CharSheetAdminCmdSet)
        self.add(PlotPointCmdSet)
        self.add(CortexCmdSet)
        self.add(OrgCmdSet)
        self.add(TemporaryAssetCmdSet)
        self.add(ComplicationCmdSet)
        self.add(CmdBoard())
        self.add(CmdRoomManagement())
        self.add(home.CmdHome())
        self.add(where.CmdWhere())
        self.add(CmdMailCharacterOOC())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when an Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        # Add request commands - this is an OOC system
        self.add(CmdRequest())
        # Add our custom page command
        self.add(CmdPage())
        # Add staff account management command
        self.add(CmdCreatePlayerAccount())
        # Add roster commands
        self.add(CmdRoster())
        self.add(CmdApplication())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        # Add roster command for guests
        self.add(CmdRoster())


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
