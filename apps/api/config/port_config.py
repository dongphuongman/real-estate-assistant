"""
Port configuration loader for backend.

Loads port settings from environment variables, .env.ports file, or PORT_REGISTRY.json.
Priority: PORT env var > .env.ports > registry > default
"""

import json
import os
from pathlib import Path


def _find_project_root() -> Path:
    """Find project root by looking for docs/PORT_REGISTRY.json."""
    current = Path(__file__).resolve()

    # Walk up the directory tree
    for parent in current.parents:
        if (parent / "docs" / "PORT_REGISTRY.json").exists():
            return parent
        if (parent / "apps" / "api").exists() and (parent / "apps" / "web").exists():
            return parent

    # Fallback: assume we're in apps/api/config/
    return Path(__file__).resolve().parents[3]


def _load_env_ports(project_root: Path) -> dict[str, str]:
    """Load .env.ports file into a dict."""
    env_ports_path = project_root / ".env.ports"
    if not env_ports_path.exists():
        return {}

    result = {}
    for line in env_ports_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()

    return result


def _load_registry_ports(project_root: Path) -> dict[str, int]:
    """Load ports from PORT_REGISTRY.json."""
    registry_path = project_root / "docs" / "PORT_REGISTRY.json"
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, encoding="utf-8") as f:
            registry = json.load(f)

        result = {}
        for alloc in registry.get("allocations", []):
            if alloc.get("status") == "active":
                category = alloc.get("category")
                port = alloc.get("port")
                if category and port:
                    result[category] = port

        return result
    except (json.JSONDecodeError, IOError):
        return {}


def get_backend_port() -> int:
    """
    Get backend port from environment or registry.

    Priority:
    1. PORT environment variable
    2. BACKEND_PORT from .env.ports
    3. Backend allocation from PORT_REGISTRY.json
    4. Default: 8000
    """
    # 1. Check PORT env var
    port = os.getenv("PORT")
    if port:
        try:
            return int(port)
        except ValueError:
            pass

    # 2. Check .env.ports
    project_root = _find_project_root()
    env_ports = _load_env_ports(project_root)

    if "BACKEND_PORT" in env_ports:
        try:
            return int(env_ports["BACKEND_PORT"])
        except ValueError:
            pass

    # 3. Check registry
    registry_ports = _load_registry_ports(project_root)
    if "backend" in registry_ports:
        return registry_ports["backend"]

    # 4. Default
    return 8000


def get_frontend_url() -> str:
    """
    Get frontend URL for CORS configuration.

    Priority:
    1. FRONTEND_URL environment variable
    2. FRONTEND_URL from .env.ports
    3. Constructed from FRONTEND_PORT in .env.ports
    4. Constructed from frontend allocation in registry
    5. Default: http://localhost:3000
    """
    # 1. Check FRONTEND_URL env var
    url = os.getenv("FRONTEND_URL")
    if url:
        return url

    # 2-3. Check .env.ports
    project_root = _find_project_root()
    env_ports = _load_env_ports(project_root)

    if "FRONTEND_URL" in env_ports:
        return env_ports["FRONTEND_URL"]

    if "FRONTEND_PORT" in env_ports:
        try:
            port = int(env_ports["FRONTEND_PORT"])
            return f"http://localhost:{port}"
        except ValueError:
            pass

    # 4. Check registry
    registry_ports = _load_registry_ports(project_root)
    if "frontend" in registry_ports:
        return f"http://localhost:{registry_ports['frontend']}"

    # 5. Default
    return "http://localhost:3000"


def get_cors_origins() -> list[str]:
    """
    Get CORS allowed origins.

    Priority:
    1. CORS_ALLOW_ORIGINS environment variable
    2. CORS_ALLOW_ORIGINS from .env.ports
    3. Frontend URL
    4. Default: ["*"] for development
    """
    # 1. Check CORS_ALLOW_ORIGINS env var
    cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    if cors_origins:
        return [o.strip() for o in cors_origins.split(",") if o.strip()]

    # 2. Check .env.ports
    project_root = _find_project_root()
    env_ports = _load_env_ports(project_root)

    if "CORS_ALLOW_ORIGINS" in env_ports:
        origins = env_ports["CORS_ALLOW_ORIGINS"]
        return [o.strip() for o in origins.split(",") if o.strip()]

    # 3. Use frontend URL
    frontend_url = get_frontend_url()
    if frontend_url != "http://localhost:3000":
        return [frontend_url]

    # 4. Default for development
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        # In production, this should be explicitly set
        return []
    return ["*"]


def get_all_port_config() -> dict[str, int | str]:
    """
    Get all port configuration as a dict.

    Returns:
        Dict with backend_port, frontend_url, and cors_origins
    """
    return {
        "backend_port": get_backend_port(),
        "frontend_url": get_frontend_url(),
        "cors_origins": get_cors_origins(),
    }


# Convenience function for settings.py
def get_frontend_url_for_settings() -> str:
    """
    Get frontend URL for use in Pydantic settings.

    This function is designed to be used as a default_factory.
    """
    return get_frontend_url()
