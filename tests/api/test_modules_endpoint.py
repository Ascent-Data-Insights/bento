"""Tests for GET /api/v1/modules and POST /api/v1/tenants/onboard endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestModulesEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/v1/modules")
        assert response.status_code == 200

    def test_returns_list(self, client):
        response = client.get("/api/v1/modules")
        data = response.json()
        assert isinstance(data, list)

    def test_contains_all_five_modules(self, client):
        response = client.get("/api/v1/modules")
        keys = {m["key"] for m in response.json()}
        assert {"time_windows", "co_delivery", "ev_fuel", "shift_limits", "priority_sla"}.issubset(keys)

    def test_each_entry_has_required_fields(self, client):
        response = client.get("/api/v1/modules")
        for entry in response.json():
            assert "key" in entry
            assert "name" in entry
            assert "description" in entry
            assert "dependencies" in entry
            assert "conflicts" in entry
            assert "required_dimensions" in entry
            assert "implemented" in entry

    def test_stub_modules_implemented_false(self, client):
        response = client.get("/api/v1/modules")
        by_key = {m["key"]: m for m in response.json()}
        assert by_key["ev_fuel"]["implemented"] is False
        assert by_key["shift_limits"]["implemented"] is False
        assert by_key["priority_sla"]["implemented"] is False

    def test_real_modules_implemented_true(self, client):
        response = client.get("/api/v1/modules")
        by_key = {m["key"]: m for m in response.json()}
        assert by_key["time_windows"]["implemented"] is True
        assert by_key["co_delivery"]["implemented"] is True


class TestOnboardEndpoint:
    def _make_body(self, **overrides):
        body = {
            "tenant_name": "Acme Landscaping",
            "industry": "landscaping",
            "profile_name": "Default",
            "dimensions": {
                "origin_model": "single_depot",
                "fleet_composition": "heterogeneous",
            },
            "objective": {"distance": 1.0},
            "modules": [],
        }
        body.update(overrides)
        return body

    def test_missing_tenant_name_returns_422(self, client):
        body = self._make_body()
        del body["tenant_name"]
        response = client.post("/api/v1/tenants/onboard", json=body)
        assert response.status_code == 422

    def test_missing_objective_returns_422(self, client):
        body = self._make_body()
        del body["objective"]
        response = client.post("/api/v1/tenants/onboard", json=body)
        assert response.status_code == 422

    def test_invalid_origin_model_returns_422(self, client):
        body = self._make_body()
        body["dimensions"]["origin_model"] = "bad_value"
        response = client.post("/api/v1/tenants/onboard", json=body)
        assert response.status_code == 422

    def test_invalid_fleet_composition_returns_422(self, client):
        body = self._make_body()
        body["dimensions"]["fleet_composition"] = "invalid"
        response = client.post("/api/v1/tenants/onboard", json=body)
        assert response.status_code == 422
