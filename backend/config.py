from pathlib import Path

from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost:5432/routing"
    solver_name: str = "cbc"
    solver_time_limit: int = 300
    custom_modules_dir: Path = _BACKEND_DIR / "solver" / "custom"
    log_level: str = "INFO"
    osrm_base_url: str = "https://router.project-osrm.org"
    cors_origins: str = "*"

    model_config = {"env_prefix": "ROUTING_"}


settings = Settings()
