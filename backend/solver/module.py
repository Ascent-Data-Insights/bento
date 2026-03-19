from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
import pyomo.environ as pyo


@dataclass
class ModuleMetadata:
    """Declarative metadata for a constraint module."""
    key: str
    name: str
    description: str
    required_dimensions: dict[str, list[str]] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


class ConstraintModule(ABC):
    """Abstract base class for all constraint modules (built-in and custom)."""

    @abstractmethod
    def get_metadata(self) -> ModuleMetadata:
        """Return static metadata about this module."""
        ...

    @abstractmethod
    def get_data_schema(self) -> type[BaseModel]:
        """Return a Pydantic model class describing the data this module requires.

        The orchestrator validates incoming request data against this schema
        before calling add_to_model.
        """
        ...

    @abstractmethod
    def validate(self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]) -> list[str]:
        """Run semantic validation beyond schema checks.

        Called after the base model is built but before add_to_model.
        Return a list of error strings. Empty list means valid.
        """
        ...

    @abstractmethod
    def add_to_model(self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]) -> None:
        """Mutate the Pyomo model in place.

        Add sets, parameters, variables, and/or constraints.
        All added components MUST be prefixed with the module key
        (e.g., model.time_windows_arrival).
        """
        ...

    def extract_results(self, model: pyo.ConcreteModel, data: BaseModel) -> dict[str, Any]:
        """Extract module-specific results from a solved model.

        Optional — default returns empty dict. Override to pull
        module-specific variable values from the solution.
        """
        return {}
