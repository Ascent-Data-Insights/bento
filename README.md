# Routing Product Demo

A modular vehicle routing optimization platform. Compose industry-specific routing solutions from reusable optimization modules rather than building bespoke solvers per client.

## The Problem

Vehicle routing optimization (VRP) is needed across many industries — landscaping, grocery delivery, robotaxis, roofing, field service, and more. These industries share 80%+ of the same core routing logic, but each has unique constraints. Today, solutions are either industry-specific (rigid) or general-purpose (complex to configure).

## The Approach

The platform has a powerful base model built on four core concepts — **locations**, **vehicles**, **compartments**, and **resources** — that handles the fundamental routing problem. On top of that, clients configure **dimensions** (mutually exclusive structural choices) and enable **constraint modules** (composable, toggleable rules). Custom constraints can be added per-tenant as Python scripts that follow the same interface as built-in modules.

Under the hood, every module adds variables and constraints to a [Pyomo](http://www.pyomo.org/) optimization model. This means modules, custom constraints, and the core solver all speak the same language — there's no abstraction gap between "standard" and "custom."

## Core Concepts

The base model is built on four concepts that apply to every routing problem:

### Locations
Places on the map — depots, job sites, warehouses, charging stations, customer addresses.

### Vehicles
Things that move between locations. Each vehicle has one or more compartments.

### Compartments
Spaces within a vehicle, each with capacity dimensions. A pickup truck has a cab (seats=3) and a bed (weight=1000lbs, volume=50cuft). A robotaxi has a cabin (seats=4). A refrigerated truck has a cold section and an ambient section. Compartments are how the model understands what a vehicle can carry.

### Resources
Things being moved. A resource is anything that gets picked up at one location and either dropped off at a specific location or rides along for the whole route, consuming compartment capacity. People and goods are both resources:

| Resource | Compartment Type | Consumes | Attributes | Stays with vehicle? |
|---|---|---|---|---|
| Landscaper (mower operator) | Cab | 1 seat | `skills: [mower_operator]` | Yes |
| Lawn mower | Bed or Trailer | weight, volume | `type: mower` | Yes |
| 10 bags of mulch | Bed | weight, volume (quantity=10) | — | No (consumed) |
| Robotaxi passenger | Cabin | 1 seat | — | No (consumed) |
| Pallet of frozen pizzas | Refrigerated | weight, volume | — | No (consumed) |

Resources are either **stays-with-vehicle** (`stays_with_vehicle=True`) or **consumed** (the default). A stays-with-vehicle resource — like a worker or a mower — rides along for the entire route and is present at every location the vehicle visits. A consumed resource — like mulch or a passenger — has a specific dropoff location and is removed from the vehicle at that stop.

The solver doesn't distinguish between people and goods — they're all resources with attributes, pickup/dropoff locations, and capacity consumption. A job site that needs a forklift-certified worker just requires a resource with `skills: [forklift]`. Resources can list multiple compatible compartment types (e.g., a mower fits in a bed or a trailer) and can have a quantity for batch items (e.g., 10 bags of mulch).

## What the Base Model Handles

- Route vehicles through locations, minimizing the objective
- Pick up and drop off resources along each route
- Match resources to compatible compartment types (resources list which compartment types they fit in)
- Enforce compartment capacity limits at every point in the route
- Satisfy location resource requirements (skills, equipment, quantities)
- Allow multiple vehicles to serve the same location when needed
- Support for stays-with-vehicle resources (workers, equipment) that ride along for the entire route
- Subtour elimination (MTZ formulation)

### Known Limitations

- **No mid-route depot reloading.** Each vehicle visits the depot once at the start and once at the end. If a vehicle can't carry enough for all its stops in one trip, the solver assigns multiple vehicles rather than having one vehicle return to reload. Mid-route reloading (depot→A→depot→B→depot) is a future enhancement.
- **MTZ subtour elimination scales poorly** past ~50-100 locations. Fine for the demo; production would need lazy constraint generation.
- **Compartment capacity is additive.** Checked as a linear sum, not geometric bin packing. For real-world packing concerns, set conservative capacity values or add a custom module.

## Dimensions

Structural choices that shape the problem. Each client selects one option per dimension:

| Dimension | Options |
|---|---|
| **Origin Model** | Single depot · Multi-depot · Depot + intermediate stops |
| **Fleet Composition** | Homogeneous · Heterogeneous (capabilities vary by vehicle) |

The **objective** is not a dimension — it's a weighted dict on the client profile. Keys reference named cost matrices (e.g., `"distance"`, `"time"`, `"fuel"`) or the special term `"vehicles"`. Examples: `{"distance": 1.0}` to minimize distance, `{"distance": 0.7, "time": 0.3}` for a multi-objective blend, `{"vehicles": 100, "distance": 1.0}` to minimize fleet size with distance as tiebreaker.

Cost matrices are provided per solve request. Clients can supply any named matrices (distance, time, fuel cost, etc.). Matrices must be provided in every solve request — there is no auto-computation fallback.

## Constraint Modules

Optional rules toggled on/off per client, each with its own configuration:

| Module | What It Adds | Example |
|---|---|---|
| **Time Windows** | Service/delivery window per stop | Customer wants lawn cut between 8am-12pm |
| **EV/Fuel** | Range limits, refueling/charging stops | Robotaxi must route through charging stations |
| **Shift Limits** | Max drive time, mandatory breaks | Crews work 8-hour days with a lunch break |
| **Priority/SLA** | Priority tiers with penalty weights | Emergency jobs served before routine maintenance |
| **Co-delivery** | All resources for a location arrive on the same vehicle | Landscaper and their mower must be on the same truck |

## Custom Constraints

Per-tenant Python scripts written by the team (not auto-generated via UI). These follow the same module interface as built-in modules. When a custom constraint proves reusable across clients, it gets promoted to a standard module.

## Demo Scenarios

Three demos proving the model's flexibility across radically different industries:

### 1. Grasscutting (Landscaping)
- **Origin Model**: Single depot (HQ where crew and equipment are stored)
- **Fleet**: Heterogeneous (trucks with trailers, trucks without, cars for quotes)
- **Objective**: `{"distance": 1.0}`
- **Modules**: Time Windows, Shift Limits, Co-delivery
- **Key features exercised**: Mixed people + equipment as resources, varying job sizes (1 mower + 1 operator vs. 2 mowers + 1 hedger + 3 operators), quote-only visits (just a person in a car, no equipment)

### 2. Roofing
- **Origin Model**: Depot + intermediate stops (leave HQ, pick up materials at warehouse, then to job sites)
- **Fleet**: Heterogeneous
- **Objective**: `{"distance": 1.0}`
- **Modules**: Time Windows, Shift Limits, Co-delivery
- **Key features exercised**: Intermediate warehouse stops, heavy materials requiring specific vehicle capacity

### 3. Robotaxi
- **Origin Model**: Multi-depot (taxis spread across the city)
- **Fleet**: Heterogeneous (different battery levels/vehicle sizes)
- **Objective**: `{"time": 1.0}`
- **Modules**: Time Windows, EV/Fuel
- **Key features exercised**: No operators (vehicle is autonomous), passengers as resources with unique pickup/dropoff pairs, no return-to-depot requirement, charging station routing

## Tech Stack

| Layer | Technology |
|---|---|
| **Optimization Engine** | Pyomo (with CBC solver, Gurobi/CPLEX optional) |
| **Backend API** | FastAPI (Python) |
| **Frontend** | React |
| **Database** | PostgreSQL (shared multi-tenant) |

## System Dependencies

- **CBC solver**: Required for optimization. Install via `sudo apt install coinor-cbc` (Ubuntu/Debian). Not a Python package — it's a system binary that Pyomo calls. For production, include in a Dockerfile.

## Running

### Local Development

```bash
uv run uvicorn backend.main:app --reload
```

### Docker

```bash
docker compose up --build
```

### Endpoints

- **Health check**: `GET http://localhost:8000/health`
- **Solve**: `POST http://localhost:8000/api/v1/solve`

### Example Solve Request

```bash
curl -X POST http://localhost:8000/api/v1/solve \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "locations": [
        {"id": "depot", "latitude": 40.7128, "longitude": -74.006},
        {"id": "site_a", "latitude": 40.7228, "longitude": -74.000, "service_time": 60,
         "required_resources": [{"attributes": {"skill": "mower_operator"}, "quantity": 1}]}
      ],
      "vehicles": [
        {"id": "truck_1", "start_location_id": "depot", "end_location_id": "depot",
         "compartments": [{"type": "cab", "capacity": {"seats": 2}}]}
      ],
      "resources": [
        {"id": "worker_1", "pickup_location_id": "depot",
         "compartment_types": ["cab"], "capacity_consumption": {"seats": 1},
         "attributes": {"skill": "mower_operator"}, "stays_with_vehicle": true}
      ],
      "matrices": {
        "distance": {
          "depot": {"depot": 0, "site_a": 5},
          "site_a": {"depot": 5, "site_a": 0}
        }
      }
    },
    "profile": {
      "tenant_id": "demo",
      "name": "Demo Landscaper",
      "dimensions": {
        "origin_model": "single_depot",
        "fleet_composition": "heterogeneous"
      },
      "objective": {"distance": 1.0},
      "modules": []
    }
  }'
```

## Project Structure

```
routing/
├── backend/
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # App settings
│   ├── api/
│   │   └── routes/            # solve.py, profiles.py
│   ├── solver/
│   │   ├── module.py          # ConstraintModule ABC + ModuleMetadata
│   │   ├── orchestrator.py    # Composes modules into a solvable model
│   │   ├── base_model.py      # Core Pyomo model (locations, vehicles, compartments, resources)
│   │   ├── result_extractor.py
│   │   ├── exceptions.py
│   │   ├── dimensions/        # origin_model.py, fleet_composition.py
│   │   ├── modules/           # time_windows.py, ev_fuel.py, shift_limits.py, etc.
│   │   └── custom/            # Per-tenant custom constraint scripts
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── session.py
│   └── schemas/               # Pydantic: solve.py, profile.py, module_data.py
├── tests/
│   └── solver/
├── frontend/
│   └── src/
└── README.md
```

## Key Concepts

- **Unified Resource Model**: People and goods are both resources with attributes. A job site's requirements are expressed as "deliver resources with these attributes here." The solver doesn't know or care what's a person vs. what's a bag of mulch.
- **Module Interface**: Every module (built-in or custom) implements the same ABC: metadata, data schema, validation, add constraints, extract results.
- **Dependency & Conflict Declaration**: Modules declare what they require and what they conflict with. The orchestrator validates profiles before solving.
- **Solver Backend Flexibility**: Pyomo separates model definition from solving. Start with CBC (free). Swap in Gurobi or CPLEX for performance without changing model code.
