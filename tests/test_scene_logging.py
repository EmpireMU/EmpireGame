import os
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from web.scenes.models import SceneEntry, SceneLog
from utils import scene_logger

pytestmark = pytest.mark.django_db


@pytest.fixture
def account():
    User = get_user_model()
    return User.objects.create_user(username="tester", email="tester@example.com", password="tester")


@pytest.fixture
def room():
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.create(db_key="Test Room", db_typeclass_path="typeclasses.rooms.Room")


def test_start_and_finalize_scene(account, room):
    scene = scene_logger.start_scene(room, owner=room, chapter=None)
    assert scene.status == SceneLog.Status.ACTIVE
    scene_logger.finalize_scene(scene)
    scene.refresh_from_db()
    assert scene.status == SceneLog.Status.COMPLETED


def test_record_entry(account, room):
    scene = scene_logger.start_scene(room, owner=room, chapter=None)
    scene_logger.record_entry(scene, SceneEntry.EntryType.EMIT, text="|wHello|n", text_plain="Hello")
    assert SceneEntry.objects.filter(scene=scene).count() == 1
