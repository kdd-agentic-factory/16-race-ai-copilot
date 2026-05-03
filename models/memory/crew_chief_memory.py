"""Crew chief preference memory interface placeholder."""

from dataclasses import dataclass, field


@dataclass
class CrewChiefMemory:
    crew_chief_id: str
    preferences: dict[str, str] = field(default_factory=dict)
