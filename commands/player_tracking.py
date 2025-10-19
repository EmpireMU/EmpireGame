"""
Commands and helpers for email-based player tracking.

These commands let staff analyze everything tied to a player email in one
place: application history, shared-IP detection, linked characters, and any
staff notes saved about that email. Notes are stored using lightweight
persistent scripts keyed by the normalized email address.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils.evtable import EvTable
from evennia.utils.search import search_object
from django.conf import settings
from django.utils import timezone


EMAIL_TRACKER_TYPECLASS = "typeclasses.scripts.Script"  # Generic persistent script
EMAIL_TRACKER_KEY_PREFIX = "email_notes:"  # Namespace for per-email note scripts


def _normalize_email(email):
    """Return a lowercase, trimmed version of an email for consistent keys."""
    return (email or "").strip().lower()


def _tracker_key(email):
    """Build the storage key (email_notes:<email>) used for Script lookup."""
    return f"{EMAIL_TRACKER_KEY_PREFIX}{_normalize_email(email)}"


def get_email_tracker(email):
    """Fetch the persistent script for an email, creating one if it is missing."""
    key = _tracker_key(email)
    tracker = ScriptDB.objects.filter(db_key=key, db_typeclass_path=EMAIL_TRACKER_TYPECLASS).first()
    if tracker:
        tracker.db.notes = tracker.db.notes or []
        return tracker

    tracker = create_script(EMAIL_TRACKER_TYPECLASS, key=key, persistent=True)
    tracker.db.notes = []
    return tracker


def find_email_tracker(email):
    """Fetch the persistent script for an email, returning None if absent."""
    key = _tracker_key(email)
    tracker = ScriptDB.objects.filter(db_key=key, db_typeclass_path=EMAIL_TRACKER_TYPECLASS).first()
    if tracker and tracker.db.notes is None:
        tracker.db.notes = []
    return tracker


class CmdCheckEmails(MuxCommand):
    """
    Check application patterns, characters, IPs, and notes for an email address.

    Usage:
        checkemails <email>
    """

    key = "checkemails"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: checkemails <email>")
            return

        email = self.args.strip()

        # Gather every application tied to this email so we can summarize
        all_apps = ScriptDB.objects.filter(
            db_typeclass_path="typeclasses.applications.Application"
        )

        user_apps = []
        user_ips = set()

        for app in all_apps:
            if app.db.email == email:
                user_apps.append(app)
                if app.db.ip_address:
                    user_ips.add(app.db.ip_address)

        if not user_apps:
            caller.msg(f"No applications found for {email}")
            return

        caller.msg(f"|w=== Email Analysis: {email} ===|n")
        caller.msg(f"Total applications: {len(user_apps)}")

        # Application history: status timeline is often the first thing staff want
        caller.msg("\n|wApplication History:|n")
        for app in sorted(user_apps, key=lambda x: x.id):
            status = app.db.status or "pending"
            char_name = app.db.char_name
            reviewer = f" (by {app.db.reviewer.key})" if app.db.reviewer else ""
            date = f" on {app.db.review_date.strftime('%Y-%m-%d')}" if app.db.review_date else ""
            caller.msg(f"  #{app.id}: {char_name} - {status}{reviewer}{date}")

        # IP usage summary: shows how many times each IP was seen for this email
        ip_usage = {}
        for app in user_apps:
            ip = app.db.ip_address or "Unknown"
            ip_usage[ip] = ip_usage.get(ip, 0) + 1

        if ip_usage:
            caller.msg("\n|wIP Addresses Used:|n")
            for ip, count in sorted(ip_usage.items(), key=lambda item: (-item[1], item[0])):
                label = "time" if count == 1 else "times"
                caller.msg(f"  {ip} ({count} {label})")

        # Cross-reference shared IPs to expose overlaps with other emails
        shared_ip_users = {}
        for ip in user_ips:
            if ip == "Unknown":
                continue

            for app in all_apps:
                if (app.db.ip_address == ip and
                        app.db.email != email and
                        app.db.email):
                    shared_ip_users.setdefault(ip, set()).add(app.db.email)

        if shared_ip_users:
            caller.msg("\n|y*** SHARED IP DETECTED ***|n")
            for ip, emails in shared_ip_users.items():
                caller.msg(f"  {ip} also used by:")
                for other_email in sorted(emails):
                    other_app_count = sum(1 for app in all_apps if app.db.email == other_email)
                    caller.msg(f"    - {other_email} ({other_app_count} applications)")
        else:
            caller.msg("\n|g** No shared IPs detected **|n")

        # Characters linked via approved applications (tracks roster grants)
        tracked_characters = []
        seen_char_ids = set()
        for app in user_apps:
            if app.db.status == "approved":
                chars = search_object(app.db.char_name, typeclass=settings.BASE_CHARACTER_TYPECLASS)
                for char in chars:
                    if char.id in seen_char_ids:
                        continue
                    acct = getattr(char.db, "account", None)
                    if acct:
                        tracked_characters.append((char, acct))
                        seen_char_ids.add(char.id)

        if tracked_characters:
            caller.msg("\n|wCharacters Linked To This Email:|n")
            table = EvTable("Character", "Account")
            for char, account in tracked_characters:
                account_name = getattr(account, "key", None) or getattr(account, "username", "Unknown")
                table.add_row(char.key, account_name)
            caller.msg(str(table))
        else:
            caller.msg("\n|gNo characters currently linked to this email.|n")

        # Staff notes give the commentary history that admins have recorded
        tracker = find_email_tracker(email)
        if tracker and tracker.db.notes:
            caller.msg("\n|wStaff Notes:|n")
            for entry in tracker.db.notes:
                timestamp = entry.get("timestamp", "Unknown time")
                author = entry.get("author", "Unknown")
                comment = entry.get("comment", "")
                caller.msg(f"  [{timestamp}] {author}: {comment}")
        else:
            caller.msg("\n|gNo staff notes recorded for this email.|n")


class CmdEmailNote(MuxCommand):
    """
    View or add staff notes tied to an email address.

    Usage:
        emailnote <email>              - View notes
        emailnote <email> = <comment>  - Append a new note
    """

    key = "emailnote"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: emailnote <email> or emailnote <email> = <comment>")
            return

        email = self.lhs.strip() if self.lhs else self.args.strip()
        if not email:
            caller.msg("You must supply an email address.")
            return

        if self.rhs:  # Adding a note to the email's persistent script
            note_text = self.rhs.strip()
            if not note_text:
                caller.msg("Note text cannot be empty.")
                return

            tracker = get_email_tracker(email)
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            entry = {
                "timestamp": timestamp,
                "author": caller.key,
                "comment": note_text,
            }

            notes = tracker.db.notes or []
            notes.append(entry)
            tracker.db.notes = notes

            caller.msg(f"Added note for {email}.")

        # Display notes (if none exist yet, the command exits early above)
        tracker = find_email_tracker(email)
        if not tracker or not tracker.db.notes:
            caller.msg(f"No notes recorded for {email}.")
            return

        caller.msg(f"|wNotes for {email}:|n")
        for entry in tracker.db.notes:
            timestamp = entry.get("timestamp", "Unknown time")
            author = entry.get("author", "Unknown")
            comment = entry.get("comment", "")
            caller.msg(f"  [{timestamp}] {author}: {comment}")

