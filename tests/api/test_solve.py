"""Tests for the solve API endpoint."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.solve import SolveStatus
from backend.solver.exceptions import InfeasibleError


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSolveEndpoint:
    def _make_solve_body(self, **overrides):
        body = {
            "request": {
                "locations": [
                    {"id": "depot", "latitude": 40.7128, "longitude": -74.006},
                    {
                        "id": "site_a",
                        "latitude": 40.7228,
                        "longitude": -74.000,
                        "service_time": 60,
                        "required_resources": [
                            {"attributes": {"skill": "mower_operator"}, "quantity": 1}
                        ],
                    },
                ],
                "vehicles": [
                    {
                        "id": "truck_1",
                        "start_location_id": "depot",
                        "end_location_id": "depot",
                        "compartments": [{"type": "cab", "capacity": {"seats": 2}}],
                    }
                ],
                "resources": [
                    {
                        "id": "worker_1",
                        "pickup_location_id": "depot",
                        "compartment_types": ["cab"],
                        "capacity_consumption": {"seats": 1},
                        "attributes": {"skill": "mower_operator"},
                        "stays_with_vehicle": True,
                    }
                ],
                "matrices": {
                    "distance": {
                        "depot": {"depot": 0, "site_a": 5},
                        "site_a": {"depot": 5, "site_a": 0},
                    }
                },
            },
            "profile": {
                "tenant_id": "test",
                "name": "Test",
                "dimensions": {
                    "origin_model": "single_depot",
                    "fleet_composition": "heterogeneous",
                },
                "objective": {"distance": 1.0},
                "modules": [],
            },
        }
        body.update(overrides)
        return body

    def test_solve_success(self, client):
        """CBC must be installed for this test."""
        import pyomo.environ as pyo
        solver = pyo.SolverFactory("cbc")
        if not solver.available():
            pytest.skip("CBC solver not available")

        body = self._make_solve_body()
        response = client.post("/api/v1/solve", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "optimal"
        assert data["objective_value"] is not None
        assert len(data["routes"]) > 0

    def test_solve_with_time_windows(self, client):
        """Solve with time windows module enabled."""
        import pyomo.environ as pyo
        solver = pyo.SolverFactory("cbc")
        if not solver.available():
            pytest.skip("CBC solver not available")

        body = self._make_solve_body()
        body["request"]["matrices"]["time"] = body["request"]["matrices"]["distance"].copy()
        body["request"]["module_data"] = {
            "time_windows": {
                "windows": [
                    {"location_id": "site_a", "earliest": 0, "latest": 200}
                ]
            }
        }
        body["profile"]["modules"] = [{"key": "time_windows"}]
        response = client.post("/api/v1/solve", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "optimal"
        assert "time_windows" in data["module_results"]

    def test_solve_invalid_request(self, client):
        """Missing required fields should return 422."""
        response = client.post("/api/v1/solve", json={"request": {}, "profile": {}})
        assert response.status_code == 422

    def test_solve_unknown_module(self, client):
        """Unknown module should return 422."""
        body = self._make_solve_body()
        body["profile"]["modules"] = [{"key": "nonexistent_module"}]
        response = client.post("/api/v1/solve", json=body)
        assert response.status_code == 422

    def test_solve_infeasible(self, client):
        """Infeasible problem should return 400."""
        body = self._make_solve_body()
        with patch("backend.api.routes.solve.Orchestrator") as mock_orch:
            mock_orch.return_value.solve.side_effect = InfeasibleError("Problem is infeasible.")
            response = client.post("/api/v1/solve", json=body)
            assert response.status_code == 400
            assert "infeasible" in response.json()["detail"]["message"].lower()

    def test_solve_invalid_objective_key(self, client):
        """Objective referencing non-existent matrix should return 422."""
        body = self._make_solve_body()
        body["profile"]["objective"] = {"nonexistent": 1.0}
        response = client.post("/api/v1/solve", json=body)
        assert response.status_code == 422
