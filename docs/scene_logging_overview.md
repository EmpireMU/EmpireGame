# Scene Logging System Overview

This document explains the end-to-end scene logging system used by Empire,
including the in-game commands, supporting services, database models, and web
interfaces. It is intended for staff and developers who need to understand or
extend the feature.

## Goals

- Capture roleplay scenes directly from in-game commands (say, pose, emit,
  whisper, roll, arrivals/departs).
- Allow players to start/stop logging and annotate scenes (titles, chapter tags,
  plot links, organisation visibility).
- Store data in structured Django models for efficient searching and web display.
- Expose scenes on the website with access restrictions matching in-game
  visibility rules.
- Maintain deterministic scene numbering (Scene 1, 2, 3, ...).

## High-Level Architecture

```
+--------------------+       +---------------------+
| In-game Commands   | ----> | utils.scene_logger  |
| (commands/*.py)    |       | (service layer)     |
+--------------------+       +---------------------+
           |                             |
           v                             v
+--------------------+       +---------------------+
| Room Script        |       | Django Models       |
| SceneTrackerScript |       | (web.scenes.models) |
+--------------------+       +---------------------+
                                          |
                                          v
                               +---------------------+
                               | Web Views / Templates|
                               | (web/scenes, templates)
                               +---------------------+
```

### Key Components

- **Command overrides** (`commands/overrides/speech.py`, `commands/emit.py`,
  `commands/cortex_roll.py`): capture IC output when a scene is active.
- **Scene command suite** (`commands/scenes.py`): player-facing controls for
  starting/stopping logs and adding metadata.
- **Scene logger service** (`utils/scene_logger.py`): orchestrates creation,
  participant tracking, entry persistence, and visibility checks.
- **Room script** (`typeclasses/scripts.py:SceneTrackerScript`): attached to a
  room while logging is active; watches joins/leaves and auto-closes scenes.
- **Models** (`web.scenes.models`): normalized tables for logs, participants,
  segments, entries.
- **Web views/templates** (`web/scenes/views.py`, `web/templates/website/scenes`):
  list, detail, and download pages scoped to permitted viewers.

## Data Model Summary

- `SceneLog`: top-level record with room reference, visibility (private,
  organisation, event), status (active/completed/archived/deleted), chapter FK,
  optional title, M2M to organisations and plots, timestamps, and auto-closed
  flag.
- `SceneParticipant`: link between scene and character/account plus first join,
  last leave, and "present" flag.
- `SceneParticipantSegment`: join/leave pairs used for per-participant transcript
  filtering.
- `SceneEntry`: ordered list of log entries (emit, say, pose, roll, whisper,
  arrival, depart, system) with actor/target references and both raw ANSI text
  and stripped plain text for search.

## In-Game Commands

All commands live in `commands/scenes.py` and are registered via
`commands/default_cmdsets.py`.

### Starting Scenes

- `@scene/startlog`: begin logging a **private** scene in the current room (one
  active scene per room). Autoselects the current chapter. Private scenes are
  only visible to participants and staff.
- `@scene/eventlog`: begin logging a **public event** scene. Event scenes are
  visible to everyone (including non-logged-in website visitors) and will not
  auto-close when the room empties.
- `@scene/orglog`: begin logging an **organisation-restricted** scene. These
  scenes are visible to all members of organisations you specify with
  `@scene/org`, and will not auto-close when the room empties.

### Managing Scenes

- `@scene/endlog [scene]`: finalize the active scene (or a specific scene by ID).
  Remote ending by scene number is staff-only.
- `@scene/title [scene]=<title>`: set or update the scene title.
- `@scene/plot [scene]=<plot id or name>[,<plot>...]`: associate plots with the
  scene.
- `@scene/visibility <scene>=<visibility>`: **staff only** - retroactively change
  visibility between private, organisation, and event. Players should use the
  appropriate start command instead.
- `@scene/org [scene]=<organisation>[,<organisation>...]`: grant organisation
  access to an organisation scene.
- `@scene/list`: show the 20 most recent scenes the player can access.

Syntax supports optional explicit scene IDs (`@scene/title 12=New Title`),
falling back to the active scene, and then the most recent scene where
permitted. Staff can operate on any scene; players are limited to scenes where
they were participants.

### Captured Commands

- `say`, `pose`, `emit`, `whisper`: overridden to record the formatted message
  after broadcasting.
- `roll`: logs result messages from the Cortex rolling system.
- Room script (`SceneTrackerScript`) records arrivals (`at_object_receive`) and
  departures (`at_object_leave`), auto-finalizing when the room empties.

## Scene Lifecycle

1. Player runs `@scene/startlog`, `@scene/eventlog`, or `@scene/orglog`. Service
   creates `SceneLog` with appropriate visibility, attaches `SceneTrackerScript`,
   and registers present participants.
2. While active, speech/roll commands feed entries via `scene_logger.record_entry`.
3. Participants arriving/leaving update `SceneParticipant` and `SceneParticipantSegment`.
4. Closing (`@scene/endlog` or auto-close) sets status to completed, removes room
   reference, and closes open segments. **Note**: Only **private** scenes auto-close
   when the room empties. Organisation and event scenes must be manually ended.
5. Players can continue to edit metadata (title, plots, organisations) if they
   participated; staff can archive or delete scenes via admin tools (future work).

## Web Interface

- **Scene list** (`/scenes/`): filter by keyword, chapter, plot, visibility; only
  shows scenes the viewer may access (public, events, participant scenes, or
  organisation scenes for members). Pagination defaults to 25 per page.
- **Scene detail** (`/scenes/<id>/`): shows metadata, participant list, and
  transcript filtered to the viewer's participation window (unless visibility
  lifts restrictions). Transcript entries show entry type badges and timestamps.
- **Download** (`/scenes/<id>/download/`): plain-text export of the same filtered
  transcript.

Templates and views live under `web/scenes` and `web/templates/website/scenes`.

## Permissions

- Scene commands require `perm(Player)` by default.
- Editing metadata/visibility requires participant status or staff lock
  (`perm(Admin) or perm(Builder) or perm(Helper)`).
- Event/public scenes are accessible to all; organisation scenes require
  membership; private scenes require participation (enforced by both commands
  and web views).

## Extending the System

- Add additional command hooks by calling `scene_logger.record_entry` with the
  appropriate entry type.
- Define staff/admin tools for archiving/deleting scenes as needed.
- Add search indexing or API endpoints by leveraging the plain-text fields.
- For additional visibility levels (e.g., factions), extend
  `SceneLog.Visibility` and update `scene_allows_viewer` and command validations.

## Testing Notes

- Unit tests should cover command flows, visibility checks, and web permissions.
- Current placeholder tests live in `tests/test_scene_logging.py`; expand to cover
  new behaviours.
- Run `pytest` after changes; migrations via `evennia migrate` as usual.

## Future Ideas

- Admin dashboard for scene moderation.
- Scene comparison/diff tool for editing history.
- Web-based tagging UI for players.
- API endpoints for exporting scenes to external tools.
