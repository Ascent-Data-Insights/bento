from backend.solver.module import ConstraintModule

REGISTRY: dict[str, ConstraintModule] = {}


def register(cls: type[ConstraintModule]) -> type[ConstraintModule]:
    """Decorator to register a built-in module."""
    instance = cls()
    REGISTRY[instance.get_metadata().key] = instance
    return cls
