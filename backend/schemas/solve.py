from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceRequirement(BaseModel):
    """Describes a resource requirement at a location.

    A location can require resources with specific attributes and quantities.
    For example, a job site might require 2 resources with skill "mower_operator".
    """
    attributes: dict[str, str | list[str] | bool | int | float] = {}
    quantity: int = 1


class Location(BaseModel):
    """A place on the map — depot, job site, warehouse, charging station, etc."""
    id: str
    latitude: float
    longitude: float
    service_time: float = 0.0
    required_resources: list[ResourceRequirement] = []


class Compartment(BaseModel):
    """A space within a vehicle with capacity limits.

    Examples:
        Pickup truck cab: Compartment(type="cab", capacity={"seats": 3})
        Truck bed: Compartment(type="bed", capacity={"weight": 1000, "volume": 50})
        Refrigerated section: Compartment(type="refrigerated", capacity={"weight": 5000, "volume": 200})
    """
    type: str
    capacity: dict[str, float] = Field(..., min_length=1)


class Vehicle(BaseModel):
    """A vehicle that moves between locations, with one or more compartments."""
    id: str
    start_location_id: str
    end_location_id: str | None = None
    compartments: list[Compartment] = Field(..., min_length=1)


class Resource(BaseModel):
    """Something being moved — a person, equipment, goods.

    People and goods are both resources. A landscaper is a resource with skills.
    A bag of mulch is a resource with weight. The solver doesn't distinguish between them.

    Examples:
        Landscaper: Resource(id="worker_1", pickup_location_id="depot", dropoff_location_id="site_a",
                             compartment_types=["cab"], capacity_consumption={"seats": 1},
                             attributes={"skill": "mower_operator"})
        Mower: Resource(id="mower_1", pickup_location_id="depot", dropoff_location_id="site_a",
                        compartment_types=["bed", "trunk"], capacity_consumption={"weight": 150, "volume": 10},
                        attributes={"type": "mower"})
    """
    id: str
    pickup_location_id: str
    dropoff_location_id: str
    compartment_types: list[str] = Field(..., min_length=1)
    capacity_consumption: dict[str, float]
    quantity: int = 1
    attributes: dict[str, str | list[str] | bool | int | float] = {}


class SolveRequest(BaseModel):
    """Input to the solver: locations, vehicles, resources, and optional module data."""
    locations: list[Location] = Field(..., min_length=1)
    vehicles: list[Vehicle] = Field(..., min_length=1)
    resources: list[Resource]
    matrices: dict[str, dict[str, dict[str, float]]] = Field(..., min_length=1)
    module_data: dict[str, Any] = {}


class RouteStop(BaseModel):
    """A single stop along a vehicle's route."""
    location_id: str
    arrival_time: float | None = None
    departure_time: float | None = None
    resources_picked_up: list[str] = []
    resources_dropped_off: list[str] = []


class Route(BaseModel):
    """A vehicle's complete route: ordered stops with resource movements."""
    vehicle_id: str
    stops: list[RouteStop]
    total_distance: float
    total_time: float | None = None


class SolveStatus(str, Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    ERROR = "error"


class SolveResponse(BaseModel):
    """Output from the solver."""
    status: SolveStatus
    objective_value: float | None = None
    routes: list[Route] = []
    unserved_locations: list[str] = []
    unserved_resources: list[str] = []
    module_results: dict[str, Any] = {}
