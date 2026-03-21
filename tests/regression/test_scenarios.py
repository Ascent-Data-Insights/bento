"""Regression test scenarios for the routing solver.

Each scenario defines a realistic routing problem, solves it, and validates
that key metrics remain stable across code changes. These tests check
objective bounds, feasibility, and constraint satisfaction — NOT exact
route ordering (which can vary between equivalent optimal solutions).
"""

import pytest

from backend.schemas.solve import (
    Compartment,
    Location,
    Resource,
    ResourceRequirement,
    SolveRequest,
    SolveStatus,
    Vehicle,
)
from backend.schemas.profile import (
    ClientProfile,
    DimensionSelections,
    FleetComposition,
    ModuleConfig,
    OriginModel,
)
from backend.solver.orchestrator import Orchestrator
from tests.regression.conftest import ExpectedMetrics, validate_solution, compare_to_baseline


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _grasscutting_locations():
    return [
        Location(id="depot", latitude=40.7128, longitude=-74.0060),
        Location(
            id="site_a", latitude=40.7228, longitude=-74.0000, service_time=60,
            required_resources=[
                ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                ResourceRequirement(attributes={"type": "mower"}, quantity=1),
            ],
        ),
        Location(
            id="site_b", latitude=40.7028, longitude=-73.9900, service_time=60,
            required_resources=[
                ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                ResourceRequirement(attributes={"type": "mower"}, quantity=1),
            ],
        ),
        Location(
            id="site_c", latitude=40.7328, longitude=-74.0100, service_time=30,
            required_resources=[
                ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
            ],
        ),
    ]


def _grasscutting_vehicles():
    return [
        Vehicle(
            id="truck_1", start_location_id="depot", end_location_id="depot",
            compartments=[
                Compartment(type="cab", capacity={"seats": 2}),
                Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
            ],
        ),
        Vehicle(
            id="truck_2", start_location_id="depot", end_location_id="depot",
            compartments=[
                Compartment(type="cab", capacity={"seats": 2}),
                Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
            ],
        ),
    ]


def _grasscutting_resources():
    return [
        Resource(
            id="worker_1", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"}, stays_with_vehicle=True,
        ),
        Resource(
            id="worker_2", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"}, stays_with_vehicle=True,
        ),
        Resource(
            id="worker_3", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"}, stays_with_vehicle=True,
        ),
        Resource(
            id="mower_1", pickup_location_id="depot",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"}, stays_with_vehicle=True,
        ),
        Resource(
            id="mower_2", pickup_location_id="depot",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"}, stays_with_vehicle=True,
        ),
        Resource(
            id="mulch_site_a", pickup_location_id="depot", dropoff_location_id="site_a",
            compartment_types=["bed"], capacity_consumption={"weight": 50, "volume": 3},
            quantity=2,
        ),
    ]


def _grasscutting_distance_matrix():
    return {
        "depot": {"depot": 0, "site_a": 5, "site_b": 8, "site_c": 6},
        "site_a": {"depot": 5, "site_a": 0, "site_b": 4, "site_c": 7},
        "site_b": {"depot": 8, "site_b": 0, "site_a": 4, "site_c": 3},
        "site_c": {"depot": 6, "site_a": 7, "site_b": 3, "site_c": 0},
    }


def _grasscutting_time_matrix():
    """Time matrix — same values as distance for simplicity (1 unit distance = 1 unit time)."""
    return _grasscutting_distance_matrix()


def _base_profile(**overrides):
    defaults = dict(
        tenant_id="regression_test",
        name="Regression Test",
        dimensions=DimensionSelections(
            origin_model=OriginModel.SINGLE_DEPOT,
            fleet_composition=FleetComposition.HETEROGENEOUS,
        ),
        objective={"distance": 1.0},
        modules=[],
    )
    defaults.update(overrides)
    return ClientProfile(**defaults)


# ---------------------------------------------------------------------------
# Scenario 1: Grasscutting basic (no modules)
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_grasscutting_basic():
    request = SolveRequest(
        locations=_grasscutting_locations(),
        vehicles=_grasscutting_vehicles(),
        resources=_grasscutting_resources(),
        matrices={"distance": _grasscutting_distance_matrix()},
    )
    profile = _base_profile()
    expected = ExpectedMetrics(
        max_objective=50.0,  # generous ceiling; optimal is likely ~28-32
        max_vehicles_used=2,
    )
    return request, profile, expected


def test_grasscutting_basic(scenario_grasscutting_basic, cbc_available, update_baselines):
    request, profile, expected = scenario_grasscutting_basic
    response = Orchestrator().solve(request, profile)
    validate_solution(response, request, profile, expected)
    compare_to_baseline("grasscutting_basic", response, update_baselines)


# ---------------------------------------------------------------------------
# Scenario 2: Grasscutting + time windows
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_grasscutting_time_windows():
    request = SolveRequest(
        locations=_grasscutting_locations(),
        vehicles=_grasscutting_vehicles(),
        resources=_grasscutting_resources(),
        matrices={
            "distance": _grasscutting_distance_matrix(),
            "time": _grasscutting_time_matrix(),
        },
        module_data={
            "time_windows": {
                "windows": [
                    {"location_id": "site_a", "earliest": 0, "latest": 200},
                    {"location_id": "site_b", "earliest": 0, "latest": 200},
                    {"location_id": "site_c", "earliest": 0, "latest": 200},
                ],
            },
        },
    )
    profile = _base_profile(modules=[ModuleConfig(key="time_windows")])
    expected = ExpectedMetrics(
        max_objective=50.0,
        max_vehicles_used=2,
        time_windows_respected=True,
    )
    return request, profile, expected


def test_grasscutting_time_windows(scenario_grasscutting_time_windows, cbc_available, update_baselines):
    request, profile, expected = scenario_grasscutting_time_windows
    response = Orchestrator().solve(request, profile)
    validate_solution(response, request, profile, expected)
    compare_to_baseline("grasscutting_time_windows", response, update_baselines)


# ---------------------------------------------------------------------------
# Scenario 3: Grasscutting + co-delivery
#
# Uses a simplified resource set (2 workers, 2 mowers) so that the
# co-delivery constraint is satisfiable: each truck carries exactly one
# worker and one mower, letting the two sites that need [mower_op + mower]
# each be served by a separate truck.
# ---------------------------------------------------------------------------

def _co_delivery_resources():
    """Two workers and two mowers — one pair per truck."""
    return [
        Resource(
            id="worker_1", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"}, stays_with_vehicle=True,
        ),
        Resource(
            id="worker_2", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"}, stays_with_vehicle=True,
        ),
        Resource(
            id="mower_1", pickup_location_id="depot",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"}, stays_with_vehicle=True,
        ),
        Resource(
            id="mower_2", pickup_location_id="depot",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"}, stays_with_vehicle=True,
        ),
    ]


@pytest.fixture
def scenario_grasscutting_co_delivery():
    request = SolveRequest(
        locations=_grasscutting_locations(),
        vehicles=_grasscutting_vehicles(),
        resources=_co_delivery_resources(),
        matrices={"distance": _grasscutting_distance_matrix()},
        module_data={"co_delivery": {}},
    )
    profile = _base_profile(modules=[ModuleConfig(key="co_delivery")])
    expected = ExpectedMetrics(
        max_objective=60.0,  # co-delivery may increase distance
        max_vehicles_used=2,
        co_delivery_enforced=True,
    )
    return request, profile, expected


def test_grasscutting_co_delivery(scenario_grasscutting_co_delivery, cbc_available, update_baselines):
    request, profile, expected = scenario_grasscutting_co_delivery
    response = Orchestrator().solve(request, profile)
    validate_solution(response, request, profile, expected)
    compare_to_baseline("grasscutting_co_delivery", response, update_baselines)


# ---------------------------------------------------------------------------
# Scenario 4: Grasscutting full (time windows + co-delivery)
#
# Same simplified resource set as the co-delivery scenario.
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_grasscutting_full():
    request = SolveRequest(
        locations=_grasscutting_locations(),
        vehicles=_grasscutting_vehicles(),
        resources=_co_delivery_resources(),
        matrices={
            "distance": _grasscutting_distance_matrix(),
            "time": _grasscutting_time_matrix(),
        },
        module_data={
            "time_windows": {
                "windows": [
                    {"location_id": "site_a", "earliest": 0, "latest": 200},
                    {"location_id": "site_b", "earliest": 0, "latest": 200},
                    {"location_id": "site_c", "earliest": 0, "latest": 200},
                ],
            },
            "co_delivery": {},
        },
    )
    profile = _base_profile(
        modules=[ModuleConfig(key="time_windows"), ModuleConfig(key="co_delivery")]
    )
    expected = ExpectedMetrics(
        max_objective=60.0,
        max_vehicles_used=2,
        time_windows_respected=True,
        co_delivery_enforced=True,
    )
    return request, profile, expected


def test_grasscutting_full(scenario_grasscutting_full, cbc_available, update_baselines):
    request, profile, expected = scenario_grasscutting_full
    response = Orchestrator().solve(request, profile)
    validate_solution(response, request, profile, expected)
    compare_to_baseline("grasscutting_full", response, update_baselines)


# ---------------------------------------------------------------------------
# Scenario 5: Multi-vehicle scaling
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_multi_vehicle_scaling():
    locations = [
        Location(id="depot", latitude=40.71, longitude=-74.00),
        Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                 required_resources=[
                     ResourceRequirement(attributes={"skill": "worker"}, quantity=1),
                 ]),
        Location(id="site_b", latitude=40.73, longitude=-73.99, service_time=30,
                 required_resources=[
                     ResourceRequirement(attributes={"skill": "worker"}, quantity=1),
                 ]),
        Location(id="site_c", latitude=40.70, longitude=-74.01, service_time=30,
                 required_resources=[
                     ResourceRequirement(attributes={"skill": "worker"}, quantity=1),
                 ]),
        Location(id="site_d", latitude=40.74, longitude=-73.98, service_time=30,
                 required_resources=[
                     ResourceRequirement(attributes={"skill": "worker"}, quantity=1),
                 ]),
        Location(id="site_e", latitude=40.69, longitude=-74.02, service_time=30,
                 required_resources=[
                     ResourceRequirement(attributes={"skill": "worker"}, quantity=1),
                 ]),
    ]
    vehicles = [
        Vehicle(
            id=f"truck_{i}", start_location_id="depot", end_location_id="depot",
            compartments=[Compartment(type="cab", capacity={"seats": 3})],
        )
        for i in range(1, 4)
    ]
    resources = [
        Resource(
            id=f"worker_{i}", pickup_location_id="depot",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "worker"}, stays_with_vehicle=True,
        )
        for i in range(1, 6)
    ]
    # 6x6 distance matrix
    locs = ["depot", "site_a", "site_b", "site_c", "site_d", "site_e"]
    raw_dists = {
        ("depot", "site_a"): 5, ("depot", "site_b"): 8, ("depot", "site_c"): 6,
        ("depot", "site_d"): 10, ("depot", "site_e"): 7,
        ("site_a", "site_b"): 4, ("site_a", "site_c"): 7, ("site_a", "site_d"): 6,
        ("site_a", "site_e"): 9,
        ("site_b", "site_c"): 3, ("site_b", "site_d"): 5, ("site_b", "site_e"): 8,
        ("site_c", "site_d"): 9, ("site_c", "site_e"): 4,
        ("site_d", "site_e"): 7,
    }
    matrix: dict[str, dict[str, float]] = {}
    for loc in locs:
        matrix[loc] = {}
        for other in locs:
            if loc == other:
                matrix[loc][other] = 0.0
            elif (loc, other) in raw_dists:
                matrix[loc][other] = float(raw_dists[(loc, other)])
            elif (other, loc) in raw_dists:
                matrix[loc][other] = float(raw_dists[(other, loc)])

    request = SolveRequest(
        locations=locations,
        vehicles=vehicles,
        resources=resources,
        matrices={"distance": matrix},
    )
    profile = _base_profile()
    expected = ExpectedMetrics(
        max_objective=80.0,  # generous ceiling for 5 sites
        max_vehicles_used=3,
    )
    return request, profile, expected


def test_multi_vehicle_scaling(scenario_multi_vehicle_scaling, cbc_available, update_baselines):
    request, profile, expected = scenario_multi_vehicle_scaling
    response = Orchestrator().solve(request, profile)
    validate_solution(response, request, profile, expected)
    compare_to_baseline("multi_vehicle_scaling", response, update_baselines)
