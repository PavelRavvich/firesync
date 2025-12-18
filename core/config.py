"""Configuration management for FireSync."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FiresyncConfig:
    """Configuration for FireSync operations."""

    project_id: str
    service_account: str
    key_path: Path
    schema_dir: Path

    @classmethod
    def from_args(
        cls,
        key_path: str,
        schema_dir: str = "firestore_schema"
    ) -> "FiresyncConfig":
        """
        Create configuration from command-line arguments.

        Args:
            key_path: Path to GCP service account key file
            schema_dir: Directory containing schema JSON files

        Returns:
            FiresyncConfig instance

        Raises:
            SystemExit: If key file is invalid or missing
        """
        # Load GCP key file
        key_file_path = Path(key_path)

        if not key_file_path.exists():
            print(f"[!] Key file not found: {key_file_path}")
            print(f"[!] Please ensure the service account key exists at: {key_file_path.resolve()}")
            sys.exit(1)

        try:
            key_data = json.loads(key_file_path.read_text(encoding="utf-8"))
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
            project_id=project_id,
            service_account=service_account,
            key_path=key_file_path.resolve(),
            schema_dir=schema_path
        )

    def display_info(self) -> None:
        """Print configuration information."""
        print(f"[~] Project: {self.project_id}")
        print(f"[~] Service Account: {self.service_account}")
        print(f"[~] Key Path: {self.key_path}")
