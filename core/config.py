"""Configuration management for FireSync."""

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Environment(Enum):
    """Supported deployment environments."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Convert string to Environment enum."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {value}. Must be one of: dev, staging, production")


@dataclass
class FiresyncConfig:
    """Configuration for FireSync operations."""

    env: Environment
    project_id: str
    service_account: str
    key_path: Path
    schema_dir: Path

    @classmethod
    def from_args(
        cls,
        env: Optional[str] = None,
        schema_dir: str = "firestore_schema"
    ) -> "FiresyncConfig":
        """
        Create configuration from command-line arguments and environment.

        Args:
            env: Environment name (dev, staging, production)
            schema_dir: Directory containing schema JSON files

        Returns:
            FiresyncConfig instance

        Raises:
            SystemExit: If environment is not specified or key file is invalid
        """
        # Get environment from argument or ENV variable
        env_str = env or os.getenv("ENV")
        if not env_str:
            print("[!] Please provide --env flag or set ENV environment variable.")
            print("[!] Valid values: dev, staging, production")
            sys.exit(1)

        try:
            environment = Environment.from_string(env_str)
        except ValueError as e:
            print(f"[!] {e}")
            sys.exit(1)

        # Load GCP key file
        key_path = Path(f"secrets/gcp-key-{environment.value}.json")
        if not key_path.exists():
            print(f"[!] Key file not found: {key_path}")
            print(f"[!] Please ensure the service account key exists at: {key_path.resolve()}")
            sys.exit(1)

        try:
            key_data = json.loads(key_path.read_text(encoding="utf-8"))
            project_id = key_data["project_id"]
            service_account = key_data["client_email"]
        except KeyError as e:
            print(f"[!] Invalid key file format: missing field {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[!] Failed to parse key file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[!] Failed to read key file: {e}")
            sys.exit(1)

        # Resolve schema directory
        schema_path = (Path.cwd() / schema_dir).resolve()

        return cls(
            env=environment,
            project_id=project_id,
            service_account=service_account,
            key_path=key_path.resolve(),
            schema_dir=schema_path
        )

    def display_info(self) -> None:
        """Print configuration information."""
        print(f"[~] Environment: {self.env.value}")
        print(f"[~] Project: {self.project_id}")
        print(f"[~] Service Account: {self.service_account}")
