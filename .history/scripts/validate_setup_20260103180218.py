#!/usr/bin/env python3
"""
Validation script to check if the Just A Bill application is properly configured
and ready to run. This script performs comprehensive checks on all components.
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Tuple

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class Validator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.passed = 0
        self.failed = 0
    
    def check(self, name: str, condition: bool, error_msg: str = None):
        """Check a condition and track results"""
        if condition:
            print(f"{GREEN}✓{RESET} {name}")
            self.passed += 1
            return True
        else:
            print(f"{RED}✗{RESET} {name}")
            if error_msg:
                print(f"  {error_msg}")
                self.errors.append(f"{name}: {error_msg}")
            self.failed += 1
            return False
    
    def warn(self, name: str, message: str):
        """Issue a warning"""
        print(f"{YELLOW}⚠{RESET} {name}")
        print(f"  {message}")
        self.warnings.append(f"{name}: {message}")
    
    def section(self, name: str):
        """Print a section header"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}{name}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
    
    def validate_file_exists(self, path: Path, name: str) -> bool:
        """Check if a file exists"""
        return self.check(
            f"File exists: {path.name}",
            path.exists(),
            f"Missing file: {path}"
        )
    
    def validate_docker(self):
        """Validate Docker is installed and running"""
        self.section("Docker Validation")
        
        # Check docker command
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.check(
                "Docker installed",
                result.returncode == 0,
                "Docker is not installed or not in PATH"
            )
        except Exception as e:
            self.check("Docker installed", False, str(e))
        
        # Check docker-compose command
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.check(
                "Docker Compose installed",
                result.returncode == 0,
                "Docker Compose is not installed or not in PATH"
            )
        except Exception as e:
            self.check("Docker Compose installed", False, str(e))
    
    def validate_files(self):
        """Validate all required files exist"""
        self.section("File Structure Validation")
        
        # Core files
        core_files = [
            "docker-compose.yml",
            ".env",
            ".env.example",
            "README.md",
        ]
        
        for file in core_files:
            self.validate_file_exists(self.project_root / file, file)
        
        # Backend files
        backend_files = [
            "backend/Dockerfile",
            "backend/requirements.txt",
            "backend/alembic.ini",
            "backend/app/main.py",
            "backend/app/models.py",
            "backend/app/database.py",
            "backend/app/config.py",
            "backend/app/routers/bills.py",
            "backend/app/routers/votes.py",
            "backend/app/routers/ingestion.py",
        ]
        
        for file in backend_files:
            self.validate_file_exists(self.project_root / file, file)
        
        # Frontend files
        frontend_files = [
            "frontend/package.json",
            "frontend/Dockerfile",
            "frontend/pages/index.tsx",
            "frontend/pages/_app.tsx",
        ]
        
        for file in frontend_files:
            self.validate_file_exists(self.project_root / file, file)
    
    def validate_env_file(self):
        """Validate .env file configuration"""
        self.section("Environment Configuration Validation")
        
        env_path = self.project_root / ".env"
        if not env_path.exists():
            self.check(".env file exists", False, "Create .env from .env.example")
            return
        
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        # Check for required variables
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "CONGRESS_API_KEY",
            "LLM_PROVIDER",
            "LLM_API_KEY",
        ]
        
        for var in required_vars:
            if var in env_content:
                # Check if it has a placeholder value
                lines = [l for l in env_content.split('\n') if l.startswith(f"{var}=")]
                if lines:
                    value = lines[0].split('=', 1)[1].strip()
                    
                    # Check for placeholder values
                    if var in ["CONGRESS_API_KEY", "LLM_API_KEY"]:
                        if "your_" in value.lower() or "change" in value.lower() or len(value) < 10:
                            self.warn(
                                f"Environment variable: {var}",
                                f"Appears to be a placeholder. Add your actual API key."
                            )
                        else:
                            self.check(f"Environment variable: {var}", True)
                    else:
                        self.check(f"Environment variable: {var}", True)
            else:
                self.check(
                    f"Environment variable: {var}",
                    False,
                    f"Missing from .env file"
                )
    
    def validate_docker_compose(self):
        """Validate docker-compose.yml structure"""
        self.section("Docker Compose Validation")
        
        compose_path = self.project_root / "docker-compose.yml"
        if not compose_path.exists():
            self.check("docker-compose.yml exists", False)
            return
        
        # Check if it's valid YAML and contains required services
        required_services = ["postgres", "redis", "backend", "worker", "frontend", "n8n"]
        
        try:
            with open(compose_path, 'r') as f:
                content = f.read()
            
            for service in required_services:
                self.check(
                    f"Service defined: {service}",
                    f"{service}:" in content,
                    f"Missing service in docker-compose.yml"
                )
        except Exception as e:
            self.check("docker-compose.yml readable", False, str(e))
    
    def validate_migration(self):
        """Validate database migration files exist"""
        self.section("Database Migration Validation")
        
        migrations_dir = self.project_root / "backend" / "alembic" / "versions"
        
        if not migrations_dir.exists():
            self.check("Migrations directory exists", False, f"Missing: {migrations_dir}")
            return
        
        # Check for migration files
        migration_files = list(migrations_dir.glob("*.py"))
        migration_files = [f for f in migration_files if not f.name.startswith('__')]
        
        self.check(
            "Migration files exist",
            len(migration_files) > 0,
            "No migration files found. Run: docker-compose exec backend alembic revision --autogenerate -m 'initial'"
        )
        
        if migration_files:
            print(f"  Found {len(migration_files)} migration file(s)")
    
    def validate_ports(self):
        """Check if required ports are available"""
        self.section("Port Availability Check")
        
        # On Windows, use netstat
        required_ports = {
            5432: "PostgreSQL",
            6379: "Redis",
            8000: "Backend API",
            3000: "Frontend",
            5678: "n8n"
        }
        
        try:
            result = subprocess.run(
                ["netstat", "-an"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                for port, service in required_ports.items():
                    port_in_use = f":{port} " in output or f":{port}\n" in output
                    if port_in_use:
                        self.warn(
                            f"Port {port} ({service})",
                            "Port appears to be in use. May need to stop existing services."
                        )
                    else:
                        self.check(f"Port {port} ({service})", True)
            else:
                self.warn("Port check", "Could not check port availability")
        except Exception as e:
            self.warn("Port check", f"Could not check ports: {e}")
    
    def generate_report(self):
        """Generate final validation report"""
        self.section("Validation Summary")
        
        total = self.passed + self.failed
        print(f"\nTotal Checks: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        
        if self.failed > 0:
            print(f"\n{RED}Critical Issues:{RESET}")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n{YELLOW}Warnings:{RESET}")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.failed == 0 and len(self.warnings) == 0:
            print(f"\n{GREEN}✓ All checks passed! Ready to start.{RESET}")
            print("\nNext steps:")
            print("  1. docker-compose up -d")
            print("  2. docker-compose exec backend alembic upgrade head")
            print("  3. python scripts/demo.py")
            return True
        elif self.failed == 0:
            print(f"\n{YELLOW}⚠ Setup is functional but has warnings.{RESET}")
            print("Review warnings above and fix if needed.")
            return True
        else:
            print(f"\n{RED}✗ Setup has critical issues that must be fixed.{RESET}")
            return False


def main():
    """Main validation function"""
    print(f"{BLUE}Just A Bill - Setup Validator{RESET}")
    print("=" * 60)
    
    validator = Validator()
    
    # Run all validations
    validator.validate_docker()
    validator.validate_files()
    validator.validate_env_file()
    validator.validate_docker_compose()
    validator.validate_migration()
    validator.validate_ports()
    
    # Generate report
    success = validator.generate_report()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
