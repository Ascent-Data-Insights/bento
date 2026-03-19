class SolverError(Exception):
    """Base class for all solver errors."""
    pass


class ValidationError(SolverError):
    """Raised when input data fails validation."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class DependencyError(SolverError):
    """Raised when module dependencies/conflicts are violated."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Dependency errors: {errors}")


class InfeasibleError(SolverError):
    """Raised when the solver finds the problem infeasible."""
    pass


class SolverTimeoutError(SolverError):
    """Raised when the solver exceeds the time limit."""
    pass


class CustomModuleError(SolverError):
    """Raised when a custom module fails to load or execute."""
    pass
