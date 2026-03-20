import pytest
from pydantic import ValidationError

from backend.schemas.solve import (
    Compartment,
    Location,
    Resource,
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


class TestCompartment:
    def test_valid(self):
        c = Compartment(type="cab", capacity={"seats": 3})
        assert c.type == "cab"
        assert c.capacity == {"seats": 3}

    def test_empty_capacity_rejected(self):
        with pytest.raises(ValidationError):
            Compartment(type="cab", capacity={})


class TestVehicle:
    def test_valid(self):
        v = Vehicle(
            id="truck_1",
            start_location_id="depot",
            compartments=[Compartment(type="cab", capacity={"seats": 3})],
        )
        assert v.id == "truck_1"
        assert v.end_location_id is None

    def test_empty_compartments_rejected(self):
        with pytest.raises(ValidationError):
            Vehicle(id="truck_1", start_location_id="depot", compartments=[])


class TestResource:
    def test_valid_person(self):
        r = Resource(
            id="worker_1",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["cab"],
            capacity_consumption={"seats": 1},
            attributes={"skill": "mower_operator"},
        )
        assert r.attributes == {"skill": "mower_operator"}

    def test_valid_equipment(self):
        r = Resource(
            id="mower_1",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["bed"],
            capacity_consumption={"weight": 150, "volume": 10},
        )
        assert r.attributes == {}

    def test_attributes_list_values(self):
        r = Resource(
            id="worker_1",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["cab"],
            capacity_consumption={"seats": 1},
            attributes={"skills": ["mower", "hedger"], "certified": True},
        )
        assert r.attributes["skills"] == ["mower", "hedger"]

    def test_multiple_compartment_types(self):
        r = Resource(
            id="mower_1",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["bed", "trailer"],
            capacity_consumption={"weight": 150, "volume": 10},
        )
        assert r.compartment_types == ["bed", "trailer"]

    def test_empty_compartment_types_rejected(self):
        with pytest.raises(ValidationError):
            Resource(
                id="bad",
                pickup_location_id="depot",
                dropoff_location_id="site_a",
                compartment_types=[],
                capacity_consumption={"seats": 1},
            )

    def test_quantity_default(self):
        r = Resource(
            id="worker_1",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["cab"],
            capacity_consumption={"seats": 1},
        )
        assert r.quantity == 1

    def test_quantity_batch(self):
        r = Resource(
            id="mulch_for_site_a",
            pickup_location_id="depot",
            dropoff_location_id="site_a",
            compartment_types=["bed"],
            capacity_consumption={"weight": 50, "volume": 2},
            quantity=10,
        )
        assert r.quantity == 10


class TestSolveRequest:
    def _make_request(self, **overrides):
        defaults = dict(
            locations=[Location(id="depot", latitude=40.7128, longitude=-74.0060)],
            vehicles=[
                Vehicle(
                    id="truck_1",
                    start_location_id="depot",
                    compartments=[Compartment(type="cab", capacity={"seats": 2})],
                )
            ],
            resources=[],
            matrices={"distance": {"depot": {"depot": 0.0}}},
        )
        defaults.update(overrides)
        return SolveRequest(**defaults)

    def test_valid(self):
        req = self._make_request()
        assert len(req.locations) == 1

    def test_empty_locations_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(locations=[])

    def test_empty_vehicles_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(vehicles=[])

    def test_named_matrices(self):
        req = self._make_request(
            matrices={
                "distance": {"depot": {"depot": 0}},
                "time": {"depot": {"depot": 0}},
            }
        )
        assert "distance" in req.matrices
        assert "time" in req.matrices

    def test_empty_matrices_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(matrices={})


class TestSolveResponse:
    def test_status_enum(self):
        resp = SolveResponse(status=SolveStatus.OPTIMAL, objective_value=42.0)
        assert resp.status == SolveStatus.OPTIMAL

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            SolveResponse(status="not_a_status")

    def test_unserved_resources_field(self):
        resp = SolveResponse(status=SolveStatus.FEASIBLE, unserved_resources=["r1"])
        assert resp.unserved_resources == ["r1"]


class TestClientProfile:
    def test_valid(self):
        profile = ClientProfile(
            tenant_id="t1",
            name="Test Landscaper",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HETEROGENEOUS,
            ),
            objective={"distance": 1.0},
            modules=[ModuleConfig(key="time_windows")],
        )
        assert profile.dimensions.origin_model == OriginModel.SINGLE_DEPOT
        assert profile.objective == {"distance": 1.0}
        assert len(profile.modules) == 1

    def test_multi_objective(self):
        profile = ClientProfile(
            tenant_id="t1",
            name="Test",
            dimensions=DimensionSelections(
                origin_model=OriginModel.SINGLE_DEPOT,
                fleet_composition=FleetComposition.HOMOGENEOUS,
            ),
            objective={"distance": 0.7, "time": 0.3},
        )
        assert profile.objective == {"distance": 0.7, "time": 0.3}

    def test_empty_objective_rejected(self):
        with pytest.raises(ValidationError):
            ClientProfile(
                tenant_id="t1",
                name="Bad",
                dimensions=DimensionSelections(
                    origin_model=OriginModel.SINGLE_DEPOT,
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={},
            )

    def test_invalid_dimension_rejected(self):
        with pytest.raises(ValidationError):
            ClientProfile(
                tenant_id="t1",
                name="Bad",
                dimensions=DimensionSelections(
                    origin_model="invalid",
                    fleet_composition=FleetComposition.HETEROGENEOUS,
                ),
                objective={"distance": 1.0},
            )
