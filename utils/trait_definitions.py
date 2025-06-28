"""
Definitions for character traits, including attributes, skills, and distinctions.
"""
from dataclasses import dataclass
from typing import List

@dataclass
class TraitDefinition:
    """Represents a trait definition with its key, name, and description."""
    key: str
    name: str
    description: str
    default_value: int

# Attribute definitions (all start at d6 - "typical person")
ATTRIBUTES: List[TraitDefinition] = [
    TraitDefinition("prowess", "Prowess", "Strength, endurance and ability to fight", 6),
    TraitDefinition("finesse", "Finesse", "Dexterity and agility", 6),
    TraitDefinition("leadership", "Leadership", "Capacity as a leader", 6),
    TraitDefinition("social", "Social", "Charisma and social navigation", 6),
    TraitDefinition("acuity", "Acuity", "Perception and information processing", 6),
    TraitDefinition("erudition", "Erudition", "Learning and recall ability", 6)
]

# Skill definitions (all start at d4 - "untrained")
SKILLS: List[TraitDefinition] = [
    TraitDefinition("administration", "Administration", "Organizing affairs of large groups", 4),
    TraitDefinition("arcana", "Arcana", "Knowledge of magic", 4),
    TraitDefinition("athletics", "Athletics", "General physical feats", 4),
    TraitDefinition("dexterity", "Dexterity", "Precision physical feats", 4),
    TraitDefinition("diplomacy", "Diplomacy", "Protocol and high politics", 4),
    TraitDefinition("direction", "Direction", "Leading in non-combat", 4),
    TraitDefinition("exploration", "Exploration", "Wilderness and ruins", 4),
    TraitDefinition("fighting", "Fighting", "Melee combat", 4),
    TraitDefinition("influence", "Influence", "Personal persuasion", 4),
    TraitDefinition("learning", "Learning", "Education and research", 4),
    TraitDefinition("making", "Making", "Crafting and building", 4),
    TraitDefinition("medicine", "Medicine", "Healing and medical knowledge", 4),
    TraitDefinition("perception", "Perception", "Awareness and searching", 4),
    TraitDefinition("performance", "Performance", "Entertainment arts", 4),
    TraitDefinition("presentation", "Presentation", "Style and bearing", 4),
    TraitDefinition("rhetoric", "Rhetoric", "Public speaking", 4),
    TraitDefinition("seafaring", "Seafaring", "Sailing and navigation", 4),
    TraitDefinition("shooting", "Shooting", "Ranged combat", 4),
    TraitDefinition("warfare", "Warfare", "Military leadership and strategy", 4)
]

# Distinction definitions (all start at d8)
DISTINCTIONS: List[TraitDefinition] = [
    TraitDefinition("concept", "Character Concept", "Core character concept (e.g. Bold Adventurer)", 8),
    TraitDefinition("culture", "Culture", "Character's cultural origin", 8),
    TraitDefinition("vocation", "Vocation", "Character's profession or calling", 8)
] 