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
        consumed, swv = _precompute_requirement_satisfiers(grasscutting_locations, grasscutting_resources)
        # site_a req 0: skill=mower_operator -> swv workers (all 3 match attributes, no dropoff filter)
        assert set(swv[("site_a", 0)]) == {"worker_1", "worker_2", "worker_3"}
        # site_a req 1: type=mower -> swv mowers
        assert set(swv[("site_a", 1)]) == {"mower_1", "mower_2"}
        # site_c req 0: skill=mower_operator -> swv workers
        assert set(swv[("site_c", 0)]) == {"worker_1", "worker_2", "worker_3"}
        # No consumed satisfiers for mower_operator requirements (workers are swv)
        assert consumed.get(("site_a", 0), []) == []


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
        assert len(list(model.R)) == 6
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
        assert hasattr(model, 'serves_qty')

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

    def test_serves_qty_exists(self, grasscutting_request, grasscutting_profile):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        assert hasattr(model, 'serves_qty')
        assert hasattr(model, 'SERVES_SET')
        # Check that serves_set contains entries for swv resources at required locations
        serves_entries = list(model.SERVES_SET)
        assert len(serves_entries) > 0
        # All entries should be (vehicle_id, swv_resource_id, location_id) tuples
        for v, r, i in serves_entries:
            assert v in {"truck_1", "truck_2"}
            assert r in {"worker_1", "worker_2", "worker_3", "mower_1", "mower_2"}
            assert i in {"site_a", "site_b", "site_c"}


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

    def test_swv_worker_visits_multiple_sites(self, cbc_available):
        """A single swv worker must visit 2 sites — verifies the worker stays on the vehicle."""
        from backend.schemas.solve import ResourceRequirement
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00, service_time=0),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1)]),
            Location(id="site_b", latitude=40.73, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1)]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})])
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 5, "site_b": 8},
                "site_a": {"depot": 5, "site_a": 0, "site_b": 4},
                "site_b": {"depot": 8, "site_a": 4, "site_b": 0},
            }
        }
        request = SolveRequest(locations=locations, vehicles=vehicles, resources=resources, matrices=matrices)
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(origin_model=OriginModel.SINGLE_DEPOT, fleet_composition=FleetComposition.HETEROGENEOUS),
            objective={"distance": 1.0},
        )
        model = build_base_model(request, profile)
        results = cbc_available.solve(model, tee=False)
        assert results.solver.termination_condition == pyo.TerminationCondition.optimal

        # Worker is on truck_1
        assert pyo.value(model.y["truck_1", "worker_1"]) == 1

        # Truck visits both sites
        visited = set()
        for (i, j) in model.A:
            if pyo.value(model.x["truck_1", i, j]) > 0.5:
                visited.add(j)
        assert "site_a" in visited
        assert "site_b" in visited

    def test_mixed_consumed_and_swv(self, cbc_available):
        """SWV worker + consumed mulch delivered to the same site."""
        from backend.schemas.solve import ResourceRequirement
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00, service_time=0),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[
                         ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                     ]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ])
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True),
            Resource(id="mulch_1", pickup_location_id="depot", dropoff_location_id="site_a",
                     compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 5}),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 5},
                "site_a": {"depot": 5, "site_a": 0},
            }
        }
        request = SolveRequest(locations=locations, vehicles=vehicles, resources=resources, matrices=matrices)
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(origin_model=OriginModel.SINGLE_DEPOT, fleet_composition=FleetComposition.HETEROGENEOUS),
            objective={"distance": 1.0},
        )
        model = build_base_model(request, profile)
        results = cbc_available.solve(model, tee=False)
        assert results.solver.termination_condition == pyo.TerminationCondition.optimal

        # Worker rides with truck, mulch delivered
        assert pyo.value(model.y["truck_1", "worker_1"]) == 1
        assert pyo.value(model.y["truck_1", "mulch_1"]) == 1
