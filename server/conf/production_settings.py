"""
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
TELNET_HOSTNAME = "empiremush.org"

# Hook in custom search handling
SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"

# Account creation settings
GUEST_ENABLED = True  # Allow guest accounts
BASE_GUEST_TYPECLASS = "typeclasses.accounts.Guest"  # Fix stale puppet references
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
    'web.scenes',
)

MULTISESSION_MODE = 1  #Many sessions per account, with input and output being the same across all sessions.

######################################################################
# Text processing settings
######################################################################

# Use custom command parser for %r and %t text substitutions
COMMAND_PARSER = "server.conf.cmdparser.cmdparser"

######################################################################
# Email Configuration
######################################################################

# Mailgun Web API configuration for production (preferred)
# Fallback email backend for development or if Mailgun unavailable
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Mailgun settings (will be overridden in secret_settings.py)
MAILGUN_API_KEY = 'your-mailgun-api-key'
MAILGUN_DOMAIN = 'your-domain.mailgun.org'

# Default from email address (will be overridden in secret_settings.py)
DEFAULT_FROM_EMAIL = 'Empire MUSH <noreply@your-domain.mailgun.org>'
SERVER_EMAIL = 'Empire MUSH <noreply@your-domain.mailgun.org>'

#Remove debug and error output for production
DEBUG = True
IN_GAME_ERRORS = False

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

ALLOWED_HOSTS = ['178.62.90.58', 'localhost', 'empiremush.org', 'www.empiremush.org']

# Security settings for website
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session timeout for website login
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

IDLE_TIMEOUT = -1  # Disable idle timeout for MUD connections

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
CSRF_TRUSTED_ORIGINS = ['https://empiremush.org', 'https://www.empiremush.org']

# Web profile domain for generating character URLs in info command
WEB_PROFILE_DOMAIN = 'empiremush.org'  # Production setting

# Make Django aware it's behind a TLS-terminating proxy (Caddy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Send cookies only over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security (Caddy also redirects HTTP->HTTPS)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # enable only if you will preload the domain
SECURE_SSL_REDIRECT = False  # handled by Caddy to avoid redirect loops

# Tighten browser security headers
SECURE_REFERRER_POLICY = 'same-origin'

######################################################################
# Game Index Connection Settings
######################################################################
try:
    from server.conf.connection_settings import *
except ImportError:
    print("connection_settings.py file not found or failed to import.")
