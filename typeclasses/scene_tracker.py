"""Scene tracking script for logging in-game scenes."""

from evennia.scripts.scripts import DefaultScript

from utils import scene_logger
from web.scenes.models import SceneEntry


class SceneTrackerScript(DefaultScript):
    """Script attached to a room while a scene log is active."""

    def at_script_creation(self):
        super().at_script_creation()
        self.interval = 0
        self.persistent = True

    @property
    def scene(self):
        scene_id = self.db.scene_id
        if not scene_id:
            return None
        from web.scenes.models import SceneLog

        try:
            return SceneLog.objects.get(pk=scene_id)
        except SceneLog.DoesNotExist:
            return None

    def at_object_receive(self, obj, **kwargs):
        scene = self.scene
        if not scene:
            return
        account = scene_logger._resolve_account(obj)
        if account:
            scene_logger.record_participant_join(scene, obj, account)
            scene_logger.record_entry(
                scene,
                SceneEntry.EntryType.ARRIVAL,
                text=f"|w{obj.key}|n arrives.",
                actor=obj,
            )

    def at_object_leave(self, obj, **kwargs):
        scene = self.scene
        if not scene:
            return
        account = scene_logger._resolve_account(obj)
        if account:
            scene_logger.record_participant_depart(scene, obj)
            scene_logger.record_entry(
                scene,
                SceneEntry.EntryType.DEPART,
                text=f"|w{obj.key}|n departs.",
                actor=obj,
            )
        remaining_players = [
            content for content in self.obj.contents if getattr(content, "account", None)
        ]
        if not remaining_players:
            scene_logger.finalize_scene(scene, auto_closed=True)

