"""Race session memory interface placeholder."""

from dataclasses import dataclass, field


@dataclass
class SessionMemory:
    session_id: str
    facts: dict[str, str] = field(default_factory=dict)

    def remember_fact(self, key: str, value: str) -> None:
        self.facts[key] = value
