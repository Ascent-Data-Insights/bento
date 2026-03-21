from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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

    Resources are either:
    - stays_with_vehicle=True: ride with the vehicle all day (workers, mowers). dropoff_location_id
      may be omitted entirely — they return to depot when the vehicle does.
    - stays_with_vehicle=False (default): consumed — picked up and dropped off at specific locations
      (mulch, passengers). dropoff_location_id is required.

    Examples:
        Worker (stays with vehicle):
            Resource(id="worker_1", pickup_location_id="depot",
                     compartment_types=["cab"], capacity_consumption={"seats": 1},
                     attributes={"skill": "mower_operator"}, stays_with_vehicle=True)
        Mulch (consumed):
            Resource(id="mulch_1", pickup_location_id="depot", dropoff_location_id="site_a",
                     compartment_types=["bed"], capacity_consumption={"weight": 50, "volume": 3},
                     quantity=10)
        Robotaxi passenger (consumed):
            Resource(id="passenger_1", pickup_location_id="stop_a", dropoff_location_id="stop_b",
                     compartment_types=["cabin"], capacity_consumption={"seats": 1})
    """
    id: str
    pickup_location_id: str
    dropoff_location_id: str | None = None
    compartment_types: list[str] = Field(..., min_length=1)
    capacity_consumption: dict[str, float]
    quantity: int = 1
    attributes: dict[str, str | list[str] | bool | int | float] = {}
    stays_with_vehicle: bool = False

    @model_validator(mode="after")
    def dropoff_required_for_consumed(self) -> "Resource":
        if not self.stays_with_vehicle and self.dropoff_location_id is None:
            raise ValueError(
                f"Resource '{self.id}': dropoff_location_id is required when stays_with_vehicle=False. "
                "Set stays_with_vehicle=True for resources that ride with the vehicle all day (workers, equipment), "
                "or provide a dropoff_location_id for consumed resources (mulch, passengers)."
            )
        return self


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
