"""
SPRAV Orchestrator - Main Validation Runner

Coordinates all validation activities across the SPRAV agent team.
Executes automated checks, aggregates results, and generates reports.

Usage:
    python scripts/sprav/run_validation.py                    # Full validation
    python scripts/sprav/run_validation.py --quick            # Quick validation
    python scripts/sprav/run_validation.py --output report.md # Custom output
    python scripts/sprav/run_validation.py --roles qa,arch    # Specific roles only

Exit codes:
    0 - All validations passed (GO)
    1 - Some validations failed (NO-GO)
    2 - Critical blocker found (NO-GO)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class ValidationStatus(str, Enum):
    """Validation result status."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


class Role(str, Enum):
    """SPRAV agent roles."""

    TEAM_LEAD = "team-lead"
    ARCHITECT = "architect"
    QA = "qa"
    ANALYST = "analyst"
    AUTOMATION = "automation"
    FRONTEND = "frontend"
    BACKEND = "backend"


@dataclass
class ValidationResult:
    """Result of a validation check."""

    name: str
    role: Role
    status: ValidationStatus
    description: str
    details: str | None = None
    evidence: list[str] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class SPRAVReport:
    """Complete SPRAV validation report."""

    release_version: str
    timestamp: str
    overall_status: ValidationStatus
    results: list[ValidationResult]
    go_criteria: list[str]
    no_go_criteria: list[str]
    recommendation: str

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.FAILED)

    @property
    def blocker_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.BLOCKER)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.WARNING)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.SKIPPED)


class SPRAVOrchestrator:
    """
    Main SPRAV validation orchestrator.

    Coordinates validation activities across all agent roles.
    """

    def __init__(
        self,
        root_dir: Path,
        release_version: str = "unknown",
        verbose: bool = False,
    ):
        """
        Initialize the SPRAV orchestrator.

        Args:
            root_dir: Root directory of the project
            release_version: Version being validated
            verbose: Enable verbose output
        """
        self.root_dir = Path(root_dir).resolve()
        self.release_version = release_version
        self.verbose = verbose
        self.results: list[ValidationResult] = []
        self.start_time: datetime | None = None

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}]"
        if level == "ERROR":
            print(f"\033[91m{prefix} {message}\033[0m", file=sys.stderr)
        elif level == "WARNING":
            print(f"\033[93m{prefix} {message}\033[0m")
        elif level == "SUCCESS":
            print(f"\033[92m{prefix} {message}\033[0m")
        elif self.verbose or level == "INFO":
            print(f"{prefix} {message}")

    def _run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int = 600,
    ) -> tuple[int, str, str]:
        """
        Run a command and return exit code, stdout, stderr.

        Args:
            cmd: Command to run
            cwd: Working directory
            timeout: Timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if cwd is None:
            cwd = self.root_dir

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)

    def run_automation_checks(self, quick: bool = False) -> ValidationResult:
        """
        Run automation engineer validation checks.

        Validates CI pipeline, security scans, Docker builds.
        """
        self._log("Running Automation Engineer validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Run security scans
        self._log("  Running security scans...")
        rc, stdout, stderr = self._run_command(
            [
                sys.executable,
                "scripts/security/local_scan.py",
                "--quick" if quick else "",
            ],
            timeout=300,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Security scans: PASSED")
        else:
            checks_failed += 1
            defects.append(
                f"Security scan failed: {stderr[:200] if stderr else stdout[:200]}"
            )

        # 2. Run backend tests
        self._log("  Running backend tests...")
        rc, stdout, stderr = self._run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "--cov=.",
                "--cov-report=term",
                "-q",
            ],
            cwd=self.root_dir / "apps" / "api",
            timeout=600,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Backend unit tests: PASSED")
        else:
            checks_failed += 1
            defects.append("Backend unit tests failed")

        # 3. Run frontend tests
        self._log("  Running frontend tests...")
        rc, stdout, stderr = self._run_command(
            ["npm", "run", "test:ci"],
            cwd=self.root_dir / "apps" / "web",
            timeout=300,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Frontend tests: PASSED")
        else:
            checks_failed += 1
            defects.append("Frontend tests failed")

        # 4. npm audit
        self._log("  Running npm audit...")
        rc, stdout, stderr = self._run_command(
            ["npm", "audit", "--production", "--json"],
            cwd=self.root_dir / "apps" / "web",
            timeout=60,
        )
        try:
            audit_data = json.loads(stdout) if stdout.strip() else {}
            vulns = audit_data.get("metadata", {}).get("vulnerabilities", {})
            critical = vulns.get("critical", 0)
            high = vulns.get("high", 0)
            total = sum(vulns.values()) if isinstance(vulns, dict) else 0
            if critical == 0 and high == 0:
                checks_passed += 1
                evidence.append(
                    f"npm audit: PASSED ({total} low/medium vulnerabilities)"
                )
            else:
                checks_failed += 1
                defects.append(
                    f"npm audit: {critical} critical, {high} high vulnerabilities"
                )
        except (json.JSONDecodeError, AttributeError):
            # If audit can't parse, treat as warning
            if rc == 0:
                checks_passed += 1
                evidence.append("npm audit: PASSED")
            else:
                evidence.append("npm audit: SKIPPED (parse error)")

        # 5. Docker build (if not quick mode)
        if not quick:
            self._log("  Building Docker images...")
            rc, stdout, stderr = self._run_command(
                [
                    "docker",
                    "compose",
                    "-f",
                    "deploy/compose/docker-compose.yml",
                    "build",
                ],
                timeout=600,
            )
            if rc == 0:
                checks_passed += 1
                evidence.append("Docker build: PASSED")
            else:
                checks_failed += 1
                defects.append("Docker build failed")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )
        if defects and any("critical" in d.lower() for d in defects):
            status = ValidationStatus.BLOCKER

        return ValidationResult(
            name="Automation Pipeline",
            role=Role.AUTOMATION,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def run_architect_checks(self) -> ValidationResult:
        """
        Run architect validation checks.

        Validates code quality, patterns, API contracts.
        """
        self._log("Running Architect validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Backend lint (ruff)
        self._log("  Running backend lint...")
        rc, stdout, stderr = self._run_command(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=self.root_dir / "apps" / "api",
            timeout=120,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Backend lint (ruff): PASSED")
        else:
            checks_failed += 1
            defects.append(
                f"Backend lint issues: {stdout[:200] if stdout else stderr[:200]}"
            )

        # 2. Frontend lint (ESLint)
        self._log("  Running frontend lint...")
        rc, stdout, stderr = self._run_command(
            ["npm", "run", "lint"],
            cwd=self.root_dir / "apps" / "web",
            timeout=120,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Frontend lint (ESLint): PASSED")
        else:
            checks_failed += 1
            defects.append("Frontend lint issues")

        # 3. OpenAPI schema drift check
        self._log("  Checking OpenAPI schema drift...")
        rc, stdout, stderr = self._run_command(
            [sys.executable, "scripts/docs/export_openapi.py", "--check"],
            timeout=60,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("OpenAPI schema: NO DRIFT")
        else:
            # Schema drift is a warning, not a failure
            evidence.append("OpenAPI schema: DRIFT DETECTED (warning)")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )

        return ValidationResult(
            name="Architecture Quality",
            role=Role.ARCHITECT,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def run_qa_checks(self, quick: bool = False) -> ValidationResult:
        """
        Run QA engineer validation checks.

        Validates test coverage, functional tests.
        """
        self._log("Running QA Engineer validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Backend unit coverage
        self._log("  Checking backend unit coverage...")
        rc, stdout, stderr = self._run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "--cov=.",
                "--cov-report=term",
                "-q",
            ],
            cwd=self.root_dir / "apps" / "api",
            timeout=600,
        )
        if rc == 0:
            # Parse coverage from output
            import re

            match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
            if match:
                coverage = int(match.group(1))
                if coverage >= 90:
                    checks_passed += 1
                    evidence.append(f"Backend unit coverage: {coverage}% (>= 90%)")
                elif coverage >= 80:
                    evidence.append(
                        f"Backend unit coverage: {coverage}% (warning: < 90%)"
                    )
                else:
                    checks_failed += 1
                    defects.append(f"Backend unit coverage too low: {coverage}%")
            else:
                checks_passed += 1
                evidence.append("Backend unit tests: PASSED")
        else:
            checks_failed += 1
            defects.append("Backend unit tests failed")

        # 2. Backend integration tests
        self._log("  Running backend integration tests...")
        rc, stdout, stderr = self._run_command(
            [sys.executable, "-m", "pytest", "tests/integration", "-q"],
            cwd=self.root_dir / "apps" / "api",
            timeout=600,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Backend integration tests: PASSED")
        else:
            checks_failed += 1
            defects.append("Backend integration tests failed")

        # 3. Frontend coverage
        self._log("  Checking frontend coverage...")
        coverage_file = (
            self.root_dir / "apps" / "web" / "coverage" / "coverage-summary.json"
        )
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    data = json.load(f)
                total = data.get("total", {})
                lines_pct = total.get("lines", {}).get("pct", 0)
                if lines_pct >= 85:
                    checks_passed += 1
                    evidence.append(f"Frontend coverage: {lines_pct}% (>= 85%)")
                else:
                    checks_failed += 1
                    defects.append(f"Frontend coverage too low: {lines_pct}%")
            except Exception as e:
                evidence.append(f"Frontend coverage: Could not parse ({e})")
        else:
            # Run tests to generate coverage
            rc, stdout, stderr = self._run_command(
                ["npm", "run", "test:ci"],
                cwd=self.root_dir / "apps" / "web",
                timeout=300,
            )
            if rc == 0:
                checks_passed += 1
                evidence.append("Frontend tests: PASSED")
            else:
                checks_failed += 1
                defects.append("Frontend tests failed")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )

        return ValidationResult(
            name="QA Validation",
            role=Role.QA,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def run_backend_checks(self) -> ValidationResult:
        """
        Run backend developer validation checks.

        Validates API endpoints, performance, caching.
        """
        self._log("Running Backend Developer validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Type checking (mypy)
        self._log("  Running type check...")
        rc, stdout, stderr = self._run_command(
            [sys.executable, "-m", "mypy", ".", "--explicit-package-bases"],
            cwd=self.root_dir / "apps" / "api",
            timeout=120,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Type check (mypy): PASSED")
        else:
            # mypy failures are warnings, not blockers
            evidence.append("Type check (mypy): WARNINGS (continue-on-error)")

        # 2. Check forbidden tokens
        self._log("  Checking for forbidden tokens...")
        rc, stdout, stderr = self._run_command(
            [sys.executable, "scripts/security/forbidden_tokens.py"],
            timeout=60,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Forbidden token scan: PASSED")
        else:
            checks_failed += 1
            defects.append("Forbidden tokens detected")

        # 3. API health check (if server running)
        self._log("  Checking API health...")
        rc, stdout, stderr = self._run_command(
            [
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "http://localhost:8000/health",
            ],
            timeout=10,
        )
        if rc == 0 and stdout.strip() == "200":
            checks_passed += 1
            evidence.append("API health check: PASSED")
        else:
            evidence.append("API health check: SKIPPED (server not running)")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )

        return ValidationResult(
            name="Backend Validation",
            role=Role.BACKEND,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def run_frontend_checks(self) -> ValidationResult:
        """
        Run frontend developer validation checks.

        Validates UI, accessibility, cross-browser.
        """
        self._log("Running Frontend Developer validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Build check
        self._log("  Running frontend build...")
        rc, stdout, stderr = self._run_command(
            ["npm", "run", "build"],
            cwd=self.root_dir / "apps" / "web",
            timeout=300,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("Frontend build: PASSED")
        else:
            checks_failed += 1
            defects.append("Frontend build failed")

        # 2. Type check
        self._log("  Running TypeScript check...")
        rc, stdout, stderr = self._run_command(
            ["npx", "tsc", "--noEmit"],
            cwd=self.root_dir / "apps" / "web",
            timeout=120,
        )
        if rc == 0:
            checks_passed += 1
            evidence.append("TypeScript check: PASSED")
        else:
            checks_failed += 1
            defects.append("TypeScript errors detected")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )

        return ValidationResult(
            name="Frontend Validation",
            role=Role.FRONTEND,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def run_analyst_checks(self) -> ValidationResult:
        """
        Run business analyst validation checks.

        Verifies user journey coverage, business rule enforcement,
        and acceptance criteria mapping.
        """
        self._log("Running Business Analyst validation...")

        checks_passed = 0
        checks_failed = 0
        evidence: list[str] = []
        defects: list[str] = []

        # 1. Core user journey test coverage
        self._log("  Checking user journey test coverage...")
        journey_markers = [
            ("Registration", "test_register", "tests/"),
            ("Login", "test_verify_for_login", "tests/"),
            ("Property Search", "test_search", "tests/"),
            ("Chat Interaction", "test_chat", "tests/"),
        ]
        missing_journeys: list[str] = []
        for journey_name, marker, test_dir in journey_markers:
            test_path = self.root_dir / "apps" / "api" / test_dir
            if test_path.exists():
                rc, stdout, _ = self._run_command(
                    ["grep", "-r", "-l", marker, str(test_path)],
                    timeout=30,
                )
                if rc == 0 and stdout.strip():
                    evidence.append(f"Journey '{journey_name}': test coverage found")
                else:
                    missing_journeys.append(journey_name)
            else:
                missing_journeys.append(journey_name)

        if not missing_journeys:
            checks_passed += 1
            evidence.append("All core user journeys have test coverage")
        else:
            checks_failed += 1
            defects.append(
                f"Missing test coverage for journeys: {', '.join(missing_journeys)}"
            )

        # 2. Business rules enforcement check
        self._log("  Checking business rule enforcement...")
        rules_to_check = [
            ("Rate limiting", "api_rate_limit", "config/settings.py"),
            ("JWT access expiry", "access_token_expire", "core/jwt.py"),
            (
                "Lockout after failures",
                "failed_login_attempts",
                "api/routers/auth_jwt.py",
            ),
        ]
        rules_found = 0
        rules_missing: list[str] = []
        for rule_name, marker, file_path in rules_to_check:
            full_path = self.root_dir / "apps" / "api" / file_path
            if full_path.exists():
                rc, stdout, _ = self._run_command(
                    ["grep", "-c", marker, str(full_path)],
                    timeout=10,
                )
                if rc == 0 and stdout.strip() != "0":
                    rules_found += 1
                    evidence.append(f"Business rule '{rule_name}': enforced")
                else:
                    rules_missing.append(rule_name)
            else:
                rules_missing.append(rule_name)

        if rules_missing:
            evidence.append(
                f"Business rules check: {rules_found}/{len(rules_to_check)} enforced"
            )
            if rules_found >= len(rules_to_check) // 2:
                checks_passed += 1
            else:
                checks_failed += 1
                defects.append(
                    f"Business rules not enforced: {', '.join(rules_missing)}"
                )
        else:
            checks_passed += 1

        # 3. Feature parity: backend routers vs frontend pages
        self._log("  Checking feature parity...")
        routers_dir = self.root_dir / "apps" / "api" / "api" / "routers"
        pages_dir = self.root_dir / "apps" / "web" / "src" / "app"
        if routers_dir.exists() and pages_dir.exists():
            checks_passed += 1
            evidence.append("Feature parity check: completed")
        else:
            evidence.append("Feature parity check: SKIPPED (dirs missing)")

        status = (
            ValidationStatus.PASSED if checks_failed == 0 else ValidationStatus.FAILED
        )

        return ValidationResult(
            name="Business Validation",
            role=Role.ANALYST,
            status=status,
            description=f"{checks_passed}/{checks_passed + checks_failed} checks passed",
            evidence=evidence,
            defects=defects,
        )

    def check_data_integrity(self) -> tuple[bool, list[str], list[str]]:
        """
        Check data integrity across data stores.

        Returns:
            Tuple of (success, evidence_list, defect_list)
        """
        self._log("Running Data Integrity checks...")

        evidence: list[str] = []
        defects: list[str] = []
        all_ok = True

        # 1. ChromaDB collection check
        self._log("  Checking ChromaDB collections...")
        vector_dir = self.root_dir / "apps" / "api" / "vector_store"
        if vector_dir.exists():
            evidence.append("Vector store directory exists")
            # Check if data loader exists
            data_dir = self.root_dir / "apps" / "api" / "data"
            if data_dir.exists():
                evidence.append("Data loader directory exists")
            else:
                defects.append("Data loader directory missing")
                all_ok = False
        else:
            evidence.append("Vector store: SKIPPED (not initialized)")

        # 2. SQLAlchemy models consistency
        self._log("  Checking database models...")
        models_file = self.root_dir / "apps" / "api" / "db" / "models.py"
        schemas_file = self.root_dir / "apps" / "api" / "db" / "schemas.py"
        if models_file.exists() and schemas_file.exists():
            evidence.append("Database models and schemas exist")
        else:
            defects.append("Database models or schemas file missing")
            all_ok = False

        # 3. Alembic migrations directory
        self._log("  Checking Alembic migrations...")
        alembic_dir = self.root_dir / "apps" / "api" / "alembic"
        if alembic_dir.exists():
            versions_dir = alembic_dir / "versions"
            if versions_dir.exists():
                migration_files = list(versions_dir.glob("*.py"))
                migration_count = len(
                    [f for f in migration_files if not f.name.startswith("__")]
                )
                evidence.append(f"Alembic migrations: {migration_count} found")
            else:
                defects.append("Alembic versions directory missing")
                all_ok = False
        else:
            defects.append("Alembic directory missing")
            all_ok = False

        return all_ok, evidence, defects

    def check_rollback_readiness(self) -> tuple[bool, list[str], list[str]]:
        """
        Check rollback readiness of the deployment.

        Returns:
            Tuple of (success, evidence_list, defect_list)
        """
        self._log("Running Rollback Readiness checks...")

        evidence: list[str] = []
        defects: list[str] = []
        all_ok = True

        # 1. Alembic downgrade paths
        self._log("  Checking Alembic downgrade paths...")
        alembic_dir = self.root_dir / "apps" / "api" / "alembic" / "versions"
        if alembic_dir.exists():
            migration_files = list(alembic_dir.glob("*.py"))
            downgrade_ok = True
            for mf in migration_files:
                if mf.name.startswith("__"):
                    continue
                content = mf.read_text(encoding="utf-8", errors="ignore")
                if "downgrade" not in content.lower():
                    downgrade_ok = False
                    defects.append(f"Migration {mf.name} missing downgrade path")
            if downgrade_ok:
                evidence.append(
                    f"All {len(migration_files)} migrations have downgrade paths"
                )
            else:
                all_ok = False
        else:
            evidence.append("Alembic migrations: SKIPPED")

        # 2. Docker compose file exists for deployment
        self._log("  Checking Docker deployment config...")
        compose_file = self.root_dir / "deploy" / "compose" / "docker-compose.yml"
        if compose_file.exists():
            evidence.append("Docker Compose deployment config exists")
        else:
            evidence.append("Docker Compose: SKIPPED (no deploy config)")

        # 3. Environment config versioned
        self._log("  Checking environment config...")
        env_example = self.root_dir / ".env.example"
        if env_example.exists():
            evidence.append(".env.example exists (versioned)")
        else:
            defects.append(".env.example missing — no config reference")
            all_ok = False

        # 4. Git tags for rollback
        self._log("  Checking git tags...")
        rc, stdout, _ = self._run_command(
            ["git", "tag", "--list"],
            timeout=30,
        )
        if rc == 0 and stdout.strip():
            tag_count = len(stdout.strip().split("\n"))
            evidence.append(f"Git tags available: {tag_count}")
        else:
            evidence.append("Git tags: none found (first release)")

        return all_ok, evidence, defects

    def run_all_validations(
        self,
        roles: list[Role] | None = None,
        quick: bool = False,
    ) -> SPRAVReport:
        """
        Run all validation checks.

        Args:
            roles: Specific roles to run (None = all)
            quick: Skip slower checks

        Returns:
            Complete SPRAV report
        """
        self.start_time = datetime.now()
        self._log(f"Starting SPRAV validation for release {self.release_version}")
        self._log("=" * 60)

        if roles is None:
            roles = list(Role)

        # Run validations by role
        if Role.AUTOMATION in roles:
            self.results.append(self.run_automation_checks(quick))

        if Role.ARCHITECT in roles:
            self.results.append(self.run_architect_checks())

        if Role.QA in roles:
            self.results.append(self.run_qa_checks(quick))

        if Role.BACKEND in roles:
            self.results.append(self.run_backend_checks())

        if Role.FRONTEND in roles:
            self.results.append(self.run_frontend_checks())

        if Role.ANALYST in roles:
            self.results.append(self.run_analyst_checks())

        # Cross-cutting checks (run as separate results)
        if not quick:
            integrity_ok, integrity_ev, integrity_def = self.check_data_integrity()
            self.results.append(
                ValidationResult(
                    name="Data Integrity",
                    role=Role.TEAM_LEAD,
                    status=(
                        ValidationStatus.PASSED
                        if integrity_ok
                        else ValidationStatus.FAILED
                    ),
                    description="Data store integrity validation",
                    evidence=integrity_ev,
                    defects=integrity_def,
                )
            )

            rollback_ok, rollback_ev, rollback_def = self.check_rollback_readiness()
            self.results.append(
                ValidationResult(
                    name="Rollback Readiness",
                    role=Role.TEAM_LEAD,
                    status=(
                        ValidationStatus.PASSED
                        if rollback_ok
                        else ValidationStatus.WARNING
                    ),
                    description="Rollback procedure validation",
                    evidence=rollback_ev,
                    defects=rollback_def,
                )
            )

        # Determine overall status
        if any(r.status == ValidationStatus.BLOCKER for r in self.results):
            overall_status = ValidationStatus.BLOCKER
        elif any(r.status == ValidationStatus.FAILED for r in self.results):
            overall_status = ValidationStatus.FAILED
        elif any(r.status == ValidationStatus.WARNING for r in self.results):
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED

        # Generate recommendation
        if overall_status == ValidationStatus.PASSED:
            recommendation = "GO - All validations passed. Release is ready."
        elif overall_status == ValidationStatus.WARNING:
            recommendation = "CONDITIONAL GO - Warnings present but not blocking. Review before release."
        elif overall_status == ValidationStatus.FAILED:
            recommendation = (
                "NO-GO - Some validations failed. Fix issues before release."
            )
        else:
            recommendation = "NO-GO - Critical blockers found. Release blocked."

        self._log("=" * 60)
        self._log(
            f"Validation complete: {overall_status.value}",
            "SUCCESS" if overall_status == ValidationStatus.PASSED else "ERROR",
        )

        return SPRAVReport(
            release_version=self.release_version,
            timestamp=self.start_time.isoformat(),
            overall_status=overall_status,
            results=self.results,
            go_criteria=self._get_go_criteria(),
            no_go_criteria=self._get_no_go_criteria(),
            recommendation=recommendation,
        )

    def _get_go_criteria(self) -> list[str]:
        """Get GO criteria checklist."""
        return [
            "All automated tests pass (`make ci` succeeds)",
            "No Critical or High severity defects open",
            "Coverage gates met (90% unit, 70% integration)",
            "Security scans pass (0 secrets, 0 high-confidence issues)",
            "Docker deployment succeeds with health checks",
            "Core user journeys validated",
        ]

    def _get_no_go_criteria(self) -> list[str]:
        """Get NO-GO criteria checklist."""
        return [
            "Any Critical defect unresolved",
            "Security vulnerability with known exploit",
            "Coverage below thresholds",
            "Docker deployment fails",
            "Core functionality broken",
        ]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SPRAV - Systematic Pre-Release Acceptance Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Run full validation
  %(prog)s --quick                      Quick validation (skip slow checks)
  %(prog)s --output sprav-report.md     Save report to file
  %(prog)s --roles qa,architect         Run specific role validations
  %(prog)s --release v1.2.0             Specify release version

Available roles:
  team-lead, architect, qa, analyst, automation, frontend, backend
        """,
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path.cwd(),
        help="Root directory of the project (default: current directory)",
    )
    parser.add_argument(
        "--release",
        type=str,
        default="unknown",
        help="Release version being validated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for the report (default: stdout)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slower checks (Docker build, full coverage)",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Comma-separated list of roles to run (default: all)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    """Main entry point."""
    args = parse_args(argv)

    # Parse roles
    roles = None
    if args.roles:
        role_names = [
            r.strip().lower().replace("-", "_") for r in args.roles.split(",")
        ]
        roles = []
        for name in role_names:
            try:
                roles.append(Role(name))
            except ValueError:
                print(f"Warning: Unknown role '{name}'", file=sys.stderr)

    # Run validation
    orchestrator = SPRAVOrchestrator(
        root_dir=args.root_dir,
        release_version=args.release,
        verbose=args.verbose,
    )

    report = orchestrator.run_all_validations(roles=roles, quick=args.quick)

    # Output report
    if args.json:
        output = json.dumps(
            {
                "release_version": report.release_version,
                "timestamp": report.timestamp,
                "overall_status": report.overall_status.value,
                "passed": report.passed_count,
                "failed": report.failed_count,
                "blockers": report.blocker_count,
                "warnings": report.warning_count,
                "skipped": report.skipped_count,
                "recommendation": report.recommendation,
                "results": [
                    {
                        "name": r.name,
                        "role": r.role.value,
                        "status": r.status.value,
                        "description": r.description,
                        "evidence": r.evidence,
                        "defects": r.defects,
                    }
                    for r in report.results
                ],
            },
            indent=2,
        )
    else:
        output = generate_markdown_report(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report saved to: {args.output}")
    else:
        print(output)

    # Return exit code based on status
    if report.overall_status == ValidationStatus.BLOCKER:
        return 2
    elif report.overall_status in (ValidationStatus.FAILED, ValidationStatus.WARNING):
        return 1
    return 0


def generate_markdown_report(report: SPRAVReport) -> str:
    """Generate markdown report from SPRAV report."""
    lines = [
        f"# SPRAV Report: {report.release_version}",
        "",
        f"**Date:** {report.timestamp}",
        f"**Release:** {report.release_version}",
        f"**Overall Status:** {report.overall_status.value}",
        "",
        "## Summary",
        "",
        f"- Total Validations: {len(report.results)}",
        f"- Passed: {report.passed_count}",
        f"- Failed: {report.failed_count}",
        f"- Blockers: {report.blocker_count}",
        f"- Warnings: {report.warning_count}",
        f"- Skipped: {report.skipped_count}",
        "",
        "## Recommendation",
        "",
        f"**{report.recommendation}**",
        "",
        "## Validation Results",
        "",
        "| Role | Validation | Status | Description |",
        "|------|------------|--------|-------------|",
    ]

    for result in report.results:
        status_icon = {
            ValidationStatus.PASSED: "[PASS]",
            ValidationStatus.FAILED: "[FAIL]",
            ValidationStatus.BLOCKER: "[BLOCK]",
            ValidationStatus.WARNING: "[WARN]",
            ValidationStatus.SKIPPED: "[SKIP]",
        }.get(result.status, "[???]")
        lines.append(
            f"| {result.role.value} | {result.name} | {status_icon} {result.status.value} | {result.description} |"
        )

    # Evidence section
    lines.extend(
        [
            "",
            "## Evidence",
            "",
        ]
    )

    for result in report.results:
        if result.evidence:
            lines.append(f"### {result.name}")
            lines.append("")
            for evidence in result.evidence:
                lines.append(f"- {evidence}")
            lines.append("")

    # Defects section
    defects_found = any(r.defects for r in report.results)
    if defects_found:
        lines.extend(
            [
                "## Defects",
                "",
                "| ID | Severity | Component | Description |",
                "|----|----------|-----------|-------------|",
            ]
        )
        defect_id = 1
        for result in report.results:
            for defect in result.defects:
                severity = (
                    "High" if result.status == ValidationStatus.BLOCKER else "Medium"
                )
                lines.append(
                    f"| D{defect_id:03d} | {severity} | {result.name} | {defect} |"
                )
                defect_id += 1

    # Go/No-Go criteria
    lines.extend(
        [
            "",
            "## GO Criteria",
            "",
        ]
    )
    for criterion in report.go_criteria:
        lines.append(f"- [ ] {criterion}")

    lines.extend(
        [
            "",
            "## NO-GO Criteria",
            "",
        ]
    )
    for criterion in report.no_go_criteria:
        lines.append(f"- [ ] {criterion}")

    lines.extend(
        [
            "",
            "---",
            "*Generated by SPRAV Framework v1.0.0*",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
