from django.conf import settings
from django.db import models
from django.utils import timezone


class SceneLog(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"
        DELETED = "deleted", "Deleted"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        ORGANISATION = "organisation", "Organisation"
        EVENT = "event", "Event"

    room = models.ForeignKey(
        "objects.ObjectDB",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_logs",
        limit_choices_to={"db_typeclass_path__iexact": "typeclasses.rooms.Room"},
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE, db_index=True)
    chapter = models.ForeignKey(
        "scripts.ScriptDB",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_logs",
        limit_choices_to={"db_typeclass_path__iexact": "typeclasses.story.StoryElement"},
    )
    title = models.CharField(max_length=200, blank=True)
    organisations = models.ManyToManyField(
        "objects.ObjectDB",
        blank=True,
        related_name="organisation_scene_logs",
        limit_choices_to={"db_typeclass_path__iexact": "typeclasses.organisations.Organisation"},
    )
    plots = models.ManyToManyField(
        "scripts.ScriptDB",
        blank=True,
        related_name="plot_scene_logs",
        limit_choices_to={"db_typeclass_path__iexact": "typeclasses.story.StoryElement"},
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    auto_closed = models.BooleanField(default=False)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_logs_started",
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Scene {self.number}"

    @property
    def number(self) -> int:
        return self.pk or 0


class SceneParticipant(models.Model):
    scene = models.ForeignKey(SceneLog, on_delete=models.CASCADE, related_name="participants")
    character = models.ForeignKey(
        "objects.ObjectDB", on_delete=models.CASCADE, related_name="scene_participations"
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scene_participations"
    )
    first_joined_at = models.DateTimeField(default=timezone.now)
    last_left_at = models.DateTimeField(null=True, blank=True)
    is_present = models.BooleanField(default=True)

    class Meta:
        unique_together = ("scene", "character")
        indexes = [
            models.Index(fields=["scene", "account"]),
            models.Index(fields=["scene", "character"]),
        ]

    def __str__(self):
        return f"SceneParticipant(scene={self.scene_id}, character={self.character_id})"


class SceneParticipantSegment(models.Model):
    participant = models.ForeignKey(SceneParticipant, on_delete=models.CASCADE, related_name="segments")
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["joined_at"]


class SceneEntry(models.Model):
    class EntryType(models.TextChoices):
        EMIT = "emit", "Emit"
        SAY = "say", "Say"
        POSE = "pose", "Pose"
        ROLL = "roll", "Roll"
        ARRIVAL = "arrival", "Arrival"
        DEPART = "depart", "Depart"
        SYSTEM = "system", "System"

    scene = models.ForeignKey(SceneLog, on_delete=models.CASCADE, related_name="entries")
    sequence = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    entry_type = models.CharField(max_length=16, choices=EntryType.choices, db_index=True)
    actor = models.ForeignKey(
        "objects.ObjectDB", on_delete=models.SET_NULL, null=True, blank=True, related_name="scene_entries"
    )
    text = models.TextField()
    text_plain = models.TextField(blank=True)

    class Meta:
        ordering = ["scene", "sequence"]
        unique_together = ("scene", "sequence")
        indexes = [
            models.Index(fields=["scene", "sequence"]),
            models.Index(fields=["scene", "entry_type"]),
        ]

    def save(self, *args, **kwargs):
        if self.sequence is None:
            last_sequence = (
                SceneEntry.objects.filter(scene=self.scene).order_by("-sequence").values_list("sequence", flat=True).first()
            )
            self.sequence = (last_sequence or 0) + 1
        super().save(*args, **kwargs)
