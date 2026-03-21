from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import pyomo.environ as pyo

from backend.schemas.solve import SolveRequest, SolveResponse, SolveStatus
from backend.schemas.profile import ClientProfile

BASELINES_PATH = Path(__file__).parent / "baselines.json"


def pytest_addoption(parser):
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Update regression test baselines with current results",
    )


@pytest.fixture
def update_baselines(request):
    return request.config.getoption("--update-baselines")


@dataclass
class ExpectedMetrics:
    status: SolveStatus = SolveStatus.OPTIMAL
    max_objective: float = float("inf")
    max_vehicles_used: int = 100
    all_resources_served: bool = True
    all_locations_served: bool = True
    time_windows_respected: bool = False
    co_delivery_enforced: bool = False


def validate_solution(
    response: SolveResponse,
    request: SolveRequest,
    profile: ClientProfile,
    expected: ExpectedMetrics,
) -> None:
    """Validate a solver response against expected regression metrics."""

    # Status
    assert response.status == expected.status, (
        f"Expected status {expected.status}, got {response.status}"
    )

    # Objective value
    assert response.objective_value is not None, "Objective value is None"
    assert response.objective_value <= expected.max_objective, (
        f"Objective {response.objective_value} exceeds max {expected.max_objective}"
    )

    # Vehicle count
    assert len(response.routes) <= expected.max_vehicles_used, (
        f"Used {len(response.routes)} vehicles, max allowed {expected.max_vehicles_used}"
    )

    # Resources served
    if expected.all_resources_served:
        assert response.unserved_resources == [], (
            f"Unserved resources: {response.unserved_resources}"
        )

    # Locations served
    if expected.all_locations_served:
        assert response.unserved_locations == [], (
            f"Unserved locations: {response.unserved_locations}"
        )

    # Time windows respected
    if expected.time_windows_respected:
        assert "time_windows" in response.module_results, (
            "time_windows module results missing"
        )
        arrival_times = response.module_results["time_windows"]["arrival_times"]
        windows_data = request.module_data.get("time_windows", {})
        windows_list = windows_data.get("windows", [])
        window_map = {w["location_id"]: (w["earliest"], w["latest"]) for w in windows_list}

        eps = 0.1  # tolerance for floating point
        for v_id, stops in arrival_times.items():
            for loc_id, arrival in stops.items():
                if loc_id in window_map:
                    earliest, latest = window_map[loc_id]
                    assert arrival >= earliest - eps, (
                        f"Vehicle {v_id} arrives at {loc_id} at {arrival}, "
                        f"before earliest {earliest}"
                    )
                    assert arrival <= latest + eps, (
                        f"Vehicle {v_id} arrives at {loc_id} at {arrival}, "
                        f"after latest {latest}"
                    )

    # Co-delivery enforced
    if expected.co_delivery_enforced:
        # Build map: resource_id -> vehicle_id (from route data)
        resource_to_vehicle: dict[str, str] = {}
        for route in response.routes:
            for stop in route.stops:
                for r_id in stop.resources_picked_up:
                    resource_to_vehicle[r_id] = route.vehicle_id

        # For each location with requirements, check all associated resources are on same vehicle
        resource_by_id = {r.id: r for r in request.resources}
        for loc in request.locations:
            if not loc.required_resources:
                continue

            # Gather resources for this location
            loc_resources: set[str] = set()
            for r in request.resources:
                # Consumed resources dropped off here
                if not r.stays_with_vehicle and r.dropoff_location_id == loc.id:
                    loc_resources.add(r.id)
                # SWV resources that match requirements here
                if r.stays_with_vehicle:
                    for req in loc.required_resources:
                        matches = True
                        for key, val in req.attributes.items():
                            if key not in r.attributes:
                                matches = False
                                break
                            r_val = r.attributes[key]
                            if isinstance(val, list):
                                if isinstance(r_val, list):
                                    if not all(elem in r_val for elem in val):
                                        matches = False
                                else:
                                    if not all(elem == r_val for elem in val):
                                        matches = False
                            else:
                                if isinstance(r_val, list):
                                    if val not in r_val:
                                        matches = False
                                elif r_val != val:
                                    matches = False
                        if matches:
                            loc_resources.add(r.id)

            if len(loc_resources) < 2:
                continue

            # All resources for this location should be on the same vehicle
            vehicles_used = {resource_to_vehicle.get(r_id) for r_id in loc_resources if r_id in resource_to_vehicle}
            vehicles_used.discard(None)
            assert len(vehicles_used) <= 1, (
                f"Co-delivery violated at {loc.id}: resources {loc_resources} "
                f"split across vehicles {vehicles_used}"
            )


def compare_to_baseline(
    scenario_name: str,
    response: SolveResponse,
    update: bool,
    tolerance: float = 0.05,
) -> None:
    """Compare response metrics to stored baseline.

    If update=True, writes current values as the new baseline.
    If update=False, compares against stored baseline and fails if
    objective changes by more than tolerance (default 5%).
    """
    baselines = _load_baselines()

    current = {
        "objective_value": response.objective_value,
        "vehicles_used": len(response.routes),
    }

    if update:
        baselines[scenario_name] = current
        _save_baselines(baselines)
        return

    if scenario_name not in baselines:
        pytest.skip(f"No baseline for '{scenario_name}'. Run with --update-baselines to create.")

    baseline = baselines[scenario_name]
    baseline_obj = baseline["objective_value"]
    current_obj = current["objective_value"]

    if baseline_obj == 0:
        # Avoid division by zero
        assert current_obj == 0, (
            f"Scenario '{scenario_name}': baseline objective was 0, now {current_obj}"
        )
        return

    pct_change = (current_obj - baseline_obj) / abs(baseline_obj)

    assert abs(pct_change) <= tolerance, (
        f"Scenario '{scenario_name}': objective changed by {pct_change:+.1%} "
        f"(baseline={baseline_obj}, current={current_obj}, tolerance=±{tolerance:.0%})"
    )


def _load_baselines() -> dict:
    if not BASELINES_PATH.exists():
        return {}
    return json.loads(BASELINES_PATH.read_text())


def _save_baselines(baselines: dict) -> None:
    BASELINES_PATH.write_text(json.dumps(baselines, indent=2, sort_keys=True) + "\n")


@pytest.fixture
def cbc_available():
    solver = pyo.SolverFactory("cbc")
    if not solver.available():
        pytest.skip("CBC solver not available")
    return solver
