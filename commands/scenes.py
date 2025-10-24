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


class CmdScene(MuxCommand):
    """
    Manage scene logging for roleplay sessions.
    
    Usage:
        @scene/startlog              - Start a private scene
        @scene/eventlog              - Start a public event scene
        @scene/orglog                - Start an organisation scene
        @scene/endlog [<scene>]      - End active or specified scene
        @scene/title [<scene>=]<title>        - Set scene title
        @scene/plot [<scene>=]<plot>[,<plot>] - Tag scene with plots
        @scene/org [<scene>=]<org>[,<org>]    - Add organisations
        @scene/visibility <scene>=<type>      - Change visibility (staff only)
        @scene/list                  - List your recent scenes
    
    Scene Types:
        private      - Only participants and staff can view (auto-closes)
        organisation - All members of tagged organisations can view
        event        - Publicly visible to everyone
    
    Examples:
        @scene/startlog
        @scene/title A Meeting in the Gardens
        @scene/plot 5
        @scene/org House Anadun
        @scene/endlog
        @scene/list
    
    Private scenes auto-close when the room empties. Organisation and event
    scenes must be manually ended. All scenes capture poses, emits, says,
    rolls, arrivals, and departures.
    
    For the full web interface with search and filters, visit /scenes/ on
    the website.
    """

    key = "@scene"
    aliases = ["scene"]
    locks = "cmd:perm(Player)"
    help_category = "Scenes"

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

    def _get_context(self) -> Optional[SceneCommandContext]:
        """Build a context with room and active scene, if any."""
        room = self._get_room()
        if not room:
            return None
        scene_ctx = scene_logger.get_room_scene(room)
        return SceneCommandContext(room=room, scene=scene_ctx.scene if scene_ctx else None)

    def _split_scene_and_payload(self) -> Tuple[Optional[str], str]:
        """
        Parse args like "42=title" or just "title".
        Returns (scene_token, payload).
        """
        if "=" in self.args:
            scene_token, _, payload = self.args.partition("=")
            return scene_token.strip() or None, payload.strip()
        return None, self.args.strip()

    def _scene_queryset_for_caller(self):
        """Return a queryset of scenes the caller can access."""
        account = self._get_account()
        if not account:
            self.caller.msg("You must be logged in to view scenes.")
            return SceneLog.objects.none()
        if self._is_staff():
            return SceneLog.objects.exclude(status=SceneLog.Status.DELETED)
        return scene_logger.scenes_for_account(account).exclude(status=SceneLog.Status.DELETED)

    def _resolve_scene(
        self, scene_token: Optional[str], *, require_active: bool = False, allow_completed: bool = False
    ) -> Optional[SceneLog]:
        """
        Resolve a scene from a token (number or None).
        If None, tries active scene in room, then most recent scene.
        """
        queryset = self._scene_queryset_for_caller()
        
        if scene_token:
            try:
                scene_id = int(scene_token)
                scene = queryset.filter(number=scene_id).first()
                if not scene:
                    self.caller.msg(f"Scene {scene_id} not found or not accessible.")
                    return None
                if require_active and scene.status != SceneLog.Status.ACTIVE:
                    self.caller.msg(f"Scene {scene_id} is not active.")
                    return None
                return scene
            except ValueError:
                self.caller.msg(f"Invalid scene number: {scene_token}")
                return None
        
        # Try active scene in current room
        ctx = self._get_context()
        if ctx and ctx.scene:
            return ctx.scene
        
        # Try most recent scene
        if allow_completed:
            scene = queryset.order_by("-created_at").first()
            if scene:
                return scene
        
        self.caller.msg("No active scene in this room. Specify a scene number.")
        return None

    def _has_participant_rights(self, scene: SceneLog) -> bool:
        """Check if caller can edit this scene (staff or participant)."""
        if self._is_staff():
            return True
        account = self._get_account()
        if not account:
            return False
        if scene.participants.filter(account=account).exists():
            return True
        self.caller.msg("Only participants or staff may do that.")
        return False

    def func(self):
        """Route to the appropriate switch handler."""
        if not self.switches:
            self.caller.msg("Usage: @scene/startlog, @scene/endlog, @scene/title, etc. See 'help @scene'")
            return

        switch = self.switches[0].lower()
        
        if switch == "startlog":
            self.do_startlog()
        elif switch == "eventlog":
            self.do_eventlog()
        elif switch == "orglog":
            self.do_orglog()
        elif switch == "endlog":
            self.do_endlog()
        elif switch == "title":
            self.do_title()
        elif switch == "plot":
            self.do_plot()
        elif switch == "org":
            self.do_org()
        elif switch == "visibility":
            self.do_visibility()
        elif switch == "list":
            self.do_list()
        else:
            self.caller.msg(f"Unknown switch: {switch}. See 'help @scene'")

    def do_startlog(self):
        """Start a private scene."""
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

    def do_eventlog(self):
        """Start a public event scene."""
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

    def do_orglog(self):
        """Start an organisation scene."""
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
            visibility=SceneLog.Visibility.ORGANISATION,
        )
        self.caller.msg(
            f"Organisation scene logging started (Scene {scene.number}). "
            "Use @scene/org to specify which organisations can view this scene."
        )

    def do_endlog(self):
        """End an active scene."""
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

    def do_title(self):
        """Set or update a scene's title."""
        scene_token, title = self._split_scene_and_payload()
        if not title:
            self.caller.msg("Usage: @scene/title [<scene>=]<title>")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        scene.title = title
        scene.save(update_fields=["title"])
        self.caller.msg(f"Scene {scene.number} title set to: {title}")

    def do_plot(self):
        """Associate plots with a scene."""
        scene_token, payload = self._split_scene_and_payload()
        if not payload:
            self.caller.msg("Usage: @scene/plot [<scene>=]<plot>[,<plot>...]")
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

    def do_org(self):
        """Add organisations to a scene."""
        scene_token, payload = self._split_scene_and_payload()
        if not payload:
            self.caller.msg("Usage: @scene/org [<scene>=]<organisation>[,<organisation>...]")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if not self._has_participant_rights(scene):
            return
        orgs = []
        for token in [token.strip() for token in payload.split(",") if token.strip()]:
            org = get_org(token)
            if org:
                orgs.append(org)
            else:
                self.caller.msg(f"Organisation '{token}' not found.")
        if not orgs:
            self.caller.msg("No valid organisations specified.")
            return
        scene.organisations.add(*orgs)
        if scene.visibility == SceneLog.Visibility.PRIVATE:
            scene.visibility = SceneLog.Visibility.ORGANISATION
            scene.save(update_fields=["visibility"])
            self.caller.msg(f"Scene {scene.number} visibility changed to organisation.")
        self.caller.msg(f"Scene {scene.number} organisations updated.")

    def do_visibility(self):
        """Change a scene's visibility (staff only)."""
        if not self._is_staff():
            self.caller.msg("Only staff can change scene visibility.")
            return
        
        scene_token, visibility = self._split_scene_and_payload()
        visibility = visibility.lower()
        if not visibility or not scene_token:
            self.caller.msg("Usage: @scene/visibility <scene>=<private|organisation|event>")
            return
        if visibility not in SceneLog.Visibility.values:
            self.caller.msg("Invalid visibility option. Choose: private, organisation, or event.")
            return
        scene = self._resolve_scene(scene_token, require_active=False, allow_completed=True)
        if not scene:
            return
        if visibility == SceneLog.Visibility.ORGANISATION and not scene.organisations.exists():
            self.caller.msg("Add organisations with @scene/org before switching to organisation visibility.")
            return
        scene.visibility = visibility
        scene.save(update_fields=["visibility"])
        self.caller.msg(f"Scene {scene.number} visibility changed to {visibility}.")

    def do_list(self):
        """List recent scenes."""
        queryset = self._scene_queryset_for_caller()
        if queryset is SceneLog.objects.none():
            return
        
        scenes = queryset.order_by("-created_at")[:20]
        if not scenes:
            self.caller.msg("No scenes found.")
            return
        
        lines = ["|wRecent Scenes|n", "=" * 78]
        for scene in scenes:
            status = scene.get_status_display()
            visibility = scene.get_visibility_display()
            title = scene.title or "(untitled)"
            chapter_id = scene.chapter.db.story_id if scene.chapter else "?"
            lines.append(
                f"|c{scene.number:4d}|n | {title[:40]:40s} | {status:9s} | {visibility:12s} | Ch.{chapter_id}"
            )
        lines.append("=" * 78)
        lines.append("Use @scene/title, @scene/plot, @scene/org to edit your scenes.")
        lines.append("Visit /scenes/ on the website for full search and filters.")
        self.caller.msg("\n".join(lines))
