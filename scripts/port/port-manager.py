#!/usr/bin/env python3
"""
Port Manager - Dynamic port allocation for AI Real Estate Assistant.

Features:
- Auto-detect available ports in configured ranges
- Check both registry AND actual system usage
- Cross-platform support (Windows, macOS, Linux)
- Service discovery integration
- Parent NestSolo registry integration

Usage:
    python port-manager.py --action allocate --category backend
    python port-manager.py --action release --port 8000
    python port-manager.py --action status
    python port-manager.py --action kill --port 8000 --force
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class PortManager:
    """Manages port allocation with cross-platform support."""

    PORT_RANGES = {
        "frontend": (3800, 3899),
        "backend": (8000, 8099),
    }

    DEFAULT_PORTS = {
        "frontend": 3800,
        "backend": 8000,
    }

    SERVICE_NAMES = {
        "frontend": "ai-real-estate-assistant-web",
        "backend": "ai-real-estate-assistant",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.registry_path = project_root / "docs" / "PORT_REGISTRY.json"
        self.parent_registry_path = (
            project_root / ".." / ".." / ".." / "docs" / "PORT_REGISTRY.json"
        )
        self._registry: Optional[dict] = None

    @property
    def registry(self) -> dict:
        """Load registry lazily."""
        if self._registry is None:
            self._registry = self._load_or_create_registry()
        return self._registry

    def _load_or_create_registry(self) -> dict:
        """Load existing registry or create new one."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "version": "1.0.0",
            "project": "ai-real-estate-assistant",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "ranges": {
                "frontend": {
                    "start": 3800,
                    "end": 3899,
                    "description": "Next.js frontend",
                },
                "backend": {
                    "start": 8000,
                    "end": 8099,
                    "description": "FastAPI backend",
                },
            },
            "defaults": self.DEFAULT_PORTS.copy(),
            "sharedServices": [],
            "allocations": [],
        }

    def _save_registry(self) -> None:
        """Save registry to disk."""
        self.registry["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2)

    def _get_parent_registry_ports(self, category: str) -> set[int]:
        """Get ports used in parent NestSolo registry."""
        used: set[int] = set()
        if self.parent_registry_path.exists():
            try:
                with open(self.parent_registry_path, "r", encoding="utf-8") as f:
                    parent = json.load(f)
                for alloc in parent.get("allocations", []):
                    if (
                        alloc.get("category") == category
                        and alloc.get("status") == "active"
                    ):
                        port = alloc.get("port")
                        if port:
                            used.add(port)
            except (json.JSONDecodeError, IOError):
                pass
        return used

    def _get_registry_ports(self, category: str) -> set[int]:
        """Get ports already allocated in local registry."""
        used: set[int] = set()
        for alloc in self.registry.get("allocations", []):
            if alloc.get("category") == category and alloc.get("status") == "active":
                port = alloc.get("port")
                if port:
                    used.add(port)
        return used

    def _is_port_in_use_system(self, port: int) -> bool:
        """Check if port is in use at system level (cross-platform)."""
        # Method 1: Socket binding test (fastest, works on all platforms)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    return True
        except socket.error:
            pass

        # Method 2: Platform-specific checks (more reliable)
        system = platform.system().lower()

        if system == "windows":
            return self._check_port_windows(port)
        else:  # macOS, Linux
            return self._check_port_unix(port)

    def _check_port_windows(self, port: int) -> bool:
        """Check port on Windows using netstat."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTENING" in line:
                    return True
        except (subprocess.SubprocessError, OSError):
            pass
        return False

    def _check_port_unix(self, port: int) -> bool:
        """Check port on Unix/macOS using lsof or netstat."""
        # Try lsof first (more reliable)
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                return True
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            pass

        # Fallback to netstat
        try:
            result = subprocess.run(
                ["netstat", "-tuln"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTEN" in line:
                    return True
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            pass

        return False

    def find_available_port(
        self, category: str, preferred: Optional[int] = None
    ) -> int:
        """Find an available port in the specified category range."""
        if category not in self.PORT_RANGES:
            raise ValueError(
                f"Unknown category: {category}. Valid: {list(self.PORT_RANGES.keys())}"
            )

        start, end = self.PORT_RANGES[category]

        # Collect all used ports
        used_ports: set[int] = set()
        used_ports.update(self._get_registry_ports(category))
        used_ports.update(self._get_parent_registry_ports(category))

        # Try preferred port first
        if preferred and start <= preferred <= end:
            if preferred not in used_ports and not self._is_port_in_use_system(
                preferred
            ):
                return preferred

        # Try default port
        default = self.DEFAULT_PORTS.get(category)
        if (
            default
            and default not in used_ports
            and not self._is_port_in_use_system(default)
        ):
            return default

        # Scan range for available port
        for port in range(start, end + 1):
            if port not in used_ports and not self._is_port_in_use_system(port):
                return port

        raise RuntimeError(f"No available ports in {category} range ({start}-{end})")

    def allocate_port(
        self,
        category: str,
        service_name: Optional[str] = None,
        preferred: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> int:
        """Allocate a port and register it."""
        port = self.find_available_port(category, preferred)

        if not service_name:
            service_name = self.SERVICE_NAMES.get(category, f"service-{category}")

        allocation = {
            "id": str(uuid.uuid4()),
            "serviceName": service_name,
            "category": category,
            "port": port,
            "status": "active",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastUsedAt": datetime.now(timezone.utc).isoformat(),
            "pid": pid,
            "metadata": {"env": os.getenv("ENVIRONMENT", "development")},
        }

        # Remove existing allocation for same service
        self.registry["allocations"] = [
            a
            for a in self.registry.get("allocations", [])
            if a.get("serviceName") != service_name
        ]

        self.registry["allocations"].append(allocation)
        self._save_registry()

        return port

    def release_port(self, port: int) -> bool:
        """Mark a port allocation as inactive."""
        for alloc in self.registry.get("allocations", []):
            if alloc.get("port") == port:
                alloc["status"] = "inactive"
                alloc["lastUsedAt"] = datetime.now(timezone.utc).isoformat()
                self._save_registry()
                return True
        return False

    def get_allocation(self, service_name: str) -> Optional[dict]:
        """Get allocation for a specific service."""
        for alloc in self.registry.get("allocations", []):
            if (
                alloc.get("serviceName") == service_name
                and alloc.get("status") == "active"
            ):
                return alloc
        return None

    def get_port_for_category(self, category: str) -> Optional[int]:
        """Get active port for a category."""
        for alloc in self.registry.get("allocations", []):
            if alloc.get("category") == category and alloc.get("status") == "active":
                return alloc.get("port")
        return None

    def get_all_allocated_ports(self) -> dict[str, int]:
        """Get all active port allocations as a dict."""
        result: dict[str, int] = {}
        for alloc in self.registry.get("allocations", []):
            if alloc.get("status") == "active":
                cat = alloc.get("category")
                port = alloc.get("port")
                if cat and port:
                    result[cat] = port
        return result

    def kill_process_on_port(self, port: int, force: bool = False) -> bool:
        """Kill process using the specified port (cross-platform)."""
        system = platform.system().lower()

        if system == "windows":
            return self._kill_port_windows(port, force)
        else:
            return self._kill_port_unix(port, force)

    def _kill_port_windows(self, port: int, force: bool) -> bool:
        """Kill process on Windows using netstat and taskkill."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )

            pids: set[int] = set()
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.add(int(parts[-1]))
                        except ValueError:
                            pass

            if not pids:
                return False

            # Kill processes
            for pid in pids:
                cmd = ["taskkill", "/F" if force else "", "/PID", str(pid)]
                cmd = [c for c in cmd if c]  # Remove empty strings
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0,
                )

            self.release_port(port)
            return True

        except subprocess.SubprocessError:
            return False

    def _kill_port_unix(self, port: int, force: bool) -> bool:
        """Kill process on Unix/macOS using lsof."""
        try:
            result = subprocess.run(
                ["lsof", "-t", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]

            if not pids:
                return False

            # Kill processes
            signal = "KILL" if force else "TERM"
            for pid in pids:
                subprocess.run(
                    ["kill", f"-{signal}", str(pid)],
                    capture_output=True,
                    timeout=10,
                )

            self.release_port(port)
            return True

        except subprocess.SubprocessError:
            return False

    def get_status(self) -> dict:
        """Get current status of all allocations."""
        return {
            "registry": str(self.registry_path),
            "lastUpdated": self.registry.get("lastUpdated"),
            "ranges": self.registry.get("ranges"),
            "defaults": self.registry.get("defaults"),
            "allocations": self.registry.get("allocations", []),
            "activePorts": self.get_all_allocated_ports(),
        }

    def generate_env_ports_content(self, backend_port: int, frontend_port: int) -> str:
        """Generate .env.ports file content."""
        return f"""# Auto-generated port configuration
# Generated by port-manager.py
# DO NOT EDIT MANUALLY - changes will be overwritten

# Backend Configuration
BACKEND_PORT={backend_port}
BACKEND_URL=http://localhost:{backend_port}
BACKEND_API_URL=http://localhost:{backend_port}/api/v1

# Frontend Configuration
FRONTEND_PORT={frontend_port}
FRONTEND_URL=http://localhost:{frontend_port}

# CORS Configuration (for backend)
CORS_ALLOW_ORIGINS=http://localhost:{frontend_port}

# Next.js Environment Variables
NEXT_PUBLIC_API_URL=/api/v1
PORT={frontend_port}
"""


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Port Manager - Dynamic port allocation for AI Real Estate Assistant"
    )
    parser.add_argument(
        "--action",
        "-a",
        choices=["allocate", "release", "status", "kill", "find", "generate-env"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--category",
        "-c",
        choices=["frontend", "backend"],
        help="Port category (for allocate/find)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port number (for release/kill)",
    )
    parser.add_argument(
        "--preferred",
        type=int,
        help="Preferred port (for allocate)",
    )
    parser.add_argument(
        "--service-name",
        "-s",
        help="Service name (for allocate)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force kill (for kill action)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: auto-detect)",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args(argv)

    # Determine project root
    if args.project_root:
        project_root = args.project_root
    else:
        # Auto-detect from script location
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent

    pm = PortManager(project_root)

    try:
        if args.action == "allocate":
            if not args.category:
                print(
                    "Error: --category is required for allocate action", file=sys.stderr
                )
                return 1
            port = pm.allocate_port(
                category=args.category,
                service_name=args.service_name,
                preferred=args.preferred,
            )
            if args.json:
                print(json.dumps({"port": port, "category": args.category}))
            else:
                print(f"Allocated port {port} for {args.category}")

        elif args.action == "find":
            if not args.category:
                print("Error: --category is required for find action", file=sys.stderr)
                return 1
            port = pm.find_available_port(args.category, args.preferred)
            if args.json:
                print(json.dumps({"port": port, "category": args.category}))
            else:
                print(f"Found available port {port} for {args.category}")

        elif args.action == "release":
            if not args.port:
                print("Error: --port is required for release action", file=sys.stderr)
                return 1
            if pm.release_port(args.port):
                if args.json:
                    print(json.dumps({"released": args.port}))
                else:
                    print(f"Released port {args.port}")
            else:
                print(f"Port {args.port} not found in allocations", file=sys.stderr)
                return 1

        elif args.action == "kill":
            if not args.port:
                print("Error: --port is required for kill action", file=sys.stderr)
                return 1
            if pm.kill_process_on_port(args.port, args.force):
                if args.json:
                    print(json.dumps({"killed": args.port}))
                else:
                    print(f"Killed process on port {args.port}")
            else:
                print(f"No process found on port {args.port}", file=sys.stderr)
                return 1

        elif args.action == "status":
            status = pm.get_status()
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                print("Port Registry Status")
                print("=" * 40)
                print(f"Registry: {status['registry']}")
                print(f"Last Updated: {status['lastUpdated']}")
                print()
                print("Ranges:")
                for cat, info in status["ranges"].items():
                    print(f"  {cat}: {info['start']}-{info['end']}")
                print()
                print("Active Allocations:")
                for alloc in status["allocations"]:
                    if alloc["status"] == "active":
                        print(
                            f"  {alloc['serviceName']}: {alloc['category']} port {alloc['port']}"
                        )

        elif args.action == "generate-env":
            # Get or allocate ports
            backend_port = pm.get_port_for_category("backend")
            frontend_port = pm.get_port_for_category("frontend")

            if not backend_port:
                backend_port = pm.allocate_port("backend")
            if not frontend_port:
                frontend_port = pm.allocate_port("frontend")

            content = pm.generate_env_ports_content(backend_port, frontend_port)
            env_path = project_root / ".env.ports"
            env_path.write_text(content, encoding="utf-8")

            if args.json:
                print(
                    json.dumps(
                        {
                            "path": str(env_path),
                            "backend_port": backend_port,
                            "frontend_port": frontend_port,
                        }
                    )
                )
            else:
                print(f"Generated {env_path}")
                print(f"  Backend port: {backend_port}")
                print(f"  Frontend port: {frontend_port}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
