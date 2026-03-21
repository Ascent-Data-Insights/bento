import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel


class EmptySchema(BaseModel):
    """Empty schema for test modules that don't need data."""
    pass

from backend.schemas.solve import (
    Compartment,
    Location,
    Resource,
    ResourceRequirement,
    SolveRequest,
    SolveResponse,
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
from backend.solver.exceptions import DependencyError, SolverError, ValidationError
from backend.solver.module import ConstraintModule, ModuleMetadata


class TestOrchestratorSolves:
    """Tests that require CBC solver."""

    def test_end_to_end_no_modules(self, grasscutting_request, grasscutting_profile, cbc_available):
        orchestrator = Orchestrator()
        response = orchestrator.solve(grasscutting_request, grasscutting_profile)
        assert response.status == SolveStatus.OPTIMAL
        assert response.objective_value is not None
        assert len(response.routes) > 0

    def test_routes_have_stops(self, grasscutting_request, grasscutting_profile, cbc_available):
        orchestrator = Orchestrator()
        response = orchestrator.solve(grasscutting_request, grasscutting_profile)
        # Every route has at least 2 stops (depart + return)
        for route in response.routes:
            assert len(route.stops) >= 2
        # All 3 job sites appear across routes
        all_stops = set()
        for route in response.routes:
            for stop in route.stops:
                all_stops.add(stop.location_id)
        assert "site_a" in all_stops
        assert "site_b" in all_stops
        assert "site_c" in all_stops

    def test_resource_movements_in_routes(self, grasscutting_request, grasscutting_profile, cbc_available):
        orchestrator = Orchestrator()
        response = orchestrator.solve(grasscutting_request, grasscutting_profile)

        # Collect all pickups and dropoffs across routes
        all_pickups: dict[str, list[str]] = {}  # resource_id -> [location_ids]
        all_dropoffs: dict[str, list[str]] = {}
        for route in response.routes:
            for stop in route.stops:
                for r_id in stop.resources_picked_up:
                    all_pickups.setdefault(r_id, []).append(stop.location_id)
                for r_id in stop.resources_dropped_off:
                    all_dropoffs.setdefault(r_id, []).append(stop.location_id)

        # SWV resources (workers, mowers) should be picked up at depot, never dropped off
        for swv_id in ["worker_1", "worker_2", "worker_3", "mower_1", "mower_2"]:
            if swv_id in all_pickups:
                assert all_pickups[swv_id] == ["depot"]
            assert swv_id not in all_dropoffs

        # Consumed resource (mulch) should be picked up at depot and dropped at site_a
        if "mulch_site_a" in all_pickups:
            assert all_pickups["mulch_site_a"] == ["depot"]
        if "mulch_site_a" in all_dropoffs:
            assert all_dropoffs["mulch_site_a"] == ["site_a"]

    def test_empty_modules_works(self, grasscutting_request, cbc_available):
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[],
        )
        orchestrator = Orchestrator()
        response = orchestrator.solve(grasscutting_request, profile)
        assert response.status == SolveStatus.OPTIMAL

    def test_unused_vehicles_no_routes(self, cbc_available):
        """3 vehicles but only 1 small job — unused vehicles should not appear in routes."""
        locations = [
            Location(id="depot", latitude=40.71, longitude=-74.00),
            Location(id="site_a", latitude=40.72, longitude=-74.00, service_time=30,
                     required_resources=[ResourceRequirement(attributes={"skill": "worker"}, quantity=1)]),
        ]
        vehicles = [
            Vehicle(id=f"truck_{i}", start_location_id="depot", end_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})])
            for i in range(3)
        ]
        resources = [
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "worker"}, stays_with_vehicle=True),
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
        orchestrator = Orchestrator()
        response = orchestrator.solve(request, profile)
        assert response.status == SolveStatus.OPTIMAL
        # Only 1 vehicle should have a route
        assert len(response.routes) == 1


class TestOrchestratorValidation:
    """Tests that do NOT require CBC solver."""

    def test_unknown_module_raises(self, grasscutting_request):
        profile = ClientProfile(
            tenant_id="test", name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="nonexistent_module")],
        )
        orchestrator = Orchestrator()
        with pytest.raises(SolverError, match="not found in registry"):
            orchestrator.solve(grasscutting_request, profile)

    def test_module_dependency_error(self, grasscutting_request):
        """A module that depends on a non-active module should raise DependencyError."""

        class FakeModule(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(
                    key="fake_module",
                    name="Fake",
                    description="Test module",
                    dependencies=["nonexistent_dependency"],
                )
            def get_data_schema(self):
                return EmptySchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        fake_instance = FakeModule()
        with patch.dict("backend.solver.modules.REGISTRY", {"fake_module": fake_instance}):
            profile = ClientProfile(
                tenant_id="test", name="Test",
                dimensions=DimensionSelections(
                    origin_model=OriginModel.SINGLE_DEPOT,
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={"distance": 1.0},
                modules=[ModuleConfig(key="fake_module")],
            )
            orchestrator = Orchestrator()
            with pytest.raises(DependencyError):
                orchestrator.solve(grasscutting_request, profile)

    def test_circular_dependency_raises(self, grasscutting_request):
        """Two modules that depend on each other should raise SolverError."""

        class ModuleA(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(key="mod_a", name="A", description="A", dependencies=["mod_b"])
            def get_data_schema(self):
                return EmptySchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        class ModuleB(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(key="mod_b", name="B", description="B", dependencies=["mod_a"])
            def get_data_schema(self):
                return EmptySchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        with patch.dict("backend.solver.modules.REGISTRY", {"mod_a": ModuleA(), "mod_b": ModuleB()}):
            profile = ClientProfile(
                tenant_id="test", name="Test",
                dimensions=DimensionSelections(
                    origin_model=OriginModel.SINGLE_DEPOT,
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={"distance": 1.0},
                modules=[ModuleConfig(key="mod_a"), ModuleConfig(key="mod_b")],
            )
            orchestrator = Orchestrator()
            with pytest.raises(SolverError, match="Circular dependency"):
                orchestrator.solve(grasscutting_request, profile)

    def test_module_conflict_raises(self, grasscutting_request):
        """Two modules that conflict should raise DependencyError."""

        class ConflictingModule(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(key="mod_x", name="X", description="X", conflicts=["mod_y"])
            def get_data_schema(self):
                return EmptySchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        class OtherModule(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(key="mod_y", name="Y", description="Y")
            def get_data_schema(self):
                return EmptySchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        with patch.dict("backend.solver.modules.REGISTRY", {"mod_x": ConflictingModule(), "mod_y": OtherModule()}):
            profile = ClientProfile(
                tenant_id="test", name="Test",
                dimensions=DimensionSelections(
                    origin_model=OriginModel.SINGLE_DEPOT,
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={"distance": 1.0},
                modules=[ModuleConfig(key="mod_x"), ModuleConfig(key="mod_y")],
            )
            orchestrator = Orchestrator()
            with pytest.raises(DependencyError):
                orchestrator.solve(grasscutting_request, profile)

    def test_module_schema_validation_error(self, grasscutting_request):
        """A module whose data schema requires a field not provided should raise ValidationError."""

        class StrictSchema(BaseModel):
            required_field: str

        class StrictModule(ConstraintModule):
            def get_metadata(self):
                return ModuleMetadata(key="strict_mod", name="Strict", description="Strict")
            def get_data_schema(self):
                return StrictSchema
            def validate(self, model, data, config):
                return []
            def add_to_model(self, model, data, config):
                pass
            def extract_results(self, model, data):
                return {}

        with patch.dict("backend.solver.modules.REGISTRY", {"strict_mod": StrictModule()}):
            profile = ClientProfile(
                tenant_id="test", name="Test",
                dimensions=DimensionSelections(
                    origin_model=OriginModel.SINGLE_DEPOT,
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={"distance": 1.0},
                modules=[ModuleConfig(key="strict_mod")],
            )
            orchestrator = Orchestrator()
            with pytest.raises(ValidationError):
                orchestrator.solve(grasscutting_request, profile)
