"""Configuration management for FireSync."""

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class FiresyncConfig:
    """Configuration for FireSync operations."""

    project_id: str
    service_account: str
    key_file: Path
    schema_dir: Path
    _temp_key_file: Optional[str] = None  # For cleanup of temp files

    @classmethod
    def from_args(
        cls,
        key_file: Optional[str] = None,
        key_env: Optional[str] = None,
        schema_dir: str = "firestore_schema"
    ) -> "FiresyncConfig":
        """
        Create configuration from command-line arguments.

        Args:
            key_file: Path to GCP service account key file
            key_env: Name of environment variable containing key JSON or path to key file
            schema_dir: Directory containing schema JSON files

        Returns:
            FiresyncConfig instance

        Raises:
            SystemExit: If key file is invalid or missing
        """
        # Get key data from either file or environment variable
        key_data, actual_key_file, temp_file = cls._load_key(key_file, key_env)

        # Extract required fields
        try:
            project_id = key_data["project_id"]
            service_account = key_data["client_email"]
        except KeyError as e:
            print(f"[!] Invalid key format: missing field {e}")
            sys.exit(1)

        # Resolve schema directory
        schema_path = (Path.cwd() / schema_dir).resolve()

        return cls(
            project_id=project_id,
            service_account=service_account,
            key_file=actual_key_file,
            schema_dir=schema_path,
            _temp_key_file=temp_file
        )

    @staticmethod
    def _load_key(
        key_file: Optional[str],
        key_env: Optional[str]
    ) -> Tuple[dict, Path, Optional[str]]:
        """
        Load key from file or environment variable.

        Args:
            key_file: Path to key file
            key_env: Name of environment variable with key JSON or path to key file

        Returns:
            Tuple of (key_data dict, actual_key_file, temp_file_path)
        """
        # Validate: exactly one must be provided
        if key_file and key_env:
            print("[!] Cannot specify both --key-file and --key-env")
            sys.exit(1)

        if not key_file and not key_env:
            print("[!] Must specify either --key-file or --key-env")
            sys.exit(1)

        # Load from file
        if key_file:
            key_file_path = Path(key_file)
            if not key_file_path.exists():
                print(f"[!] Key file not found: {key_file_path}")
                print(f"[!] Please ensure the service account key exists at: {key_file_path.resolve()}")
                sys.exit(1)

            try:
                key_data = json.loads(key_file_path.read_text(encoding="utf-8"))
                return key_data, key_file_path.resolve(), None
            except json.JSONDecodeError as e:
                print(f"[!] Failed to parse key file: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"[!] Failed to read key file: {e}")
                sys.exit(1)

        # Load from environment variable (auto-detect JSON vs file path)
        if key_env:
            env_value = os.getenv(key_env)
            if not env_value:
                print(f"[!] Environment variable {key_env} is not set")
                sys.exit(1)

            # Try to detect if it's a file path or JSON
            # If it starts with '{' it's likely JSON, otherwise try as file path first
            is_json = env_value.strip().startswith('{')

            if not is_json:
                # Try to treat as file path first
                potential_file = Path(env_value)
                if potential_file.exists() and potential_file.is_file():
                    try:
                        key_data = json.loads(potential_file.read_text(encoding="utf-8"))
                        return key_data, potential_file.resolve(), None
                    except json.JSONDecodeError:
                        # Not a valid JSON file, fall through to try parsing as JSON string
                        pass

            # Try to parse as JSON string
            try:
                key_data = json.loads(env_value)
            except json.JSONDecodeError as e:
                print(f"[!] Environment variable {key_env} is neither a valid file path nor valid JSON")
                print(f"[!] JSON parse error: {e}")
                sys.exit(1)

            # Create temporary file for gcloud to use
            try:
                temp_fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="firesync-key-")
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(key_data, f)
                return key_data, Path(temp_path), temp_path
            except Exception as e:
                print(f"[!] Failed to create temporary key file: {e}")
                sys.exit(1)

    def __del__(self):
        """Clean up temporary key file if created."""
        if self._temp_key_file and os.path.exists(self._temp_key_file):
            try:
                os.unlink(self._temp_key_file)
            except Exception:
                pass  # Ignore cleanup errors

    def display_info(self) -> None:
        """Print configuration information."""
        print(f"[~] Project: {self.project_id}")
        print(f"[~] Service Account: {self.service_account}")
        print(f"[~] Key File: {self.key_file}")
