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
    key_path: Path
    schema_dir: Path
    _temp_key_file: Optional[str] = None  # For cleanup of temp files

    @classmethod
    def from_args(
        cls,
        key_path: Optional[str] = None,
        key_env: Optional[str] = None,
        key_path_env: Optional[str] = None,
        schema_dir: str = "firestore_schema"
    ) -> "FiresyncConfig":
        """
        Create configuration from command-line arguments.

        Args:
            key_path: Path to GCP service account key file
            key_env: Name of environment variable containing key JSON content
            key_path_env: Name of environment variable containing path to key file
            schema_dir: Directory containing schema JSON files

        Returns:
            FiresyncConfig instance

        Raises:
            SystemExit: If key file is invalid or missing
        """
        # Get key data from either file or environment variable
        key_data, actual_key_path, temp_file = cls._load_key(key_path, key_env, key_path_env)

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
            key_path=actual_key_path,
            schema_dir=schema_path,
            _temp_key_file=temp_file
        )

    @staticmethod
    def _load_key(
        key_path: Optional[str],
        key_env: Optional[str],
        key_path_env: Optional[str] = None  # Deprecated, kept for compatibility
    ) -> Tuple[dict, Path, Optional[str]]:
        """
        Load key from file or environment variable.

        Args:
            key_path: Path to key file
            key_env: Name of environment variable (auto-detects JSON content or file path)
            key_path_env: Deprecated, use key_env instead

        Returns:
            Tuple of (key_data dict, actual_key_path, temp_file_path)
        """
        # Handle deprecated key_path_env by treating it as key_env
        if key_path_env and not key_env:
            key_env = key_path_env

        # Validate: exactly one must be provided
        if key_path and key_env:
            print("[!] Cannot specify both --key-path and --key-env")
            sys.exit(1)

        if not key_path and not key_env:
            print("[!] Must specify either --key-path or --key-env")
            sys.exit(1)

        # Load from file
        if key_path:
            key_file_path = Path(key_path)
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

        # Load from environment variable (auto-detect JSON content or file path)
        if key_env:
            env_value = os.getenv(key_env)
            if not env_value:
                print(f"[!] Environment variable {key_env} is not set")
                sys.exit(1)

            # Try to parse as JSON first
            try:
                key_data = json.loads(env_value)
                # Successfully parsed as JSON - create temp file for gcloud
                try:
                    temp_fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="firesync-key-")
                    with os.fdopen(temp_fd, 'w') as f:
                        json.dump(key_data, f)
                    return key_data, Path(temp_path), temp_path
                except Exception as e:
                    print(f"[!] Failed to create temporary key file: {e}")
                    sys.exit(1)
            except json.JSONDecodeError:
                # Not valid JSON - treat as file path
                key_file_path = Path(env_value)
                if not key_file_path.exists():
                    print(f"[!] Key file not found: {key_file_path}")
                    print(f"[!] Environment variable {key_env} contains neither valid JSON nor a valid file path")
                    sys.exit(1)

                try:
                    key_data = json.loads(key_file_path.read_text(encoding="utf-8"))
                    return key_data, key_file_path.resolve(), None
                except json.JSONDecodeError as e:
                    print(f"[!] Failed to parse key file {key_file_path}: {e}")
                    sys.exit(1)
                except Exception as e:
                    print(f"[!] Failed to read key file {key_file_path}: {e}")
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
        print(f"[~] Key Path: {self.key_path}")
