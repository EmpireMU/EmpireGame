"""
Utility helpers for managing worn items on characters.
"""

from typing import List, Optional

from evennia.objects.models import ObjectDB


def _normalize_entry(entry) -> Optional[int]:
    """Convert a worn item entry into an integer object id."""
    if hasattr(entry, "id"):
        return entry.id
    if isinstance(entry, int):
        return entry
    if isinstance(entry, str):
        token = entry.lstrip("#")
        if token.isdigit():
            return int(token)
    return None


def _get_worn_ids(character) -> List[int]:
    """Fetch and normalise the stored worn item ids for a character."""
    stored = character.db.worn_items or []
    ids: List[int] = []
    changed = False
    for entry in stored:
        obj_id = _normalize_entry(entry)
        if obj_id is None:
            changed = True
            continue
        ids.append(obj_id)
        if not isinstance(entry, int):
            changed = True
    if changed:
        character.db.worn_items = ids
    return ids


def get_worn_items(character) -> List[object]:
    """Return worn items as live objects, cleaning stale references."""
    ids = _get_worn_ids(character)
    if not ids:
        return []

    contents_map = {obj.id: obj for obj in character.contents}
    missing = [obj_id for obj_id in ids if obj_id not in contents_map]
    db_map = {}
    if missing:
        db_objects = ObjectDB.objects.filter(id__in=set(missing))
        db_map = {obj.id: obj for obj in db_objects}

    resolved = []
    for obj_id in ids:
        obj = contents_map.get(obj_id) or db_map.get(obj_id)
        if obj:
            resolved.append(obj)

    cleaned_ids = [obj.id for obj in resolved]
    if cleaned_ids != ids:
        character.db.worn_items = cleaned_ids

    return resolved


def add_worn_item(character, item) -> bool:
    """Track an item as worn on the character."""
    obj_id = _normalize_entry(item)
    if obj_id is None:
        return False
    ids = _get_worn_ids(character)
    if obj_id in ids:
        return False
    ids.append(obj_id)
    character.db.worn_items = ids
    return True


def remove_worn_item(character, item) -> bool:
    """Stop tracking an item as worn on the character."""
    obj_id = _normalize_entry(item)
    if obj_id is None:
        return False
    ids = _get_worn_ids(character)
    updated = [existing for existing in ids if existing != obj_id]
    if len(updated) == len(ids):
        return False
    character.db.worn_items = updated
    return True

