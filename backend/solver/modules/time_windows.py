"""Time Windows constraint module.

Adds service/delivery windows per location — "visit site A between 8am and 12pm."
Introduces arrival time variables and travel time constraints.
"""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo
from pydantic import BaseModel

from backend.solver.module import ConstraintModule, ModuleMetadata
from backend.solver.modules import register


class TimeWindowEntry(BaseModel):
    location_id: str
    earliest: float
    latest: float


class TimeWindowsData(BaseModel):
    windows: list[TimeWindowEntry]
    big_m: float = 1e6


@register
class TimeWindowsModule(ConstraintModule):
    implemented: bool = True

    def get_metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            key="time_windows",
            name="Time Windows",
            description="Service/delivery windows per location.",
        )

    def get_data_schema(self) -> type[BaseModel]:
        return TimeWindowsData

    def validate(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> list[str]:
        assert isinstance(data, TimeWindowsData)
        errors: list[str] = []
        location_ids = set(model.N)
        seen_locations: set[str] = set()
        for entry in data.windows:
            if entry.location_id not in location_ids:
                errors.append(
                    f"Time window references unknown location '{entry.location_id}'."
                )
            if entry.earliest > entry.latest:
                errors.append(
                    f"Time window for '{entry.location_id}': earliest ({entry.earliest}) > latest ({entry.latest})."
                )
            if entry.location_id in seen_locations:
                errors.append(
                    f"Duplicate time window for location '{entry.location_id}'."
                )
            seen_locations.add(entry.location_id)
        return errors

    def add_to_model(
        self, model: pyo.ConcreteModel, data: BaseModel, config: dict[str, Any]
    ) -> None:
        assert isinstance(data, TimeWindowsData)
        request = model._request
        big_m = data.big_m

        # Build window lookup
        window_map: dict[str, tuple[float, float]] = {}
        for entry in data.windows:
            window_map[entry.location_id] = (entry.earliest, entry.latest)

        windowed_locations = set(window_map.keys())

        # Get travel time matrix: prefer "time", fall back to first matrix key
        matrix_keys = list(request.matrices.keys())
        time_key = "time" if "time" in request.matrices else (matrix_keys[0] if matrix_keys else None)

        # Build arc_set for efficient lookup
        arc_set = set(model.A)

        # Depots — arcs returning to a depot are excluded from the travel time
        # propagation constraint to avoid a closed cycle (arrival[depot] >= ...
        # >= arrival[depot] + k, which is infeasible for k > 0).
        depots = model._depots

        # --- Parameters ---
        model.time_windows_earliest = pyo.Param(
            list(windowed_locations),
            initialize={loc: window_map[loc][0] for loc in windowed_locations},
        )
        model.time_windows_latest = pyo.Param(
            list(windowed_locations),
            initialize={loc: window_map[loc][1] for loc in windowed_locations},
        )

        # --- Variables ---
        model.time_windows_arrival = pyo.Var(
            model.V, model.N, within=pyo.NonNegativeReals
        )

        # --- Constraints ---

        # Travel time linking: if vehicle v goes from i to j, arrival[v,j] >= arrival[v,i] + service_time[i] + travel_time[i,j]
        # Skip arcs returning to depots — including them would form a cycle
        # (arrival[depot] >= ... >= arrival[depot] + k) that is always infeasible.
        def travel_rule(model_: pyo.ConcreteModel, v: str, i: str, j: str) -> Any:
            if (i, j) not in arc_set:
                return pyo.Constraint.Skip
            if j in depots:
                return pyo.Constraint.Skip
            travel_time = 0.0
            if time_key:
                travel_time = pyo.value(model_.cost[time_key, i, j])
            service = pyo.value(model_.service_time[i])
            return (
                model_.time_windows_arrival[v, j]
                >= model_.time_windows_arrival[v, i] + service + travel_time - big_m * (1 - model_.x[v, i, j])
            )

        model.time_windows_travel = pyo.Constraint(
            model.V, model.N, model.N, rule=travel_rule
        )

        # Early window: arrival >= earliest (only when vehicle visits)
        def early_rule(model_: pyo.ConcreteModel, v: str, i: str) -> Any:
            if i not in windowed_locations:
                return pyo.Constraint.Skip
            earliest = pyo.value(model_.time_windows_earliest[i])
            v_start = pyo.value(model_.vehicle_start[v])
            v_end = pyo.value(model_.vehicle_end[v])
            if i == v_start or i == v_end:
                visits_expr = model_.vehicle_used[v]
            else:
                visits_expr = sum(
                    model_.x[v, j, i] for j in model_.N if (j, i) in arc_set
                )
            return model_.time_windows_arrival[v, i] >= earliest - big_m * (1 - visits_expr)

        model.time_windows_early = pyo.Constraint(model.V, model.N, rule=early_rule)

        # Late window: arrival <= latest (only when vehicle visits)
        def late_rule(model_: pyo.ConcreteModel, v: str, i: str) -> Any:
            if i not in windowed_locations:
                return pyo.Constraint.Skip
            latest = pyo.value(model_.time_windows_latest[i])
            v_start = pyo.value(model_.vehicle_start[v])
            v_end = pyo.value(model_.vehicle_end[v])
            if i == v_start or i == v_end:
                visits_expr = model_.vehicle_used[v]
            else:
                visits_expr = sum(
                    model_.x[v, j, i] for j in model_.N if (j, i) in arc_set
                )
            return model_.time_windows_arrival[v, i] <= latest + big_m * (1 - visits_expr)

        model.time_windows_late = pyo.Constraint(model.V, model.N, rule=late_rule)

    def extract_results(
        self, model: pyo.ConcreteModel, data: BaseModel
    ) -> dict[str, Any]:
        assert isinstance(data, TimeWindowsData)
        arrival_times: dict[str, dict[str, float]] = {}
        arc_set = set(model.A)

        for v in model.V:
            vehicle_arrivals: dict[str, float] = {}
            for i in model.N:
                # Check if vehicle visits this location
                v_start = pyo.value(model.vehicle_start[v])
                v_end = pyo.value(model.vehicle_end[v])
                if i == v_start or i == v_end:
                    visits = pyo.value(model.vehicle_used[v])
                else:
                    visits = sum(
                        pyo.value(model.x[v, j, i])
                        for j in model.N
                        if (j, i) in arc_set
                    )
                if visits > 0.5:
                    vehicle_arrivals[i] = round(pyo.value(model.time_windows_arrival[v, i]), 2)
            if vehicle_arrivals:
                arrival_times[v] = vehicle_arrivals

        return {"arrival_times": arrival_times}
