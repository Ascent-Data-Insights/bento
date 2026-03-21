"""Base VRP Pyomo model.

Builds the core ConcreteModel used by all routing scenarios. Handles:
- Multi-vehicle routing with subtour elimination (MTZ)
- Resource pickup/dropoff with compartment capacity
- Resource-to-location requirement satisfaction
- Multi-objective weighted cost
"""

from __future__ import annotations

import pyomo.environ as pyo

from backend.schemas.solve import Location, Resource, ResourceRequirement, SolveRequest, Vehicle
from backend.schemas.profile import ClientProfile
from backend.solver.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _derive_depots(vehicles: list[Vehicle]) -> set[str]:
    """Collect all depot location IDs referenced by vehicle start/end."""
    depots: set[str] = set()
    for v in vehicles:
        depots.add(v.start_location_id)
        depots.add(v.end_location_id if v.end_location_id is not None else v.start_location_id)
    return depots


def _resource_matches_requirement(resource: Resource, requirement: ResourceRequirement) -> bool:
    """Return True if resource.attributes is a superset of requirement.attributes."""
    if not requirement.attributes:
        return True
    for key, req_value in requirement.attributes.items():
        if key not in resource.attributes:
            return False
        res_value = resource.attributes[key]
        if isinstance(req_value, list):
            # Every element in the required list must be present in the resource attribute
            if isinstance(res_value, list):
                for elem in req_value:
                    if elem not in res_value:
                        return False
            else:
                # Resource has a scalar; every required element must equal it (only works if list has one item)
                for elem in req_value:
                    if elem != res_value:
                        return False
        else:
            # Scalar requirement: check equality
            if isinstance(res_value, list):
                if req_value not in res_value:
                    return False
            else:
                if res_value != req_value:
                    return False
    return True


def _precompute_requirement_satisfiers(
    locations: list[Location],
    resources: list[Resource],
) -> tuple[dict[tuple[str, int], list[str]], dict[tuple[str, int], list[str]]]:
    """Returns (consumed_satisfiers, swv_satisfiers).

    consumed_satisfiers: resources where stays_with_vehicle=False AND dropoff_location_id==loc.id AND attributes match
    swv_satisfiers: resources where stays_with_vehicle=True AND attributes match (no dropoff filter)
    """
    consumed: dict[tuple[str, int], list[str]] = {}
    swv: dict[tuple[str, int], list[str]] = {}
    for loc in locations:
        if not loc.required_resources:
            continue
        for idx, req in enumerate(loc.required_resources):
            consumed_ids = [
                r.id for r in resources
                if not r.stays_with_vehicle
                and r.dropoff_location_id == loc.id
                and _resource_matches_requirement(r, req)
            ]
            swv_ids = [
                r.id for r in resources
                if r.stays_with_vehicle
                and _resource_matches_requirement(r, req)
            ]
            consumed[(loc.id, idx)] = consumed_ids
            swv[(loc.id, idx)] = swv_ids
    return consumed, swv


def _get_visit_locations(
    locations: list[Location],
    resources: list[Resource],
    depots: set[str],
) -> set[str]:
    """Return location IDs that need visit constraints.

    A location needs visiting if:
      (a) it has non-empty required_resources, OR
      (b) it is a pickup_location_id or dropoff_location_id for any resource.
    """
    visit: set[str] = set()
    for loc in locations:
        if loc.required_resources:
            visit.add(loc.id)
    for r in resources:
        visit.add(r.pickup_location_id)
        if r.dropoff_location_id is not None:
            visit.add(r.dropoff_location_id)
    return visit


# ---------------------------------------------------------------------------
# Main model builder
# ---------------------------------------------------------------------------

def build_base_model(request: SolveRequest, profile: ClientProfile) -> pyo.ConcreteModel:
    """Build and return a Pyomo ConcreteModel for the given solve request and profile."""

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------
    depots = _derive_depots(request.vehicles)

    # Effective end location (None -> start for round-trip)
    vehicle_end_map: dict[str, str] = {}
    for v in request.vehicles:
        vehicle_end_map[v.id] = v.end_location_id if v.end_location_id is not None else v.start_location_id

    consumed_resource_ids = {r.id for r in request.resources if not r.stays_with_vehicle}
    swv_resource_ids = {r.id for r in request.resources if r.stays_with_vehicle}
    visit_locations = _get_visit_locations(request.locations, request.resources, depots)
    consumed_satisfiers, swv_satisfiers = _precompute_requirement_satisfiers(request.locations, request.resources)

    # Lookup dicts
    resource_by_id: dict[str, Resource] = {r.id: r for r in request.resources}
    vehicle_by_id: dict[str, Vehicle] = {v.id: v for v in request.vehicles}
    location_by_id: dict[str, Location] = {loc.id: loc for loc in request.locations}
    location_id_set: set[str] = set(location_by_id.keys())

    # Collect compartment types and capacity dimensions
    ct_set: set[str] = set()
    for v in request.vehicles:
        for comp in v.compartments:
            ct_set.add(comp.type)

    cap_dims_set: set[str] = set()
    for v in request.vehicles:
        for comp in v.compartments:
            cap_dims_set.update(comp.capacity.keys())
    for r in request.resources:
        cap_dims_set.update(r.capacity_consumption.keys())

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    errors: list[str] = []

    # Objective keys (except "vehicles") must be present in matrices
    for key in profile.objective:
        if key != "vehicles" and key not in request.matrices:
            errors.append(f"Objective key '{key}' not found in request.matrices.")

    # Resource pickup/dropoff locations must exist
    for r in request.resources:
        if r.pickup_location_id not in location_id_set:
            errors.append(f"Resource '{r.id}' pickup_location_id '{r.pickup_location_id}' not in locations.")
        if r.dropoff_location_id is not None and r.dropoff_location_id not in location_id_set:
            errors.append(f"Resource '{r.id}' dropoff_location_id '{r.dropoff_location_id}' not in locations.")

    # Vehicle start/end locations must exist
    for v in request.vehicles:
        if v.start_location_id not in location_id_set:
            errors.append(f"Vehicle '{v.id}' start_location_id '{v.start_location_id}' not in locations.")
        effective_end = vehicle_end_map[v.id]
        if effective_end not in location_id_set:
            errors.append(f"Vehicle '{v.id}' end_location_id '{effective_end}' not in locations.")

    if errors:
        raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Build model
    # ------------------------------------------------------------------
    model = pyo.ConcreteModel()

    loc_ids = [loc.id for loc in request.locations]
    arc_set: set[tuple[str, str]] = {(i, j) for i in loc_ids for j in loc_ids if i != j}

    # ------------------------------------------------------------------
    # Sets
    # ------------------------------------------------------------------
    model.N = pyo.Set(initialize=loc_ids)
    model.D = pyo.Set(initialize=list(depots))
    model.V = pyo.Set(initialize=[v.id for v in request.vehicles])
    model.R = pyo.Set(initialize=[r.id for r in request.resources])
    model.A = pyo.Set(initialize=list(arc_set))
    model.CT = pyo.Set(initialize=list(ct_set))
    model.CAP_DIMS = pyo.Set(initialize=list(cap_dims_set))
    model.MATRICES = pyo.Set(initialize=list(request.matrices.keys()))

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def cost_init(model: pyo.ConcreteModel, m: str, i: str, j: str) -> float:
        return request.matrices[m].get(i, {}).get(j, 0.0)

    model.cost = pyo.Param(model.MATRICES, model.N, model.N, initialize=cost_init, default=0.0)
    model.service_time = pyo.Param(
        model.N,
        initialize={loc.id: loc.service_time for loc in request.locations},
        default=0.0,
    )
    model.vehicle_start = pyo.Param(
        model.V,
        initialize={v.id: v.start_location_id for v in request.vehicles},
        within=model.N,
    )
    model.vehicle_end = pyo.Param(
        model.V,
        initialize=vehicle_end_map,
        within=model.N,
    )
    model.resource_pickup = pyo.Param(
        model.R,
        initialize={r.id: r.pickup_location_id for r in request.resources},
        within=model.N,
    )
    model.resource_dropoff = pyo.Param(
        model.R,
        initialize={
            r.id: (r.dropoff_location_id if r.dropoff_location_id is not None else r.pickup_location_id)
            for r in request.resources
        },
        within=model.N,
    )
    model.resource_quantity = pyo.Param(
        model.R,
        initialize={r.id: r.quantity for r in request.resources},
        within=pyo.NonNegativeIntegers,
    )

    def consumption_init(model: pyo.ConcreteModel, r: str, dim: str) -> float:
        return resource_by_id[r].capacity_consumption.get(dim, 0.0)

    model.resource_consumption = pyo.Param(
        model.R, model.CAP_DIMS,
        initialize=consumption_init,
        default=0.0,
    )

    def capacity_init(model: pyo.ConcreteModel, v: str, ct: str, dim: str) -> float:
        vehicle = vehicle_by_id[v]
        total = 0.0
        for comp in vehicle.compartments:
            if comp.type == ct:
                total += comp.capacity.get(dim, 0.0)
        return total

    model.compartment_capacity = pyo.Param(
        model.V, model.CT, model.CAP_DIMS,
        initialize=capacity_init,
        default=0.0,
    )

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    model.x = pyo.Var(model.V, model.A, within=pyo.Binary)
    model.u = pyo.Var(model.V, model.N, within=pyo.NonNegativeReals, bounds=(0, len(request.locations)))
    model.vehicle_used = pyo.Var(model.V, within=pyo.Binary)

    if request.resources:
        def y_bounds(model: pyo.ConcreteModel, v: str, r: str) -> tuple[int, int]:
            return (0, model.resource_quantity[r])

        model.y = pyo.Var(model.V, model.R, within=pyo.NonNegativeIntegers, bounds=y_bounds)
        model.w = pyo.Var(model.V, model.R, within=pyo.Binary)

        # Precompute valid (v, r, ct) combos for z
        valid_z: set[tuple[str, str, str]] = set()
        for v in request.vehicles:
            v_cts = {c.type for c in v.compartments}
            for r in request.resources:
                for ct in r.compartment_types:
                    if ct in v_cts:
                        valid_z.add((v.id, r.id, ct))

        model.VALID_Z = pyo.Set(initialize=list(valid_z))

        def z_bounds(model: pyo.ConcreteModel, v: str, r: str, ct: str) -> tuple[int, int]:
            return (0, resource_by_id[r].quantity)

        model.z = pyo.Var(model.VALID_Z, within=pyo.NonNegativeIntegers, bounds=z_bounds)
    else:
        valid_z = set()

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    # C1: Visit — locations that need visiting
    if visit_locations:
        def visit_rule(model: pyo.ConcreteModel, i: str) -> pyo.Expression:
            return (
                sum(model.x[v, j, i] for v in model.V for j in model.N if (j, i) in arc_set and j != i)
                >= 1
            )
        model.visit_constraint = pyo.Constraint(list(visit_locations), rule=visit_rule)

    # C2: Flow conservation — non-start, non-end nodes per vehicle
    def flow_rule(model: pyo.ConcreteModel, v: str, i: str) -> pyo.Expression | type:
        v_start = pyo.value(model.vehicle_start[v])
        v_end = pyo.value(model.vehicle_end[v])
        if i == v_start or i == v_end:
            return pyo.Constraint.Skip
        inflow = sum(model.x[v, j, i] for j in model.N if (j, i) in arc_set)
        outflow = sum(model.x[v, i, j] for j in model.N if (i, j) in arc_set)
        return inflow == outflow

    model.flow_conservation = pyo.Constraint(model.V, model.N, rule=flow_rule)

    # C3: Depot departure
    def departure_rule(model: pyo.ConcreteModel, v: str) -> pyo.Expression:
        s = pyo.value(model.vehicle_start[v])
        return sum(model.x[v, s, j] for j in model.N if (s, j) in arc_set) <= 1

    model.depot_departure = pyo.Constraint(model.V, rule=departure_rule)

    # C4: Depot return
    def return_rule(model: pyo.ConcreteModel, v: str) -> pyo.Expression:
        e = pyo.value(model.vehicle_end[v])
        return sum(model.x[v, j, e] for j in model.N if (j, e) in arc_set) <= 1

    model.depot_return = pyo.Constraint(model.V, rule=return_rule)

    # C5: Departure equals return
    def depart_return_rule(model: pyo.ConcreteModel, v: str) -> pyo.Expression:
        s = pyo.value(model.vehicle_start[v])
        e = pyo.value(model.vehicle_end[v])
        depart = sum(model.x[v, s, j] for j in model.N if (s, j) in arc_set)
        arrive = sum(model.x[v, j, e] for j in model.N if (j, e) in arc_set)
        return depart == arrive

    model.depart_equals_return = pyo.Constraint(model.V, rule=depart_return_rule)

    # C6: Vehicle used linking
    def vehicle_used_rule(model: pyo.ConcreteModel, v: str) -> pyo.Expression:
        s = pyo.value(model.vehicle_start[v])
        return sum(model.x[v, s, j] for j in model.N if (s, j) in arc_set) == model.vehicle_used[v]

    model.vehicle_used_link = pyo.Constraint(model.V, rule=vehicle_used_rule)

    # C7: MTZ subtour elimination
    def mtz_rule(model: pyo.ConcreteModel, v: str, i: str, j: str) -> pyo.Expression | type:
        if i in depots or j in depots:
            return pyo.Constraint.Skip
        if i == j:
            return pyo.Constraint.Skip
        n = len(request.locations)
        return model.u[v, j] >= model.u[v, i] + 1 - n * (1 - model.x[v, i, j])

    model.mtz_subtour = pyo.Constraint(model.V, model.N, model.N, rule=mtz_rule)

    # Set lower bounds on u for non-depot nodes
    for v in model.V:
        for i in model.N:
            if i not in depots:
                model.u[v, i].setlb(1)

    # Resource-related constraints (only when resources exist)
    if request.resources:

        # C8: Resource assignment completeness
        def resource_assign_rule(model: pyo.ConcreteModel, r: str) -> pyo.Expression:
            return sum(model.y[v, r] for v in model.V) == model.resource_quantity[r]

        model.resource_assignment = pyo.Constraint(model.R, rule=resource_assign_rule)

        # C9: Resource-compartment linking — z sums to y
        def z_link_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression:
            z_sum = sum(model.z[v, r, ct] for ct in model.CT if (v, r, ct) in valid_z)
            return z_sum == model.y[v, r]

        model.z_link = pyo.Constraint(model.V, model.R, rule=z_link_rule)

        # C11: Compartment capacity
        def capacity_rule(model: pyo.ConcreteModel, v: str, ct: str, dim: str) -> pyo.Expression | type:
            if pyo.value(model.compartment_capacity[v, ct, dim]) == 0:
                return pyo.Constraint.Skip
            load = sum(
                model.z[v, r, ct] * model.resource_consumption[r, dim]
                for r in model.R if (v, r, ct) in valid_z
            )
            return load <= model.compartment_capacity[v, ct, dim]

        model.compartment_cap = pyo.Constraint(model.V, model.CT, model.CAP_DIMS, rule=capacity_rule)

        # C12: Resource routing — pickup
        def pickup_route_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression:
            p = pyo.value(model.resource_pickup[r])
            qty = pyo.value(model.resource_quantity[r])
            if p == pyo.value(model.vehicle_start[v]):
                return model.y[v, r] <= qty * model.vehicle_used[v]
            else:
                visits = sum(model.x[v, j, p] for j in model.N if (j, p) in arc_set)
                return model.y[v, r] <= qty * visits

        model.pickup_routing = pyo.Constraint(model.V, model.R, rule=pickup_route_rule)

        # C13: Resource routing — dropoff (skip for stays-with-vehicle resources)
        def dropoff_route_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression | type:
            if r in swv_resource_ids:
                return pyo.Constraint.Skip
            d = pyo.value(model.resource_dropoff[r])
            qty = pyo.value(model.resource_quantity[r])
            if d == pyo.value(model.vehicle_end[v]):
                return model.y[v, r] <= qty * model.vehicle_used[v]
            else:
                visits = sum(model.x[v, j, d] for j in model.N if (j, d) in arc_set)
                return model.y[v, r] <= qty * visits

        model.dropoff_routing = pyo.Constraint(model.V, model.R, rule=dropoff_route_rule)

        # C14: Carries linking — w binary linked to y integer
        def w_lower_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression:
            return model.w[v, r] <= model.y[v, r]

        model.w_lower = pyo.Constraint(model.V, model.R, rule=w_lower_rule)

        def w_upper_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression:
            return model.y[v, r] <= pyo.value(model.resource_quantity[r]) * model.w[v, r]

        model.w_upper = pyo.Constraint(model.V, model.R, rule=w_upper_rule)

        # C15: Pickup before dropoff ordering (skip for stays-with-vehicle resources)
        def pickup_order_rule(model: pyo.ConcreteModel, v: str, r: str) -> pyo.Expression | type:
            if r in swv_resource_ids:
                return pyo.Constraint.Skip
            p = pyo.value(model.resource_pickup[r])
            d = pyo.value(model.resource_dropoff[r])
            if p == d:
                return pyo.Constraint.Skip
            n = len(request.locations)
            return model.u[v, d] >= model.u[v, p] + 1 - n * (1 - model.w[v, r])

        model.pickup_before_dropoff = pyo.Constraint(model.V, model.R, rule=pickup_order_rule)

        # serves_qty variable — quantity of a swv resource available at a location via its vehicle
        serves_set: set[tuple[str, str, str]] = set()
        for (loc_id, req_idx), resource_ids in swv_satisfiers.items():
            for r_id in resource_ids:
                for v in request.vehicles:
                    serves_set.add((v.id, r_id, loc_id))

        if serves_set:
            model.SERVES_SET = pyo.Set(initialize=list(serves_set), dimen=3)

            def serves_qty_bounds(model: pyo.ConcreteModel, v: str, r: str, i: str) -> tuple[float, float]:
                return (0, resource_by_id[r].quantity)

            model.serves_qty = pyo.Var(
                model.SERVES_SET, within=pyo.NonNegativeReals, bounds=serves_qty_bounds
            )

            # C17a: serves_qty <= y (can only serve if vehicle carries the resource)
            def serves_upper_y_rule(model: pyo.ConcreteModel, v: str, r: str, i: str) -> pyo.Expression:
                return model.serves_qty[v, r, i] <= model.y[v, r]

            model.serves_upper_y = pyo.Constraint(model.SERVES_SET, rule=serves_upper_y_rule)

            # C17b: serves_qty <= quantity * (visits to location)
            def serves_upper_visit_rule(
                model: pyo.ConcreteModel, v: str, r: str, i: str
            ) -> pyo.Expression:
                qty = pyo.value(model.resource_quantity[r])
                v_start = pyo.value(model.vehicle_start[v])
                v_end = pyo.value(model.vehicle_end[v])
                if i == v_start or i == v_end:
                    return model.serves_qty[v, r, i] <= qty * model.vehicle_used[v]
                else:
                    visits = sum(model.x[v, j, i] for j in model.N if (j, i) in arc_set)
                    return model.serves_qty[v, r, i] <= qty * visits

            model.serves_upper_visit = pyo.Constraint(model.SERVES_SET, rule=serves_upper_visit_rule)

            # C17c: serves_qty >= y - quantity * (1 - visits) — force non-zero when vehicle visits
            def serves_lower_rule(
                model: pyo.ConcreteModel, v: str, r: str, i: str
            ) -> pyo.Expression:
                qty = pyo.value(model.resource_quantity[r])
                v_start = pyo.value(model.vehicle_start[v])
                v_end = pyo.value(model.vehicle_end[v])
                if i == v_start or i == v_end:
                    visits_expr = model.vehicle_used[v]
                else:
                    visits_expr = sum(model.x[v, j, i] for j in model.N if (j, i) in arc_set)
                return model.serves_qty[v, r, i] >= model.y[v, r] - qty * (1 - visits_expr)

            model.serves_lower = pyo.Constraint(model.SERVES_SET, rule=serves_lower_rule)

        # C16: Resource requirement satisfaction — handles both consumed and swv
        all_req_keys = set(consumed_satisfiers.keys()) | set(swv_satisfiers.keys())

        if all_req_keys:
            def req_satisfy_rule(
                model: pyo.ConcreteModel, loc_id: str, req_idx: int
            ) -> pyo.Expression:
                req_qty = location_by_id[loc_id].required_resources[req_idx].quantity

                # Consumed contribution: sum of delivered quantities
                consumed_ids = consumed_satisfiers.get((loc_id, req_idx), [])
                consumed_contrib = (
                    sum(model.y[v, r] for v in model.V for r in consumed_ids)
                    if consumed_ids else 0
                )

                # SWV contribution: sum of serves_qty (quantity available at location via visiting vehicle)
                swv_ids = swv_satisfiers.get((loc_id, req_idx), [])
                swv_contrib = (
                    sum(
                        model.serves_qty[v, r, loc_id]
                        for v in model.V for r in swv_ids
                        if (v, r, loc_id) in serves_set
                    )
                    if swv_ids else 0
                )

                return consumed_contrib + swv_contrib >= req_qty

            model.REQ_KEYS = pyo.Set(initialize=list(all_req_keys), dimen=2)
            model.requirement_satisfaction = pyo.Constraint(
                model.REQ_KEYS,
                rule=lambda model, loc_id, req_idx: req_satisfy_rule(model, loc_id, req_idx),
            )

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------
    obj_expr = 0
    for key, weight in profile.objective.items():
        if key == "vehicles":
            obj_expr += weight * sum(model.vehicle_used[v] for v in model.V)
        else:
            obj_expr += weight * sum(
                model.cost[key, i, j] * model.x[v, i, j]
                for v in model.V for (i, j) in model.A
            )

    model.objective = pyo.Objective(expr=obj_expr, sense=pyo.minimize)

    # ------------------------------------------------------------------
    # Model metadata for downstream modules
    # ------------------------------------------------------------------
    model._request = request
    model._profile = profile
    model._depots = depots
    model._visit_locations = visit_locations
    model._consumed_satisfiers = consumed_satisfiers
    model._swv_satisfiers = swv_satisfiers
    # Union for backward compatibility — merge lists for keys in both dicts
    all_req_keys = set(consumed_satisfiers.keys()) | set(swv_satisfiers.keys())
    model._requirement_satisfiers = {
        k: consumed_satisfiers.get(k, []) + swv_satisfiers.get(k, [])
        for k in all_req_keys
    }

    return model
