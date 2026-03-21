"""Tests for the matrices endpoint."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.routes import matrices as matrices_module


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the in-memory cache before each test to avoid cross-test contamination."""
    matrices_module._cache.clear()
    yield
    matrices_module._cache.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _make_mock_client(osrm_response: dict):
    """Build a mock httpx.AsyncClient context manager that returns osrm_response."""
    mock_response = MagicMock()
    mock_response.json.return_value = osrm_response
    mock_response.raise_for_status = MagicMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_client_cls


class TestMatricesEndpoint:
    def test_matrices_success(self, client):
        """Mock OSRM and verify matrix computation."""
        mock_osrm_response = {
            "code": "Ok",
            "distances": [[0, 5000], [5000, 0]],
            "durations": [[0, 300], [300, 0]],
        }

        with patch(
            "backend.api.routes.matrices.httpx.AsyncClient",
            _make_mock_client(mock_osrm_response),
        ):
            body = {
                "locations": [
                    {"id": "a", "latitude": 39.1, "longitude": -84.5},
                    {"id": "b", "latitude": 39.2, "longitude": -84.4},
                ]
            }
            response = client.post("/api/v1/matrices", json=body)
            assert response.status_code == 200
            data = response.json()
            assert "distance" in data["matrices"]
            assert "time" in data["matrices"]
            assert data["matrices"]["distance"]["a"]["b"] == 3.1  # 5000m -> 3.1mi
            assert data["matrices"]["time"]["a"]["b"] == 5.0  # 300s -> 5.0min

    def test_matrices_too_few_locations(self, client):
        body = {"locations": [{"id": "a", "latitude": 39.1, "longitude": -84.5}]}
        response = client.post("/api/v1/matrices", json=body)
        assert response.status_code == 422

    def test_matrices_cached(self, client):
        """Second call with same locations should return cached=True."""
        mock_osrm_response = {
            "code": "Ok",
            "distances": [[0, 1000], [1000, 0]],
            "durations": [[0, 60], [60, 0]],
        }

        with patch(
            "backend.api.routes.matrices.httpx.AsyncClient",
            _make_mock_client(mock_osrm_response),
        ):
            body = {
                "locations": [
                    {"id": "x", "latitude": 40.0, "longitude": -83.0},
                    {"id": "y", "latitude": 40.1, "longitude": -83.1},
                ]
            }
            # First call — not cached
            r1 = client.post("/api/v1/matrices", json=body)
            assert r1.status_code == 200
            assert r1.json()["cached"] is False

            # Second call — should be cached (no OSRM call)
            r2 = client.post("/api/v1/matrices", json=body)
            assert r2.status_code == 200
            assert r2.json()["cached"] is True

    def test_matrices_diagonal_is_zero(self, client):
        """Self-to-self distances and times should be zero."""
        mock_osrm_response = {
            "code": "Ok",
            "distances": [[0, 2000], [2000, 0]],
            "durations": [[0, 120], [120, 0]],
        }

        with patch(
            "backend.api.routes.matrices.httpx.AsyncClient",
            _make_mock_client(mock_osrm_response),
        ):
            body = {
                "locations": [
                    {"id": "p", "latitude": 38.0, "longitude": -82.0},
                    {"id": "q", "latitude": 38.1, "longitude": -82.1},
                ]
            }
            response = client.post("/api/v1/matrices", json=body)
            assert response.status_code == 200
            data = response.json()
            assert data["matrices"]["distance"]["p"]["p"] == 0.0
            assert data["matrices"]["time"]["q"]["q"] == 0.0

    def test_matrices_osrm_error_code(self, client):
        """OSRM returning a non-Ok code should yield a 502."""
        mock_osrm_response = {"code": "NoRoute"}

        with patch(
            "backend.api.routes.matrices.httpx.AsyncClient",
            _make_mock_client(mock_osrm_response),
        ):
            body = {
                "locations": [
                    {"id": "m", "latitude": 1.0, "longitude": 1.0},
                    {"id": "n", "latitude": 2.0, "longitude": 2.0},
                ]
            }
            response = client.post("/api/v1/matrices", json=body)
            assert response.status_code == 502
            assert "NoRoute" in response.json()["detail"]

    def test_matrices_null_route(self, client):
        """OSRM returns null for unreachable pairs — should yield 502."""
        mock_osrm = _make_mock_client({
            "code": "Ok",
            "distances": [[0, None], [None, 0]],
            "durations": [[0, None], [None, 0]],
        })
        with patch("backend.api.routes.matrices.httpx.AsyncClient", mock_osrm):
            body = {
                "locations": [
                    {"id": "island", "latitude": 1.0, "longitude": 1.0},
                    {"id": "mainland", "latitude": 2.0, "longitude": 2.0},
                ]
            }
            response = client.post("/api/v1/matrices", json=body)
            assert response.status_code == 502
            assert "no route" in response.json()["detail"].lower()

    def test_matrices_duplicate_ids(self, client):
        """Duplicate location IDs should yield 422."""
        body = {
            "locations": [
                {"id": "same", "latitude": 1.0, "longitude": 1.0},
                {"id": "same", "latitude": 2.0, "longitude": 2.0},
            ]
        }
        response = client.post("/api/v1/matrices", json=body)
        assert response.status_code == 422
        assert "unique" in response.json()["detail"].lower()

    def test_matrices_osrm_http_error(self, client):
        """Network-level OSRM failure should yield a 502."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.api.routes.matrices.httpx.AsyncClient", mock_client_cls):
            body = {
                "locations": [
                    {"id": "u", "latitude": 5.0, "longitude": 5.0},
                    {"id": "v", "latitude": 6.0, "longitude": 6.0},
                ]
            }
            response = client.post("/api/v1/matrices", json=body)
            assert response.status_code == 502
            assert "OSRM request failed" in response.json()["detail"]
