"""Co-delivery constraint module.

Ensures all resources associated with a location arrive on the same vehicle.
"""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo
from pydantic import BaseModel

from backend.solver.module import ConstraintModule, ModuleMetadata
from backend.solver.modules import register


class CoDeliveryData(BaseModel):
    locations: list[str] = []


@register
class CoDeliveryModule(ConstraintModule):
    implemented: bool = True

    def get_metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            key="co_delivery",
            name="Co-delivery",
            description="All resources for a location must arrive on the same vehicle.",
        )

    def get_data_schema(self) -> type[BaseModel]:
        return CoDeliveryData

    def validate(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> list[str]:
        assert isinstance(data, CoDeliveryData)
        errors: list[str] = []
        location_ids = set(model.N)
        for loc_id in data.locations:
            if loc_id not in location_ids:
                errors.append(
                    f"Co-delivery references unknown location '{loc_id}'."
                )
        return errors

    def add_to_model(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> None:
        assert isinstance(data, CoDeliveryData)
        request = model._request

        # No resources means nothing to co-deliver
        if not request.resources:
            return

        # Determine target locations
        if data.locations:
            target_locations = set(data.locations)
        else:
            # Default: all locations with required_resources
            target_locations = {
                loc.id for loc in request.locations if loc.required_resources
            }

        if not target_locations:
            return

        # Build resource groups per location
        consumed_satisfiers = model._consumed_satisfiers
        swv_satisfiers = model._swv_satisfiers

        # Collect constraint tuples: (location, reference_resource, other_resource)
        link_set: list[tuple[str, str, str]] = []

        for loc_id in target_locations:
            # Gather all resources associated with this location
            group: set[str] = set()

            # Consumed resources with dropoff at this location
            for r in request.resources:
                if not r.stays_with_vehicle and r.dropoff_location_id == loc_id:
                    group.add(r.id)

            # SWV resources that satisfy requirements at this location
            for (sat_loc, sat_idx), resource_ids in swv_satisfiers.items():
                if sat_loc == loc_id:
                    group.update(resource_ids)

            if len(group) < 2:
                continue

            # Pick reference resource (alphabetically first for determinism)
            sorted_group = sorted(group)
            r0 = sorted_group[0]
            for r in sorted_group[1:]:
                link_set.append((loc_id, r0, r))

        if not link_set:
            return

        # Create constraint
        model.CO_DELIVERY_LINKS = pyo.Set(
            initialize=link_set, dimen=3
        )

        def co_delivery_rule(
            model_: pyo.ConcreteModel, loc: str, r0: str, r: str, v: str
        ) -> Any:
            return model_.w[v, r] == model_.w[v, r0]

        model.co_delivery_link = pyo.Constraint(
            model.CO_DELIVERY_LINKS, model.V, rule=co_delivery_rule
        )

    def extract_results(
        self, model: pyo.ConcreteModel, data: BaseModel
    ) -> dict[str, Any]:
        return {}
