# Routing Product — Claude Code Instructions

## Project Overview

Modular vehicle routing optimization SaaS. The base model handles routing with four core concepts: locations, vehicles, compartments, and resources. Clients configure dimensions (structural choices) and enable constraint modules (composable rules). Built on Pyomo for full constraint flexibility.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Optimization**: Pyomo with CBC solver (free default), Gurobi/CPLEX as optional backends
- **Frontend**: React
- **Database**: PostgreSQL, shared multi-tenant with tenant isolation via foreign keys
- **ORM**: SQLAlchemy

## Core Data Model

Four concepts are foundational and handled by the base model:

- **Locations**: Places on the map (depots, job sites, warehouses, charging stations)
- **Vehicles**: Move between locations, contain one or more compartments
- **Compartments**: Spaces within vehicles with capacity dimensions (weight, volume, seats, etc.)
- **Resources**: Things being moved — people AND goods. Each has a pickup location, dropoff location, compatible compartment types (list), capacity consumption, quantity, and optional attributes (skills, certifications, etc.)

People and goods are both resources. A person with a skill is a resource with an attribute. A job site requiring a forklift operator is a location requiring a resource with `skills: [forklift]`. The solver doesn't distinguish people from goods.

## Architecture Principles

- **The base model is powerful.** It handles routing, resource pickup/dropoff, compartment capacity, resource-to-location requirements, and multi-vehicle visits. Modules only add genuinely optional constraints.
- **Dimensions shape the model structure** (origin model, fleet composition). They are NOT modules — they run during model construction and change sets/variables.
- **Objective is a weighted dict** on the profile, not a dimension. Keys are matrix names (e.g., `"distance"`, `"time"`) or `"vehicles"`. The solver builds `sum(weight * sum(matrix))` for each term.
- **Modules add constraints to an already-built model.** They follow the ConstraintModule ABC interface. Built-in modules and custom per-tenant scripts are architecturally identical.
- **Custom constraints are Python scripts** in `backend/solver/custom/`, written by the team (not auto-generated). They follow the same module interface.

## Dimensions (mutually exclusive structural choices)

- **Origin Model**: single_depot, multi_depot, depot_intermediate
- **Fleet Composition**: homogeneous, heterogeneous

Objective is NOT a dimension — it's a weighted dict on the client profile (e.g., `{"distance": 1.0}` or `{"distance": 0.7, "time": 0.3}`).

## Modules (composable constraint toggles)

- **Time Windows**: service/delivery windows per stop
- **EV/Fuel**: battery/fuel range limits, charging/refueling station routing
- **Shift Limits**: max drive time, mandatory breaks
- **Priority/SLA**: priority tiers with penalty weights
- **Co-delivery**: all resources for a location must arrive on the same vehicle

## Demo Scope

Three scenarios to prove flexibility:
1. **Grasscutting**: single depot, mixed people + equipment, co-delivery, time windows, shift limits
2. **Roofing**: depot + intermediate warehouse stops, similar modules to grasscutting
3. **Robotaxi**: multi-depot, EV/fuel, time windows, no operators, passengers as resources

## Tooling

- **Always use `uv`** for Python dependency and environment management. Never use pip or python -m venv directly.

## Code Conventions

- Backend code in `backend/`, frontend in `frontend/`
- Pyomo model-building code in `backend/solver/`
- Each constraint module is a single Python file in `backend/solver/modules/`
- Use Pydantic for API schemas, SQLAlchemy for DB models
- Type hints everywhere in Python code
- Tests mirror source structure in a `tests/` directory
- All module-added Pyomo components must be prefixed with the module key (e.g., `model.time_windows_arrival`)

## Important Patterns

- **Module ABC** in `backend/solver/module.py`: 4 abstract methods (`get_metadata()`, `get_data_schema()`, `validate()`, `add_to_model()`) + 1 optional with default (`extract_results()` returns `{}` by default)
- **Orchestrator pipeline**: resolve modules → validate dependencies/conflicts → validate data schemas → compute matrices → build base model → apply dimensions → semantic validation → apply modules → solve → extract results
- **Profile validation**: All validation is front-loaded before the solver runs.
- **Module ordering**: Topological sort on declared dependencies, profile order as tiebreaker.

## DB Schema

- Dimensions stored as ENUM columns on `client_profiles` table
- Module configs stored as JSONB (flexible, module-defined shapes)
- Shared multi-tenant with `tenant_id` foreign keys

## What NOT to Do

- Don't hardcode industry-specific logic in the core solver or base model. That belongs in modules or client configuration.
- Don't bypass the module interface for "quick" constraint additions.
- Don't use Pyomo's AbstractModel — use ConcreteModel for clarity and debuggability.
- Don't build UI tooling for custom constraint creation — those are hand-written Python by the team.
- Don't treat people and goods as fundamentally different — they're both resources.
