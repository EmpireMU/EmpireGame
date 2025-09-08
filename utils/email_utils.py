"""
Email utilities for Empire MUSH.
Handles automated emails for character applications.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import logging

# SendGrid Web API
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    # Fallback to Django's email backend
    from django.core.mail import send_mail
    SENDGRID_AVAILABLE = False

logger = logging.getLogger(__name__)


def create_password_reset_link(account):
    """
    Create a password reset link for the given account.
    
    Args:
        account: The account to create a reset link for
        
    Returns:
        str: The password reset URL
    """
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    # Use the web profile domain from settings
    domain = getattr(settings, 'WEB_PROFILE_DOMAIN', 'localhost:4001')
    return f"https://{domain}/accounts/password/reset/confirm/{uid}/{token}/"


def send_application_approved_email(email, character_name, account, comment=""):
    """
    Send an email when a character application is approved.
    
    Args:
        email (str): The applicant's email address
        character_name (str): Name of the approved character
        account: The existing account for this character
        comment (str, optional): Personal message from staff
    """
    subject = f"Empire MUSH - Application Approved for {character_name}"
    
    reset_link = create_password_reset_link(account)
    
    message = f"""Congratulations! Your application for {character_name} has been approved.

Your username is: {account.username}

To set your password and log in, please visit this link:
{reset_link}

This link will expire in 3 days. If you need a new link, please contact staff."""

    if comment:
        message += f"\n\nPersonal message from staff:\n{comment}"

    message += f"""

You can connect to Empire MUSH at: empiremush.org port 4000
Or use the web client at: https://empiremush.org/webclient/

"""
    
    return _send_email(email, subject, message, f"approval email for character {character_name}")


def send_application_declined_email(email, character_name, comment=""):
    """
    Send an email when a character application is declined.
    
    Args:
        email (str): The applicant's email address
        character_name (str): Name of the declined character
        comment (str, optional): Personal message from staff
    """
    subject = f"Empire MUSH - Application Status for {character_name}"
    
    message = f"""Thank you for your interest in playing {character_name} on Empire MUSH.

Unfortunately, your application has been declined."""

    if comment:
        message += f"\n\n{comment}"

    message += f"""

"""
    
    return _send_email(email, subject, message, f"decline email for character {character_name}")


def _send_email(to_email, subject, message, description):
    """
    Send email using SendGrid Web API or fallback to Django's email backend.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        message (str): Email body
        description (str): Description for logging
    
    Returns:
        bool: True if successful, False otherwise
    """
    if SENDGRID_AVAILABLE and hasattr(settings, 'SENDGRID_API_KEY'):
        # Use SendGrid Web API
        try:
            mail = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=to_email,
                subject=subject,
                plain_text_content=message
            )
            
            sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
            response = sg.send(mail)
            
            if response.status_code == 202:
                logger.info(f"SendGrid API: {description} sent to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} for {description}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send {description} via SendGrid API: {e}")
            return False
    else:
        # Fallback to Django's email backend
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
            logger.info(f"Django email: {description} sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send {description} via Django email: {e}")
            return False
