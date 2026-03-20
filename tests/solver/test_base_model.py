import pytest
import pyomo.environ as pyo

from backend.schemas.solve import (
    Location, Vehicle, Compartment, Resource, ResourceRequirement, SolveRequest,
)
from backend.schemas.profile import (
    ClientProfile, DimensionSelections, OriginModel, FleetComposition,
)
from backend.solver.base_model import (
    build_base_model, _derive_depots, _resource_matches_requirement,
    _precompute_requirement_satisfiers, _get_visit_locations,
)


# === Fixtures ===

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
            id="worker_1", pickup_location_id="depot", dropoff_location_id="site_a",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"},
        ),
        Resource(
            id="worker_2", pickup_location_id="depot", dropoff_location_id="site_b",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"},
        ),
        Resource(
            id="worker_3", pickup_location_id="depot", dropoff_location_id="site_c",
            compartment_types=["cab"], capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"},
        ),
        Resource(
            id="mower_1", pickup_location_id="depot", dropoff_location_id="site_a",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"},
        ),
        Resource(
            id="mower_2", pickup_location_id="depot", dropoff_location_id="site_b",
            compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
            attributes={"type": "mower"},
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


# === Helper function tests ===

class TestDeriveDepots:
    def test_single_depot(self, grasscutting_vehicles):
        depots = _derive_depots(grasscutting_vehicles)
        assert depots == {"depot"}

    def test_multi_depot(self):
        vehicles = [
            Vehicle(id="v1", start_location_id="depot_a", end_location_id="depot_a",
                    compartments=[Compartment(type="cab", capacity={"seats": 1})]),
            Vehicle(id="v2", start_location_id="depot_b", end_location_id="depot_b",
                    compartments=[Compartment(type="cab", capacity={"seats": 1})]),
        ]
        assert _derive_depots(vehicles) == {"depot_a", "depot_b"}

    def test_none_end_defaults_to_start(self):
        vehicles = [
            Vehicle(id="v1", start_location_id="depot", end_location_id=None,
                    compartments=[Compartment(type="cab", capacity={"seats": 1})]),
        ]
        assert _derive_depots(vehicles) == {"depot"}


class TestResourceMatchesRequirement:
    def test_exact_match(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"})
        req = ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1)
        assert _resource_matches_requirement(r, req) is True

    def test_superset_matches(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator", "cert": "safety"})
        req = ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1)
        assert _resource_matches_requirement(r, req) is True

    def test_missing_attribute_fails(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"cert": "safety"})
        req = ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1)
        assert _resource_matches_requirement(r, req) is False

    def test_empty_requirement_matches_any(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={})
        req = ResourceRequirement(attributes={}, quantity=1)
        assert _resource_matches_requirement(r, req) is True

    def test_list_attribute_matching(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skills": ["mower", "hedger", "chainsaw"]})
        req = ResourceRequirement(attributes={"skills": ["mower", "hedger"]}, quantity=1)
        assert _resource_matches_requirement(r, req) is True

    def test_list_attribute_missing_element(self):
        r = Resource(id="w1", pickup_location_id="d", dropoff_location_id="s",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skills": ["mower"]})
        req = ResourceRequirement(attributes={"skills": ["mower", "hedger"]}, quantity=1)
        assert _resource_matches_requirement(r, req) is False


class TestPrecomputeRequirementSatisfiers:
    def test_grasscutting(self, grasscutting_locations, grasscutting_resources):
        satisfiers = _precompute_requirement_satisfiers(grasscutting_locations, grasscutting_resources)
        # site_a req 0: skill=mower_operator AND dropoff=site_a -> worker_1 only
        assert set(satisfiers[("site_a", 0)]) == {"worker_1"}
        # site_a req 1: type=mower AND dropoff=site_a -> mower_1 only
        assert set(satisfiers[("site_a", 1)]) == {"mower_1"}
        # site_c req 0: skill=mower_operator AND dropoff=site_c -> worker_3 only
        assert set(satisfiers[("site_c", 0)]) == {"worker_3"}


class TestGetVisitLocations:
    def test_grasscutting(self, grasscutting_locations, grasscutting_resources):
        depots = {"depot"}
        visit = _get_visit_locations(grasscutting_locations, grasscutting_resources, depots)
        # All 3 sites need visiting, depot is both a depot and a pickup point
        # Depot IS a pickup location for resources, so it's in visit_locations too
        assert "site_a" in visit
        assert "site_b" in visit
        assert "site_c" in visit


# === Model building tests ===

class TestBuildBaseModel:
    def test_sets(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        assert set(model.N) == {"depot", "site_a", "site_b", "site_c"}
        assert set(model.D) == {"depot"}
        assert set(model.V) == {"truck_1", "truck_2"}
        assert len(list(model.R)) == 5
        assert set(model.CT) == {"cab", "bed"}
        assert "seats" in set(model.CAP_DIMS)
        assert "weight" in set(model.CAP_DIMS)
        assert "volume" in set(model.CAP_DIMS)

    def test_variables_exist(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        assert hasattr(model, 'x')
        assert hasattr(model, 'u')
        assert hasattr(model, 'y')
        assert hasattr(model, 'z')
        assert hasattr(model, 'w')
        assert hasattr(model, 'vehicle_used')

    def test_y_bounds(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        for v in model.V:
            for r in model.R:
                assert model.y[v, r].ub == pyo.value(model.resource_quantity[r])
                assert model.y[v, r].lb == 0

    def test_z_only_valid_combos(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        for (v, r, ct) in model.VALID_Z:
            resource = next(res for res in grasscutting_request.resources if res.id == r)
            vehicle = next(veh for veh in grasscutting_request.vehicles if veh.id == v)
            assert ct in resource.compartment_types
            assert ct in {c.type for c in vehicle.compartments}

    def test_objective_exists(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        assert hasattr(model, 'objective')

    def test_round_trip_default(self, grasscutting_locations, grasscutting_resources, grasscutting_matrices):
        vehicles = [
            Vehicle(id="v1", start_location_id="depot", end_location_id=None,
                    compartments=[Compartment(type="cab", capacity={"seats": 2}),
                                  Compartment(type="bed", capacity={"weight": 500, "volume": 30})]),
        ]
        request = SolveRequest(
            locations=grasscutting_locations, vehicles=vehicles,
            resources=grasscutting_resources, matrices=grasscutting_matrices,
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
        )
        model = build_base_model(request, profile)
        assert pyo.value(model.vehicle_end["v1"]) == "depot"

    def test_metadata_stored(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        assert model._request is grasscutting_request
        assert model._profile is grasscutting_profile
        assert isinstance(model._depots, set)
        assert isinstance(model._visit_locations, set)
        assert isinstance(model._requirement_satisfiers, dict)

    def test_invalid_objective_matrix_raises(self, grasscutting_request):
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"nonexistent_matrix": 1.0},
        )
        from backend.solver.exceptions import ValidationError
        with pytest.raises(ValidationError):
            build_base_model(grasscutting_request, profile)


# Only run solve test if CBC is available
@pytest.fixture
def cbc_available():
    solver = pyo.SolverFactory("cbc")
    if not solver.available():
        pytest.skip("CBC solver not available")
    return solver


class TestBuildBaseModelSolves:
    def test_solves_grasscutting(self, grasscutting_request, grasscutting_profile, cbc_available):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        results = cbc_available.solve(model, tee=False)
        assert results.solver.termination_condition == pyo.TerminationCondition.optimal

        # Every resource assigned to exactly one vehicle (sum of y across vehicles = quantity)
        for r in model.R:
            total = sum(pyo.value(model.y[v, r]) for v in model.V)
            assert total == pyo.value(model.resource_quantity[r])

        # At least one vehicle is used
        total_used = sum(pyo.value(model.vehicle_used[v]) for v in model.V)
        assert total_used >= 1
