import pytest
import pyomo.environ as pyo

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
from backend.solver.base_model import build_base_model
from backend.solver.modules.co_delivery import CoDeliveryData, CoDeliveryModule
from backend.solver.orchestrator import Orchestrator


@pytest.fixture
def cd_module():
    return CoDeliveryModule()


class TestCoDeliveryMetadata:
    def test_metadata(self, cd_module):
        meta = cd_module.get_metadata()
        assert meta.key == "co_delivery"
        assert meta.name == "Co-delivery"
        assert meta.dependencies == []
        assert meta.conflicts == []


class TestCoDeliverySchema:
    def test_default_empty(self):
        data = CoDeliveryData()
        assert data.locations == []

    def test_with_locations(self):
        data = CoDeliveryData(locations=["site_a", "site_b"])
        assert len(data.locations) == 2


class TestCoDeliveryValidation:
    def test_unknown_location(self, grasscutting_request, grasscutting_profile, cd_module):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        data = CoDeliveryData(locations=["nonexistent"])
        errors = cd_module.validate(model, data, {})
        assert len(errors) == 1
        assert "nonexistent" in errors[0]


class TestCoDeliveryNoResources:
    def test_no_resources_does_not_crash(self, cbc_available):
        """Co-delivery on a request with no resources should not crash."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})])
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 5},
                "site_a": {"depot": 5, "site_a": 0},
            }
        }
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=[], matrices=matrices,
            module_data={"co_delivery": {}},
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="co_delivery")],
        )
        orchestrator = Orchestrator()
        # Should not crash — just produces a solution with no resource assignments
        response = orchestrator.solve(request, profile)
        assert response.status == SolveStatus.OPTIMAL


class TestCoDeliverySolves:
    def test_same_vehicle(self, cbc_available):
        """Worker and mower for the same site must be on the same vehicle."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[
                         ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                         ResourceRequirement(attributes={"type": "mower"}, quantity=1),
                     ]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ]),
            Vehicle(id="truck_2", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ]),
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True),
            Resource(id="mower_1", pickup_location_id="depot",
                     compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
                     attributes={"type": "mower"}, stays_with_vehicle=True),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 5},
                "site_a": {"depot": 5, "site_a": 0},
            }
        }
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=resources, matrices=matrices,
            module_data={"co_delivery": {}},
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="co_delivery")],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status == SolveStatus.OPTIMAL

        # Both resources should be on the same vehicle
        worker_vehicle = None
        mower_vehicle = None
        for route in response.routes:
            for stop in route.stops:
                if "worker_1" in stop.resources_picked_up:
                    worker_vehicle = route.vehicle_id
                if "mower_1" in stop.resources_picked_up:
                    mower_vehicle = route.vehicle_id
        assert worker_vehicle is not None
        assert mower_vehicle is not None
        assert worker_vehicle == mower_vehicle

    def test_all_locations_default(self, cbc_available):
        """Empty locations list applies co-delivery to all sites with requirements."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[
                         ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                         ResourceRequirement(attributes={"type": "mower"}, quantity=1),
                     ]),
            Location(id="site_b", latitude=40.73, longitude=-74.00, service_time=30,
                     required_resources=[
                         ResourceRequirement(attributes={"skill": "mower_operator"}, quantity=1),
                         ResourceRequirement(attributes={"type": "mower"}, quantity=1),
                     ]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ]),
            Vehicle(id="truck_2", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ]),
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True),
            Resource(id="worker_2", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True),
            Resource(id="mower_1", pickup_location_id="depot",
                     compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
                     attributes={"type": "mower"}, stays_with_vehicle=True),
            Resource(id="mower_2", pickup_location_id="depot",
                     compartment_types=["bed"], capacity_consumption={"weight": 100, "volume": 8},
                     attributes={"type": "mower"}, stays_with_vehicle=True),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 5, "site_b": 8},
                "site_a": {"depot": 5, "site_a": 0, "site_b": 4},
                "site_b": {"depot": 8, "site_a": 4, "site_b": 0},
            }
        }
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=resources, matrices=matrices,
            module_data={"co_delivery": {}},
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="co_delivery")],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status == SolveStatus.OPTIMAL

        # For each vehicle, every worker should be paired with a mower
        for route in response.routes:
            picked_up = set()
            for stop in route.stops:
                picked_up.update(stop.resources_picked_up)
            workers = {r for r in picked_up if r.startswith("worker_")}
            mowers = {r for r in picked_up if r.startswith("mower_")}
            # If the vehicle has any workers, it should also have mowers (and vice versa)
            if workers:
                assert len(mowers) > 0, f"Vehicle {route.vehicle_id} has workers but no mowers"
            if mowers:
                assert len(workers) > 0, f"Vehicle {route.vehicle_id} has mowers but no workers"

    def test_consumed_and_swv_codelivery(self, cbc_available):
        """SWV worker and consumed mulch at the same site must be on the same vehicle."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
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
                    ]),
            Vehicle(id="truck_2", start_location_id="depot", end_location_id="depot",
                    compartments=[
                        Compartment(type="cab", capacity={"seats": 2}),
                        Compartment(type="bed", capacity={"weight": 500, "volume": 30}),
                    ]),
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
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=resources, matrices=matrices,
            module_data={"co_delivery": {}},
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="co_delivery")],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status == SolveStatus.OPTIMAL

        # Both resources should be on the same vehicle
        worker_vehicle = None
        mulch_vehicle = None
        for route in response.routes:
            for stop in route.stops:
                if "worker_1" in stop.resources_picked_up:
                    worker_vehicle = route.vehicle_id
                if "mulch_1" in stop.resources_picked_up:
                    mulch_vehicle = route.vehicle_id
        assert worker_vehicle is not None
        assert mulch_vehicle is not None
        assert worker_vehicle == mulch_vehicle
