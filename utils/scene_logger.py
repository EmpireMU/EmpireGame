"""Utility helpers for recording and exposing scene logs.

This module acts as the service layer between in-game commands, room scripts,
web views, and the underlying Django models living in `web.scenes`.
It keeps the Evennia world (rooms, characters, scripts) in sync with the
relational data that powers searching and web presentation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from django.db import models, transaction
from django.utils import timezone

from evennia import create_script
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.utils.search import search_script

from web.scenes.models import SceneEntry, SceneLog, SceneParticipant, SceneParticipantSegment

logger = logging.getLogger(__name__)


SCENE_SCRIPT_TYPECLASS = "typeclasses.scene_tracker.SceneTrackerScript"


@dataclass
class SceneContext:
    """Wrapper returned by :func:`get_room_scene`.

    Attributes:
        scene: The active :class:`SceneLog` instance.
        room: The room object (if still available).
    """

    scene: SceneLog
    room: Optional[ObjectDB]


def _resolve_account(owner) -> Optional[AccountDB]:
    """Best-effort conversion of any object into its owning account."""

    if isinstance(owner, AccountDB):
        return owner
    account = getattr(owner, "account", None)
    if isinstance(account, AccountDB):
        return account
    return None


def get_room_scene(room: Optional[ObjectDB]) -> Optional[SceneContext]:
    """Return the active scene associated with this room, if any."""

    if not room:
        return None
    scene_attr = room.attributes.get("active_scene_id", category="scene")
    if not scene_attr:
        return None
    try:
        scene = SceneLog.objects.get(pk=scene_attr, status=SceneLog.Status.ACTIVE)
    except SceneLog.DoesNotExist:
        room.attributes.remove("active_scene_id", category="scene")
        return None
    return SceneContext(scene=scene, room=room)


def attach_scene_script(room: ObjectDB, scene: SceneLog):
    """Ensure the scene tracker script is attached to the room."""

    # Search for existing scene tracker scripts on this room
    existing = [
        script for script in room.scripts.all()
        if script.typeclass_path == SCENE_SCRIPT_TYPECLASS and script.key == str(scene.pk)
    ]
    if existing:
        script = existing[0]
    else:
        script = create_script(SCENE_SCRIPT_TYPECLASS, key=str(scene.pk), obj=room)
    script.db.scene_id = scene.pk
    script.db.started_at = timezone.now()
    room.attributes.add("active_scene_id", scene.pk, category="scene")


def start_scene(
    room: ObjectDB,
    owner,
    *,
    chapter=None,
    visibility: str = SceneLog.Visibility.PRIVATE,
    organisations: Optional[Iterable[ObjectDB]] = None,
    title: str = "",
) -> SceneLog:
    """Create a new scene log and attach tracking to the room."""

    account = _resolve_account(owner)
    with transaction.atomic():
        scene = SceneLog.objects.create(
            room=room,
            status=SceneLog.Status.ACTIVE,
            visibility=visibility,
            chapter=chapter,
            title=title.strip(),
            started_by=account,
        )
        if organisations:
            scene.organisations.add(*organisations)
        attach_scene_script(room, scene)
        register_initial_participants(scene, room)
    logger.info("Scene %s started in room %s", scene.pk, room)
    return scene


def register_initial_participants(scene: SceneLog, room: ObjectDB):
    """Register all present puppeted characters as scene participants."""

    now = timezone.now()
    for obj in room.contents:
        account = _resolve_account(obj)
        if not account:
            continue
        participant, created = SceneParticipant.objects.get_or_create(
            scene=scene,
            character_id=obj.id,
            defaults={
                "account_id": account.id,
                "first_joined_at": now,
                "is_present": True,
            },
        )
        if created:
            SceneParticipantSegment.objects.create(participant=participant, joined_at=now)
        else:
            if not participant.is_present:
                participant.is_present = True
                participant.last_left_at = None
                participant.save(update_fields=["is_present", "last_left_at"])
                SceneParticipantSegment.objects.create(participant=participant, joined_at=now)


def record_participant_join(scene: SceneLog, character: ObjectDB, account: AccountDB):
    """Mark a character as having joined an active scene."""

    now = timezone.now()
    participant, created = SceneParticipant.objects.get_or_create(
        scene=scene,
        character_id=character.id,
        defaults={
            "account_id": account.id,
            "first_joined_at": now,
            "is_present": True,
        },
    )
    if created:
        SceneParticipantSegment.objects.create(participant=participant, joined_at=now)
    else:
        if participant.account_id != account.id:
            participant.account_id = account.id
        participant.is_present = True
        participant.last_left_at = None
        participant.save(update_fields=["account_id", "is_present", "last_left_at"])
        SceneParticipantSegment.objects.create(participant=participant, joined_at=now)


def record_participant_depart(scene: SceneLog, character: ObjectDB):
    """Mark a character as having left the scene."""

    try:
        participant = SceneParticipant.objects.get(scene=scene, character_id=character.id)
    except SceneParticipant.DoesNotExist:
        return
    if not participant.is_present:
        return
    now = timezone.now()
    participant.is_present = False
    participant.last_left_at = now
    participant.save(update_fields=["is_present", "last_left_at"])
    segment = participant.segments.filter(left_at__isnull=True).order_by("-joined_at").first()
    if segment:
        segment.left_at = now
        segment.save(update_fields=["left_at"])


def record_entry(
    scene: SceneLog,
    entry_type: str,
    text: str,
    *,
    actor: Optional[ObjectDB] = None,
    text_plain: Optional[str] = None,
):
    """Persist a single log entry within the scene."""

    if text_plain is None:
        text_plain = strip_ansi(text)
    sequence = (
        SceneEntry.objects.filter(scene=scene).order_by("-sequence").values_list("sequence", flat=True).first()
        or 0
    ) + 1
    SceneEntry.objects.create(
        scene=scene,
        sequence=sequence,
        entry_type=entry_type,
        actor=actor,
        text=text,
        text_plain=text_plain,
    )


def strip_ansi(value: str) -> str:
    """Best-effort removal of Evennia ANSI codes for indexing/search."""

    try:
        from evennia.utils.ansi import strip_ansi as evennia_strip

        return evennia_strip(value)
    except Exception:  # pragma: no cover
        return value


def _notify_scene_end(scene: SceneLog, room_name: str, auto_closed: bool):
    """Send notifications to all participants that a scene has ended."""
    
    participants = SceneParticipant.objects.filter(scene=scene).select_related("character", "account")
    
    if auto_closed:
        message = f"|yScene {scene.pk} at {room_name} has ended (auto-closed when room emptied).|n"
    else:
        message = f"|yScene {scene.pk} at {room_name} has ended.|n"
    
    for participant in participants:
        character = participant.character
        account = participant.account
        
        # Try to send to online character first
        if character and hasattr(character, "msg") and hasattr(character, "sessions") and character.sessions.all():
            character.msg(message)
        # Otherwise store on account for next login
        elif account:
            notifications = account.attributes.get("_stored_notifications", default=[])
            notifications.append(message)
            account.attributes.add("_stored_notifications", notifications)


def finalize_scene(scene: SceneLog, *, auto_closed: bool = False):
    """Close an active scene, clearing room references and timestamps."""

    if scene.status != SceneLog.Status.ACTIVE:
        return
    now = timezone.now()
    scene.status = SceneLog.Status.COMPLETED
    scene.auto_closed = auto_closed
    scene.completed_at = now
    scene.save(update_fields=["status", "auto_closed", "completed_at"])
    
    room_name = scene.room.key if scene.room else "Unknown Location"
    
    if scene.room:
        scene.room.attributes.remove("active_scene_id", category="scene")
        # Stop any scene tracker scripts attached to this room
        for script in scene.room.scripts.all():
            if script.typeclass_path == SCENE_SCRIPT_TYPECLASS and script.key == str(scene.pk):
                script.stop()
    SceneParticipant.objects.filter(scene=scene, is_present=True).update(
        is_present=False, last_left_at=now
    )
    SceneParticipantSegment.objects.filter(participant__scene=scene, left_at__isnull=True).update(left_at=now)
    
    # Notify all participants that the scene has ended
    _notify_scene_end(scene, room_name, auto_closed)


def archive_scene(scene: SceneLog):
    """Mark a scene as archived; reversible."""

    if scene.status == SceneLog.Status.ARCHIVED:
        return
    scene.status = SceneLog.Status.ARCHIVED
    scene.archived_at = timezone.now()
    scene.save(update_fields=["status", "archived_at"])


def delete_scene(scene: SceneLog):
    """Soft-delete a scene (staff-only)."""

    scene.status = SceneLog.Status.DELETED
    scene.deleted_at = timezone.now()
    scene.save(update_fields=["status", "deleted_at"])


def scene_allows_viewer(scene: SceneLog, account) -> bool:
    """Determine whether an account may read a given scene."""

    if scene.visibility == SceneLog.Visibility.EVENT:
        return True
    if account is None or not getattr(account, "is_authenticated", False):
        return False
    if getattr(account, "is_superuser", False):
        return True
    if SceneParticipant.objects.filter(scene=scene, account=account).exists():
        return True
    if scene.visibility == SceneLog.Visibility.ORGANISATION:
        organisations = scene.organisations.all()
        if not organisations:
            return False
        from utils.org_utils import get_account_organisations

        account_orgs = get_account_organisations(account)
        org_ids = {org.id for org in organisations}
        if org_ids.intersection(account_orgs):
            return True
    return False


def visible_entries_for_account(scene: SceneLog, account):
    """Derive the queryset of entries visible to a particular viewer."""

    if scene.visibility == SceneLog.Visibility.EVENT:
        return scene.entries.order_by("sequence")
    if account is None or not getattr(account, "is_authenticated", False):
        return scene.entries.none()
    if getattr(account, "is_superuser", False):
        return scene.entries.order_by("sequence")
    try:
        participant = SceneParticipant.objects.get(scene=scene, account=account)
    except SceneParticipant.DoesNotExist:
        if scene.visibility == SceneLog.Visibility.ORGANISATION:
            return scene.entries.order_by("sequence")
        return scene.entries.none()
    segments = list(participant.segments.order_by("joined_at"))
    if not segments:
        return scene.entries.none()
    filters = models.Q()
    for segment in segments:
        joined = segment.joined_at
        left = segment.left_at or scene.completed_at or timezone.now()
        filters |= models.Q(created_at__gte=joined, created_at__lte=left)
    # Also include entries where the participant is the actor (their own arrivals/departures)
    filters |= models.Q(actor=participant.character)
    return scene.entries.filter(filters).distinct().order_by("sequence") if filters else scene.entries.none()
