"""Orchestrator — the main solve pipeline."""

from __future__ import annotations

import heapq
from typing import Any

import pyomo.environ as pyo
from pydantic import ValidationError as PydanticValidationError

from backend.config import settings
from backend.schemas.profile import ClientProfile, ModuleConfig
from backend.schemas.solve import SolveRequest, SolveResponse, SolveStatus
from backend.solver.base_model import build_base_model
from backend.solver.exceptions import (
    DependencyError,
    InfeasibleError,
    SolverError,
    SolverTimeoutError,
    ValidationError,
)
from backend.solver.module import ConstraintModule
from backend.solver.modules import REGISTRY
from backend.solver.result_extractor import extract_base_results


class Orchestrator:
    """Composes modules into a solvable model and runs the solve pipeline."""

    def solve(self, request: SolveRequest, profile: ClientProfile) -> SolveResponse:
        """Full pipeline: resolve → validate → build → solve → extract."""

        # Step 1: Resolve modules
        resolved = self._resolve_modules(profile)
        active_keys = {mod.get_metadata().key for mod, _ in resolved}

        # Step 2: Validate dependencies and conflicts
        if resolved:
            self._validate_dependencies(resolved, active_keys, profile)

        # Step 3: Validate data schemas
        parsed_data: dict[str, Any] = {}
        if resolved:
            parsed_data = self._validate_data_schemas(resolved, request)

        # Step 4: Build base model
        model = build_base_model(request, profile)

        # Step 5: Semantic validation
        if resolved:
            self._semantic_validation(resolved, model, parsed_data)

        # Step 6: Apply modules in topological order
        if resolved:
            sorted_modules = self._topological_sort(resolved)
            for module, config in sorted_modules:
                key = module.get_metadata().key
                module.add_to_model(model, parsed_data[key], config.params)

        # Step 7: Solve
        status = self._run_solver(model)

        # Step 8: Extract results
        response = extract_base_results(model, request, status)

        # Step 8b: Module result extraction
        if resolved:
            for module, config in resolved:
                key = module.get_metadata().key
                module_results = module.extract_results(model, parsed_data[key])
                if module_results:
                    response.module_results[key] = module_results

        return response

    def _resolve_modules(
        self, profile: ClientProfile
    ) -> list[tuple[ConstraintModule, ModuleConfig]]:
        """Look up enabled modules in the registry."""
        resolved: list[tuple[ConstraintModule, ModuleConfig]] = []
        for config in profile.modules:
            if not config.enabled:
                continue
            if config.key not in REGISTRY:
                raise ValidationError([f"Module '{config.key}' not found in registry."])
            resolved.append((REGISTRY[config.key], config))
        return resolved

    def _validate_dependencies(
        self,
        resolved: list[tuple[ConstraintModule, ModuleConfig]],
        active_keys: set[str],
        profile: ClientProfile,
    ) -> None:
        """Check module dependencies, conflicts, and required dimensions."""
        errors: list[str] = []
        for module, _ in resolved:
            meta = module.get_metadata()

            # Check dependencies
            for dep in meta.dependencies:
                if dep not in active_keys:
                    errors.append(
                        f"Module '{meta.key}' requires module '{dep}' which is not enabled."
                    )

            # Check conflicts
            for conflict in meta.conflicts:
                if conflict in active_keys:
                    errors.append(
                        f"Module '{meta.key}' conflicts with module '{conflict}' which is also enabled."
                    )

            # Check required dimensions
            for dim_name, valid_values in meta.required_dimensions.items():
                dim_value = getattr(profile.dimensions, dim_name, None)
                if dim_value is None:
                    errors.append(
                        f"Module '{meta.key}' requires dimension '{dim_name}' which does not exist."
                    )
                elif dim_value.value not in valid_values:
                    errors.append(
                        f"Module '{meta.key}' requires {dim_name} to be one of {valid_values}, "
                        f"but got '{dim_value.value}'."
                    )

        if errors:
            raise DependencyError(errors)

    def _validate_data_schemas(
        self,
        resolved: list[tuple[ConstraintModule, ModuleConfig]],
        request: SolveRequest,
    ) -> dict[str, Any]:
        """Validate module data against each module's declared schema."""
        errors: list[str] = []
        parsed: dict[str, Any] = {}

        for module, _ in resolved:
            key = module.get_metadata().key
            schema_cls = module.get_data_schema()
            raw_data = request.module_data.get(key, {})
            try:
                parsed[key] = schema_cls(**raw_data) if isinstance(raw_data, dict) else schema_cls.model_validate(raw_data)
            except PydanticValidationError as e:
                errors.append(f"Module '{key}' data validation failed: {e}")

        if errors:
            raise ValidationError(errors)
        return parsed

    def _semantic_validation(
        self,
        resolved: list[tuple[ConstraintModule, ModuleConfig]],
        model: pyo.ConcreteModel,
        parsed_data: dict[str, Any],
    ) -> None:
        """Run each module's semantic validation."""
        errors: list[str] = []
        for module, config in resolved:
            key = module.get_metadata().key
            module_errors = module.validate(model, parsed_data[key], config.params)
            errors.extend(module_errors)

        if errors:
            raise ValidationError(errors)

    def _topological_sort(
        self, resolved: list[tuple[ConstraintModule, ModuleConfig]]
    ) -> list[tuple[ConstraintModule, ModuleConfig]]:
        """Sort modules by dependencies using Kahn's algorithm.

        Ties are broken by profile order (index in the resolved list).
        """
        if not resolved:
            return []

        # Build index mapping
        key_to_idx: dict[str, int] = {}
        key_to_entry: dict[str, tuple[ConstraintModule, ModuleConfig]] = {}
        for idx, (module, config) in enumerate(resolved):
            key = module.get_metadata().key
            key_to_idx[key] = idx
            key_to_entry[key] = (module, config)

        active_keys = set(key_to_idx.keys())

        # Build in-degree counts and adjacency (only among active modules)
        in_degree: dict[str, int] = {k: 0 for k in active_keys}
        dependents: dict[str, list[str]] = {k: [] for k in active_keys}

        for key in active_keys:
            module = key_to_entry[key][0]
            for dep in module.get_metadata().dependencies:
                if dep in active_keys:
                    in_degree[key] += 1
                    dependents[dep].append(key)

        # Kahn's with heap for tiebreaking by profile order
        # heap entries: (profile_order_index, key)
        heap: list[tuple[int, str]] = []
        for key in active_keys:
            if in_degree[key] == 0:
                heapq.heappush(heap, (key_to_idx[key], key))

        result: list[tuple[ConstraintModule, ModuleConfig]] = []
        while heap:
            _, key = heapq.heappop(heap)
            result.append(key_to_entry[key])
            for dependent in dependents[key]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    heapq.heappush(heap, (key_to_idx[dependent], dependent))

        if len(result) != len(resolved):
            raise SolverError("Circular dependency detected among modules.")

        return result

    def _run_solver(self, model: pyo.ConcreteModel) -> SolveStatus:
        """Run the solver and return the status."""
        solver = pyo.SolverFactory(settings.solver_name)
        if not solver.available():
            raise SolverError(
                f"Solver '{settings.solver_name}' is not available. "
                "Install it (e.g., 'sudo apt install coinor-cbc' for CBC)."
            )
        solver.options["sec"] = settings.solver_time_limit

        result = solver.solve(model, tee=False)
        condition = result.solver.termination_condition

        if condition == pyo.TerminationCondition.optimal:
            return SolveStatus.OPTIMAL
        elif condition == pyo.TerminationCondition.feasible:
            return SolveStatus.FEASIBLE
        elif condition == pyo.TerminationCondition.infeasible:
            raise InfeasibleError("Problem is infeasible.")
        elif condition == pyo.TerminationCondition.maxTimeLimit:
            raise SolverTimeoutError(
                f"Solver exceeded {settings.solver_time_limit}s time limit."
            )
        else:
            raise SolverError(f"Solver terminated with condition: {condition}")
