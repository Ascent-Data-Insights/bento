"""Extract routes from a solved Pyomo model."""

from __future__ import annotations

import pyomo.environ as pyo

from backend.schemas.solve import (
    Route,
    RouteStop,
    SolveRequest,
    SolveResponse,
    SolveStatus,
)


def extract_base_results(
    model: pyo.ConcreteModel, request: SolveRequest, status: SolveStatus
) -> SolveResponse:
    """Read the solved model and build a SolveResponse with routes."""

    objective_value = pyo.value(model.objective)

    # Build lookup for resource stays_with_vehicle
    resource_swv = {r.id: r.stays_with_vehicle for r in request.resources}
    resource_pickup = {r.id: r.pickup_location_id for r in request.resources}
    resource_dropoff = {r.id: r.dropoff_location_id for r in request.resources}

    # Determine primary matrix key for distance calculation
    matrix_keys = list(request.matrices.keys())
    primary_matrix_key = "distance" if "distance" in request.matrices else (matrix_keys[0] if matrix_keys else None)
    time_matrix_key = "time" if "time" in request.matrices else None

    routes: list[Route] = []
    all_visited_locations: set[str] = set()

    for v in model.V:
        v_start = pyo.value(model.vehicle_start[v])
        v_end = pyo.value(model.vehicle_end[v])

        # Find active arcs for this vehicle
        next_node: dict[str, str] = {}
        for (i, j) in model.A:
            if pyo.value(model.x[v, i, j]) > 0.5:
                next_node[i] = j

        # Skip unused vehicles
        if not next_node:
            continue

        # Walk the route: start -> ... -> end
        # Handle round-trip (start == end) by using a flag
        stops_order: list[str] = [v_start]
        current = v_start
        visited_in_walk: set[str] = {v_start}

        while current in next_node:
            next_loc = next_node[current]
            stops_order.append(next_loc)
            # For round-trip: stop when we return to end depot
            # but only after traversing at least one arc
            if next_loc == v_end and len(stops_order) > 2:
                break
            if next_loc in visited_in_walk and next_loc != v_end:
                break  # safety: prevent infinite loops
            visited_in_walk.add(next_loc)
            current = next_loc

        # Build route stops with resource movements
        # Determine which resources this vehicle carries
        carried_resources: set[str] = set()
        if hasattr(model, 'y'):
            for r in model.R:
                if round(pyo.value(model.y[v, r])) > 0:
                    carried_resources.add(r)

        route_stops: list[RouteStop] = []
        already_picked_up: set[str] = set()
        already_dropped_off: set[str] = set()
        for loc_id in stops_order:
            picked_up: list[str] = []
            dropped_off: list[str] = []

            for r_id in carried_resources:
                # Picked up at this location (only the first time we visit the pickup location)
                if resource_pickup.get(r_id) == loc_id and r_id not in already_picked_up:
                    picked_up.append(r_id)
                    already_picked_up.add(r_id)
                # Dropped off at this location (consumed resources only, first visit)
                if (not resource_swv.get(r_id, False)
                        and resource_dropoff.get(r_id) == loc_id
                        and r_id not in already_dropped_off):
                    dropped_off.append(r_id)
                    already_dropped_off.add(r_id)

            route_stops.append(RouteStop(
                location_id=loc_id,
                resources_picked_up=sorted(picked_up),
                resources_dropped_off=sorted(dropped_off),
            ))
            all_visited_locations.add(loc_id)

        # Compute total distance
        total_distance = 0.0
        if primary_matrix_key:
            for i in range(len(stops_order) - 1):
                loc_from = stops_order[i]
                loc_to = stops_order[i + 1]
                total_distance += pyo.value(model.cost[primary_matrix_key, loc_from, loc_to])

        # Compute total time if time matrix exists
        total_time = None
        if time_matrix_key:
            total_time = 0.0
            for i in range(len(stops_order) - 1):
                loc_from = stops_order[i]
                loc_to = stops_order[i + 1]
                total_time += pyo.value(model.cost[time_matrix_key, loc_from, loc_to])

        routes.append(Route(
            vehicle_id=v,
            stops=route_stops,
            total_distance=total_distance,
            total_time=total_time,
        ))

    # Unserved locations
    visit_locations = getattr(model, '_visit_locations', set())
    unserved_locations = sorted(visit_locations - all_visited_locations)

    # Unserved resources (defensive — shouldn't happen with equality constraint)
    unserved_resources: list[str] = []
    if hasattr(model, 'y'):
        for r in model.R:
            total_assigned = sum(round(pyo.value(model.y[v, r])) for v in model.V)
            qty = pyo.value(model.resource_quantity[r])
            if total_assigned < qty:
                unserved_resources.append(r)

    return SolveResponse(
        status=status,
        objective_value=objective_value,
        routes=routes,
        unserved_locations=unserved_locations,
        unserved_resources=sorted(unserved_resources),
    )
