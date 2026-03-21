import pytest
import pyomo.environ as pyo
from pydantic import ValidationError as PydanticValidationError

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
    ModuleConfig,
    OriginModel,
)
from backend.solver.base_model import build_base_model
from backend.solver.modules.time_windows import TimeWindowsData, TimeWindowEntry, TimeWindowsModule
from backend.solver.orchestrator import Orchestrator


@pytest.fixture
def tw_module():
    return TimeWindowsModule()


class TestTimeWindowsMetadata:
    def test_metadata(self, tw_module):
        meta = tw_module.get_metadata()
        assert meta.key == "time_windows"
        assert meta.name == "Time Windows"
        assert meta.dependencies == []
        assert meta.conflicts == []
        assert meta.required_dimensions == {}


class TestTimeWindowsSchema:
    def test_valid(self):
        data = TimeWindowsData(
            windows=[TimeWindowEntry(location_id="site_a", earliest=480, latest=720)]
        )
        assert len(data.windows) == 1
        assert data.big_m == 1e6

    def test_invalid_missing_fields(self):
        with pytest.raises(PydanticValidationError):
            TimeWindowsData(windows=[{"location_id": "site_a"}])


class TestTimeWindowsValidation:
    def test_unknown_location(self, grasscutting_request, grasscutting_profile, tw_module):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        data = TimeWindowsData(
            windows=[TimeWindowEntry(location_id="nonexistent", earliest=0, latest=100)]
        )
        errors = tw_module.validate(model, data, {})
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_earliest_after_latest(self, grasscutting_request, grasscutting_profile, tw_module):
        model = build_base_model(grasscutting_request, grasscutting_profile)
        data = TimeWindowsData(
            windows=[TimeWindowEntry(location_id="site_a", earliest=720, latest=480)]
        )
        errors = tw_module.validate(model, data, {})
        assert len(errors) == 1
        assert "earliest" in errors[0]


class TestTimeWindowsSolves:
    def test_feasible_wide_windows(self, cbc_available):
        """Wide time windows should not constrain the solution."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
            Location(id="site_b", latitude=40.73, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})])
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "worker"}, stays_with_vehicle=True),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 10, "site_b": 20},
                "site_a": {"depot": 10, "site_a": 0, "site_b": 15},
                "site_b": {"depot": 20, "site_a": 15, "site_b": 0},
            },
            "time": {
                "depot": {"depot": 0, "site_a": 10, "site_b": 20},
                "site_a": {"depot": 10, "site_a": 0, "site_b": 15},
                "site_b": {"depot": 20, "site_a": 15, "site_b": 0},
            },
        }
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=resources, matrices=matrices,
            module_data={
                "time_windows": {
                    "windows": [
                        {"location_id": "site_a", "earliest": 0, "latest": 1440},
                        {"location_id": "site_b", "earliest": 0, "latest": 1440},
                    ]
                }
            },
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="time_windows")],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status.value == "optimal"
        assert len(response.routes) > 0

        # Check arrival times are in module results
        assert "time_windows" in response.module_results
        arrival_times = response.module_results["time_windows"]["arrival_times"]
        assert len(arrival_times) > 0

        # All arrival times should be within the wide windows
        for v_id, stops in arrival_times.items():
            for loc_id, arrival in stops.items():
                if loc_id in ("site_a", "site_b"):
                    assert 0 <= arrival <= 1440

    def test_constraining_windows(self, cbc_available):
        """Tight windows should force visit ordering: site_a early, site_b late."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
            Location(id="site_b", latitude=40.73, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
        ]
        vehicles = [
            Vehicle(id="truck_1", start_location_id="depot", end_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})])
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "worker"}, stays_with_vehicle=True),
        ]
        matrices = {
            "distance": {
                "depot": {"depot": 0, "site_a": 10, "site_b": 20},
                "site_a": {"depot": 10, "site_a": 0, "site_b": 15},
                "site_b": {"depot": 20, "site_a": 15, "site_b": 0},
            },
            "time": {
                "depot": {"depot": 0, "site_a": 10, "site_b": 20},
                "site_a": {"depot": 10, "site_a": 0, "site_b": 15},
                "site_b": {"depot": 20, "site_a": 15, "site_b": 0},
            },
        }
        request = SolveRequest(
            locations=locations, vehicles=vehicles, resources=resources, matrices=matrices,
            module_data={
                "time_windows": {
                    "windows": [
                        {"location_id": "site_a", "earliest": 0, "latest": 100},
                        {"location_id": "site_b", "earliest": 200, "latest": 1440},
                    ]
                }
            },
        )
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="time_windows")],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status.value == "optimal"

        # site_a arrival should be <= 100, site_b arrival should be >= 200
        arrival_times = response.module_results["time_windows"]["arrival_times"]
        for v_id, stops in arrival_times.items():
            if "site_a" in stops:
                assert stops["site_a"] <= 100 + 0.1  # small tolerance
            if "site_b" in stops:
                assert stops["site_b"] >= 200 - 0.1
