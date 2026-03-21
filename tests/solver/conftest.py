import pytest
import pyomo.environ as pyo

from backend.schemas.solve import (
    Compartment,
    Location,
    Resource,
    ResourceRequirement,
    SolveRequest,
    Vehicle,
)
from backend.schemas.profile import (
    ClientProfile,
    DimensionSelections,
    FleetComposition,
    OriginModel,
)


@pytest.fixture
def grasscutting_locations():
    return [
        Location(id="depot", latitude=40.7128, longitude=-74.0060, service_time=0),
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


@pytest.fixture
def grasscutting_vehicles():
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


@pytest.fixture
def grasscutting_resources():
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


@pytest.fixture
def grasscutting_matrices(grasscutting_locations):
    """Simple symmetric distance matrix."""
    locs = [loc.id for loc in grasscutting_locations]
    # Use simple distances for test predictability
    dists = {
        ("depot", "site_a"): 5.0, ("depot", "site_b"): 8.0, ("depot", "site_c"): 6.0,
        ("site_a", "site_b"): 4.0, ("site_a", "site_c"): 7.0, ("site_b", "site_c"): 3.0,
    }
    matrix = {}
    for loc in locs:
        matrix[loc] = {}
        for other in locs:
            if loc == other:
                matrix[loc][other] = 0.0
            elif (loc, other) in dists:
                matrix[loc][other] = dists[(loc, other)]
            elif (other, loc) in dists:
                matrix[loc][other] = dists[(other, loc)]
    return {"distance": matrix}


@pytest.fixture
def grasscutting_profile():
    return ClientProfile(
        tenant_id="test", name="Test Landscaper",
        dimensions=DimensionSelections(
            origin_model=OriginModel.SINGLE_DEPOT,
            fleet_composition=FleetComposition.HETEROGENEOUS,
        ),
        objective={"distance": 1.0},
    )


@pytest.fixture
def grasscutting_request(grasscutting_locations, grasscutting_vehicles, grasscutting_resources, grasscutting_matrices):
    return SolveRequest(
        locations=grasscutting_locations,
        vehicles=grasscutting_vehicles,
        resources=grasscutting_resources,
        matrices=grasscutting_matrices,
    )


@pytest.fixture
def cbc_available():
    solver = pyo.SolverFactory("cbc")
    if not solver.available():
        pytest.skip("CBC solver not available")
    return solver
