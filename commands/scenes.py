"""Scene logging command suite.

These commands give players control over starting, finishing, and annotating
scene logs from inside the game. They work hand-in-hand with the
`utils.scene_logger` service and the room-attached `SceneTrackerScript`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from evennia.commands.default.muxcommand import MuxCommand

from utils import scene_logger
from utils.org_utils import get_org
from utils.story_manager import StoryManager
from web.scenes.models import SceneLog

STAFF_LOCKSTRING = "perm(Admin) or perm(Builder)"


@dataclass
class SceneCommandContext:
    """Small helper bundle describing the caller's location and active scene."""

    room: Any
    scene: Optional[SceneLog]


class SceneCommandMixin:
    """Shared helpers for all scene commands."""

    def _is_staff(self) -> bool:
        """Return True if the caller satisfies the staff lock."""

        return self.caller.locks.check_lockstring(self.caller, STAFF_LOCKSTRING)

    def _get_account(self):
        """Return the caller's account, if any."""

        return getattr(self.caller, "account", None)

    def _get_room(self):
        """Ensure the caller is located in a room and return it."""

        room = getattr(self.caller, "location", None)
        if not room:
            self.caller.msg("You must be in a room to do that.")
            return None
        return room

    def _active_scene(self, room) -> Optional[SceneLog]:
        ctx = scene_logger.get_room_scene(room)
        return ctx.scene if ctx else None

    def _get_context(self) -> Optional[SceneCommandContext]:
        room = self._get_room()
        if not room:
            return None
        return SceneCommandContext(room=room, scene=self._active_scene(room))

    def _split_scene_and_payload(self) -> Tuple[Optional[str], str]:
        """Support `<scene>=<value>` as well as bare `<value>` syntax."""

        if self.rhs is not None:
            return (self.lhs or "").strip() or None, (self.rhs or "").strip()
        return None, (self.args or "").strip()

    def _scene_queryset_for_caller(self):
        """Limit scene access to staff or participant-owned scenes."""

        if self._is_staff():
            return SceneLog.objects.all()
        account = self._get_account()
        if not account:
            self.caller.msg("You must be logged in through an account to manage scenes.")
            return SceneLog.objects.none()
        return SceneLog.objects.filter(participants__account=account)

    def _resolve_scene(
        self,
        scene_token: Optional[str],
        *,
        require_active: bool,
        allow_completed: bool,
        allow_room_fallback: bool = True,
    ) -> Optional[SceneLog]:
        """Resolve which scene the caller is trying to act on."""

        queryset = self._scene_queryset_for_caller()
        if queryset is SceneLog.objects.none():
            return None

        room = self._get_room()
        if not room:
            return None

        active_scene = self._active_scene(room)

        if scene_token:
            try:
                scene_id = int(scene_token.lstrip("#"))
            except ValueError:
                self.caller.msg("Scene identifier must be a number.")
                return None
            scene = queryset.filter(pk=scene_id).first()
            if not scene:
                self.caller.msg(f"You do not have access to scene {scene_id}.")
                return None
            return scene

        if require_active:
            if active_scene and queryset.filter(pk=active_scene.pk).exists():
                return active_scene
            self.caller.msg("No active scene log in this room.")
            return None

        if allow_room_fallback and active_scene and queryset.filter(pk=active_scene.pk).exists():
            return active_scene

        if allow_completed:
            scene = queryset.order_by("-created_at").first()
            if scene:
                return scene
        self.caller.msg("No scene found to operate on.")
        return None

    def _has_participant_rights(self, scene: SceneLog) -> bool:
        """Enforce that the caller is staff or part of the scene."""

        if self._is_staff():
            return True
        participant = scene.participants.filter(character_id=getattr(self.caller, "id", None)).exists()
        if participant:
            return True
        self.caller.msg("Only participants or staff may do that.")
        return False


class CmdSceneStartLog(SceneCommandMixin, MuxCommand):
    """
    Begin logging a private scene in the current room.
    
    Usage:
        @scene/startlog
        scene/startlog
    
    Starts recording all poses, emits, says, rolls, arrivals, and departures
    in the current room. The scene will be private (visible only to participants
    and staff) and will automatically be tagged with the current chapter.
    
    The scene will auto-close when the room empties, or you can manually end it
    with @scene/endlog.
    
    For public events, use @scene/eventlog instead.
    """

    key = "@scene/startlog"
    aliases = ["scene/startlog", "scenelog/start"]
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        ctx = self._get_context()
        if not ctx:
            return
        if ctx.scene:
            self.caller.msg("This room already has an active scene log.")
            return
        chapter = StoryManager.get_current_chapter()
        scene = scene_logger.start_scene(
            ctx.room,
            owner=self.caller,
            chapter=chapter,
            visibility=SceneLog.Visibility.PRIVATE,
        )
        self.caller.msg(f"Scene logging started (Scene {scene.number}).")


class CmdSceneEventLog(SceneCommandMixin, MuxCommand):
    """
    Begin logging a public event scene in the current room.
    
    Usage:
        @scene/eventlog
        scene/eventlog
    
    Starts recording an event scene that will be publicly visible to everyone.
    Use this for public events which all characters might reasonably be
    expected to know about.

    Event scenes will not auto-close when the room empties - you must manually
    end them with @scene/endlog.
    
    For private scenes, use @scene/startlog instead.
    """

    key = "@scene/eventlog"
    aliases = ["scene/eventlog", "scenelog/event"]
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        ctx = self._get_context()
        if not ctx:
            return
        if ctx.scene:
            self.caller.msg("This room already has an active scene log.")
            return
        chapter = StoryManager.get_current_chapter()
        scene = scene_logger.start_scene(
            ctx.room,
            owner=self.caller,
            chapter=chapter,
            visibility=SceneLog.Visibility.EVENT,
        )
        self.caller.msg(f"Event scene logging started (Scene {scene.number}). This scene is publicly visible.")


class CmdSceneEndLog(SceneCommandMixin, MuxCommand):
    """
    End an active scene log.
    
    Usage:
        @scene/endlog
        @scene/endlog <scene number>  (staff only)
    
    Stops logging the active scene in your current room. All participants will
    be notified that the scene has ended, and the scene will be marked as
    completed and viewable on the website.
    
    """

    key = "@scene/endlog"
    aliases = ["scene/endlog", "scenelog/end"]
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        scene_token, _ = self._split_scene_and_payload()
        
        # If a specific scene number was provided, only staff can end it remotely
        if scene_token and not self._is_staff():
            self.caller.msg("Only staff can end scenes remotely by number.")
            return
        
        scene = self._resolve_scene(scene_token, require_active=True, allow_completed=False)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        scene_logger.finalize_scene(scene, auto_closed=False)
        self.caller.msg(f"Scene {scene.number} closed.")


class CmdSceneTitle(SceneCommandMixin, MuxCommand):
    """Set or update a scene's title."""

    key = "@scene/title"
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        scene_token, title = self._split_scene_and_payload()
        if not title:
            self.caller.msg("Usage: @scene/title [scene]=<title>")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        scene.title = title
        scene.save(update_fields=["title"])
        self.caller.msg(f"Scene {scene.number} title set to '{title}'.")


class CmdScenePlot(SceneCommandMixin, MuxCommand):
    """
    Tag a scene with one or more plots.
    
    Usage:
        @scene/plot <plot>
        @scene/plot <plot1>,<plot2>,<plot3>
        @scene/plot <scene number>=<plot>
    
    Associates your scene with story plots. You can specify plots by name or ID.
    Multiple plots can be separated by commas.
    """

    key = "@scene/plot"
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        scene_token, payload = self._split_scene_and_payload()
        if not payload:
            self.caller.msg("Usage: @scene/plot [scene]=<plot>[,<plot>...]")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        plots = []
        for token in [token.strip() for token in payload.split(",") if token.strip()]:
            plot = StoryManager.find_plot(token) or StoryManager.find_plot_by_name(token)
            if plot:
                plots.append(plot)
            else:
                self.caller.msg(f"Plot '{token}' not found.")
        if not plots:
            self.caller.msg("No valid plots specified.")
            return
        scene.plots.set(plots)
        self.caller.msg(f"Scene {scene.number} plots updated.")


class CmdSceneVisibility(SceneCommandMixin, MuxCommand):
    """
    Change a scene's visibility level.
    
    Usage:
        @scene/visibility <private|organisation|event>
        @scene/visibility <scene number>=<private|organisation|event>
    
    Visibility levels:
        private      - Only participants and staff can view (default)
        organisation - All members of tagged organisations can view
        event        - Publicly visible to everyone (staff only)

    
    Note: Only staff can retroactively mark scenes as events. Players can start
    event scenes using @scene/eventlog.
    """

    key = "@scene/visibility"
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        scene_token, visibility = self._split_scene_and_payload()
        visibility = visibility.lower()
        if not visibility:
            self.caller.msg("Usage: @scene/visibility [scene]=<private|organisation|event>")
            return
        if visibility == SceneLog.Visibility.EVENT and not self._is_staff():
            self.caller.msg("Only staff may retroactively mark scenes as events.")
            return
        if visibility not in SceneLog.Visibility.values:
            self.caller.msg("Invalid visibility option.")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if visibility == SceneLog.Visibility.ORGANISATION and not scene.organisations.exists():
            self.caller.msg("Add organisations with @scene/org before switching to organisation visibility.")
            return
        if not self._has_participant_rights(scene):
            return
        scene.visibility = visibility
        scene.save(update_fields=["visibility"])
        self.caller.msg(f"Scene {scene.number} visibility set to {scene.get_visibility_display()}.")


class CmdSceneOrg(SceneCommandMixin, MuxCommand):
    """
    Grant organisation-wide access to a scene.
    
    Usage:
        @scene/org <organisation>
        @scene/org <org1>,<org2>,<org3>
        @scene/org <scene number>=<organisation>
    
    Examples:
        @scene/org House Anadun
        @scene/org The Guild,House Otrese
        @scene/org 42=House Anadun
    
    Allows all members of the specified organisation(s) to view the scene.
    This is good for meetings and similar which organisation members but
    not all characters on the game might know about.

    If the scene is currently private, it will automatically be changed to
    organisation visibility.
    """

    key = "@scene/org"
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        scene_token, payload = self._split_scene_and_payload()
        if not payload:
            self.caller.msg("Usage: @scene/org [scene]=<organisation>[,<organisation>...]")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        organisations = []
        for token in [token.strip() for token in payload.split(",") if token.strip()]:
            org = get_org(token, caller=self.caller)
            if org:
                organisations.append(org)
        if not organisations:
            self.caller.msg("No valid organisations specified.")
            return
        scene.organisations.set(organisations)
        if scene.visibility == SceneLog.Visibility.PRIVATE:
            scene.visibility = SceneLog.Visibility.ORGANISATION
            scene.save(update_fields=["visibility"])
            self.caller.msg(
                "Organisations added. Scene visibility set to Organisation."
            )
        else:
            scene.save(update_fields=["title"])  # touch instance without changing fields
            self.caller.msg("Organisations added to scene.")


class CmdSceneList(SceneCommandMixin, MuxCommand):
    """
    List your recent scenes.
    
    Usage:
        @scene/list
        scene/list
    
    Shows the 20 most recent scenes you participated in, including their titles,
    status (Active/Completed), visibility level, and chapter.
    
    For a full browsable list with search and filters, visit the scenes page
    on the website.
    """

    key = "@scene/list"
    aliases = ["scene/list", "@scenelist"]
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

    def func(self):
        queryset = self._scene_queryset_for_caller()
        if queryset is SceneLog.objects.none():
            return
        scenes = queryset.filter(status__in=[SceneLog.Status.ACTIVE, SceneLog.Status.COMPLETED]).order_by("-created_at")[:20]
        if not scenes:
            self.caller.msg("You are not part of any recorded scenes yet.")
            return
        lines = ["|wYour Scenes|n"]
        for scene in scenes:
            title = scene.title or "Untitled"
            chapter = f"Chapter {scene.chapter.db.story_id}" if scene.chapter else "No chapter"
            status = scene.get_status_display()
            lines.append(
                f"Scene {scene.number}: {title} ({status}, {scene.get_visibility_display()}, {chapter})"
            )
        self.caller.msg("\n".join(lines))
