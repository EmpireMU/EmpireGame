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
)

######################################################################
# Text processing settings
######################################################################

# Use custom command parser for %r and %t text substitutions
COMMAND_PARSER = "server.conf.cmdparser.cmdparser"

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

#Remove debug and error output for production
DEBUG = True  # Temporarily enable to see detailed CSRF errors
IN_GAME_ERRORS = False

ALLOWED_HOSTS = ['178.62.90.58', 'localhost', 'empiremush.org']

# Security settings for website
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session timeout for website login
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

TIME_ZONE = 'UTC'

# Security settings for reverse proxy (Caddy)
# Restrict Evennia to only listen on localhost since Caddy handles external connections
WEBSERVER_INTERFACES = ['127.0.0.1']
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'

# Tell webclient to connect via Caddy's websocket proxy
WEBSOCKET_CLIENT_URL = "wss://empiremush.org/ws/"

# HTTPS Configuration for Reverse Proxy Setup
# 
# The game runs behind Caddy reverse proxy for HTTPS termination:
# - Caddy handles SSL certificates and serves HTTPS on port 443
# - Caddy forwards requests to Evennia on localhost:4001 as HTTP
# - Django needs to trust HTTPS origins from browsers even though it receives HTTP internally
#
# To use these settings: evennia start --settings=production_settings
# 
# Required for CSRF validation with HTTPS frontend + HTTP backend:
CSRF_TRUSTED_ORIGINS = ['https://empiremush.org']
#
# Only enable if you need Django to detect requests as "secure" for other features.