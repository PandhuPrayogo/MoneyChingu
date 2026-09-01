from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseSkill(ABC):
    """
    Abstract Base Class for Modular AI Agent Skills.
    Each skill defines its capabilities, parameters, and execution logic.
    """
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the skill with provided keyword arguments."""
        pass

    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert skill metadata to function calling schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
