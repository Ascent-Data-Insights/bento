"""Shift Limits constraint module (stub).

Adds maximum drive time and mandatory break constraints per vehicle.
Not yet implemented — raises NotImplementedError when added to model.
"""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo
from pydantic import BaseModel

from backend.solver.module import ConstraintModule, ModuleMetadata
from backend.solver.modules import register


class ShiftLimitsData(BaseModel):
    pass


@register
class ShiftLimitsModule(ConstraintModule):
    implemented: bool = False

    def get_metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            key="shift_limits",
            name="Shift Limits",
            description=(
                "Enforces maximum drive time per shift and inserts mandatory "
                "break periods for drivers."
            ),
        )

    def get_data_schema(self) -> type[BaseModel]:
        return ShiftLimitsData

    def validate(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> list[str]:
        return []

    def add_to_model(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> None:
        raise NotImplementedError("ShiftLimitsModule is not yet implemented.")
