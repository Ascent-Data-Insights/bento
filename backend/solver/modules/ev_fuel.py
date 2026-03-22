"""EV/Fuel Range constraint module (stub).

Adds battery/fuel range limits and charging/refueling station routing.
Not yet implemented — raises NotImplementedError when added to model.
"""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo
from pydantic import BaseModel

from backend.solver.module import ConstraintModule, ModuleMetadata
from backend.solver.modules import register


class EvFuelData(BaseModel):
    pass


@register
class EvFuelModule(ConstraintModule):
    implemented: bool = False

    def get_metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            key="ev_fuel",
            name="EV/Fuel Range",
            description=(
                "Enforces battery or fuel range limits per vehicle and routes "
                "vehicles through charging or refueling stations as needed."
            ),
        )

    def get_data_schema(self) -> type[BaseModel]:
        return EvFuelData

    def validate(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> list[str]:
        return []

    def add_to_model(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> None:
        raise NotImplementedError("EvFuelModule is not yet implemented.")
