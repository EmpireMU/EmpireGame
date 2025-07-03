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
    TraitDefinition("mind", "Mind", "", 6),
    TraitDefinition("spirit", "Spirit", "", 6),
    TraitDefinition("social", "Social", "", 6),
    TraitDefinition("leadership", "Leadership", "", 6),
    TraitDefinition("prowess", "Prowess", "", 6),
    TraitDefinition("finesse", "Finesse", "", 6)
]

# Skill definitions (all start at d4 - "untrained")
SKILLS: List[TraitDefinition] = [
    TraitDefinition("administration", "Administration", "", 4),
    TraitDefinition("arcana", "Arcana", "", 4),
    TraitDefinition("athletics", "Athletics", "", 4),
    TraitDefinition("composure", "Composure", "", 4),
    TraitDefinition("dexterity", "Dexterity", "", 4),
    TraitDefinition("espionage", "Espionage", "", 4),
    TraitDefinition("exploration", "Exploration", "", 4),
    TraitDefinition("fighting", "Fighting", "", 4),
    TraitDefinition("influence", "Influence", "", 4),
    TraitDefinition("learning", "Learning", "", 4),
    TraitDefinition("making", "Making", "", 4),
    TraitDefinition("medicine", "Medicine", "", 4),
    TraitDefinition("perception", "Perception", "", 4),
    TraitDefinition("performance", "Performance", "", 4),
    TraitDefinition("politics", "Politics", "", 4),
    TraitDefinition("rhetoric", "Rhetoric", "", 4),
    TraitDefinition("seafaring", "Seafaring", "", 4),
    TraitDefinition("survival", "Survival", "", 4),
    TraitDefinition("warfare", "Warfare", "", 4)
]

# Distinction definitions (all start at d8)
DISTINCTIONS: List[TraitDefinition] = [
    TraitDefinition("concept", "Character Concept", "Core character concept (e.g. Bold Adventurer)", 8),
    TraitDefinition("culture", "Culture", "Character's cultural origin", 8),
    TraitDefinition("vocation", "Vocation", "Character's profession or calling", 8)
] 