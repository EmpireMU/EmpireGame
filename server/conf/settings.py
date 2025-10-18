r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Empire"

# Enable custom search handler for multi-keyword fuzzy matching
SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"

# Account creation settings
GUEST_ENABLED = True  # Allow guest accounts
CREATE_ACCOUNT_ON_CONNECT = False  # Disable automatic account creation
RESTRICTED_CREATION = True  # Restrict account creation to staff only
AUTO_PUPPET_ON_LOGIN = True  # Auto-puppet the last character on login
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False  # Don't auto-create characters

# Disable website registration
NEW_ACCOUNT_REGISTRATION_ENABLED = False

# Add our custom apps
INSTALLED_APPS += (
    'web.roster',
    'web.worldinfo',
    'web.relationships',
)

# Web profile domain for generating character URLs in info command
WEB_PROFILE_DOMAIN = 'localhost:4001'  # Development setting

######################################################################
# Text processing settings
######################################################################

# Use custom command parser for %r and %t text substitutions
COMMAND_PARSER = "server.conf.cmdparser.cmdparser"

######################################################################
# Email Configuration
######################################################################

# Email backend for development (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Default from email address (development - emails go to console)
DEFAULT_FROM_EMAIL = 'Empire MUSH <noreply@localhost>'
SERVER_EMAIL = 'Empire MUSH <noreply@localhost>'

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
