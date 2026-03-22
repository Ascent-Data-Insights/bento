from backend.solver.module import ConstraintModule

REGISTRY: dict[str, ConstraintModule] = {}


def register(cls: type[ConstraintModule]) -> type[ConstraintModule]:
    """Decorator to register a built-in module."""
    instance = cls()
    REGISTRY[instance.get_metadata().key] = instance
    return cls


# Import modules to trigger @register
from backend.solver.modules import time_windows  # noqa: F401
from backend.solver.modules import co_delivery  # noqa: F401
from backend.solver.modules import ev_fuel  # noqa: F401
from backend.solver.modules import shift_limits  # noqa: F401
from backend.solver.modules import priority_sla  # noqa: F401
