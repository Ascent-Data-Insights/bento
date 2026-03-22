"""Priority/SLA constraint module (stub).

Adds priority tiers with penalty weights for late or missed service.
Not yet implemented — raises NotImplementedError when added to model.
"""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo
from pydantic import BaseModel

from backend.solver.module import ConstraintModule, ModuleMetadata
from backend.solver.modules import register


class PrioritySlaData(BaseModel):
    pass


@register
class PrioritySlaModule(ConstraintModule):
    implemented: bool = False

    def get_metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            key="priority_sla",
            name="Priority/SLA",
            description=(
                "Assigns priority tiers to stops and applies penalty weights "
                "for late or missed service-level agreements."
            ),
        )

    def get_data_schema(self) -> type[BaseModel]:
        return PrioritySlaData

    def validate(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> list[str]:
        return []

    def add_to_model(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> None:
        raise NotImplementedError("PrioritySlaModule is not yet implemented.")
