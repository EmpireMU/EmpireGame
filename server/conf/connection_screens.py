# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
|b==============================================================|n
 Welcome to |540{}|n! For more details about the game, visit the
 website at https://www.empiremush.org

 You can connect to a guest account to apply for a character or
 chat on channels by typing:
      |wconnect guest|n

 If you have an existing account, connect to it by typing:
      |wconnect <username> <password>|n

Information about the game and the setting can be found at:
      |whttps://empiremush.org/world/|n

 A list of characters can be found at:
      |whttps://empiremush.org/characters/|n

The game rules can be found at:
      |whttps://empiremush.org/world/game-rules/|n

 Enter |whelp|n for information on game commands.
 |wlook|n will redisplay this screen.
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
