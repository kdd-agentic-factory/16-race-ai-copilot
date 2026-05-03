"""Conversation memory interface placeholder."""

from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    session_id: str
    turns: list[dict[str, str]] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
