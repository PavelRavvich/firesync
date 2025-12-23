"""GCloud CLI wrapper for Firestore operations."""

import json
import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from firesync.config import FiresyncConfig

logger = logging.getLogger(__name__)


def get_gcloud_binary() -> str:
    """
    Get the appropriate gcloud binary for the current platform.

    Returns:
        str: "gcloud.cmd" on Windows, "gcloud" on other platforms
    """
    return "gcloud.cmd" if platform.system() == "Windows" else "gcloud"


class GCloudClient:
    """Client for executing gcloud commands."""

    def __init__(self, config: FiresyncConfig):
        """
        Initialize GCloud client.

        Args:
            config: FiresyncConfig instance with project and authentication details
        """
        self.config = config
        self.gcloud_bin = get_gcloud_binary()
        self._authenticated = False

    def activate_service_account(self) -> None:
        """
        Activate GCP service account for gcloud commands.

        Raises:
            SystemExit: If authentication fails
        """
        if self._authenticated:
            return

        logger.info(f"Activating service account: {self.config.service_account}")
        print(f"[~] Activating {self.config.service_account} for project {self.config.project_id}")

        cmd = [
            self.gcloud_bin,
            "auth",
            "activate-service-account",
            self.config.service_account,
            f"--key-file={self.config.key_path}",
            f"--project={self.config.project_id}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[!] Failed to activate service account: {result.stderr.strip()}")
            sys.exit(1)

        self._authenticated = True
        logger.info("Service account activated successfully")

    def run_command(
        self,
        cmd: List[str],
        capture_json: bool = False,
        quiet: bool = False
    ) -> Optional[Any]:
        """
        Execute a gcloud command.

        Args:
            cmd: Command arguments (without 'gcloud' prefix)
            capture_json: If True, parse output as JSON
            quiet: If True, add --quiet flag

        Returns:
            Parsed JSON if capture_json=True, None otherwise

        Raises:
            SystemExit: If command fails
        """
        self.activate_service_account()

        full_cmd = [self.gcloud_bin] + cmd + [f"--project={self.config.project_id}"]

        if capture_json:
            full_cmd.append("--format=json")

        if quiet:
            full_cmd.append("--quiet")

        logger.debug(f"Running: {' '.join(full_cmd)}")

        result = subprocess.run(full_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.error(f"Command failed: {stderr}")
            print(f"[!] gcloud error: {stderr}")
            sys.exit(1)

        if capture_json:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"[!] Failed to parse gcloud JSON output: {e}")
                sys.exit(1)

        return None

    def run_command_tolerant(
        self,
        cmd: List[str],
        quiet: bool = True
    ) -> bool:
        """
        Execute a gcloud command with error tolerance (for apply operations).

        Args:
            cmd: Command arguments (without 'gcloud' prefix)
            quiet: If True, add --quiet flag

        Returns:
            True if successful, False if failed
        """
        self.activate_service_account()

        full_cmd = [self.gcloud_bin] + cmd + [f"--project={self.config.project_id}"]

        if quiet:
            full_cmd.append("--quiet")

        print(f"[~] {' '.join(full_cmd)}")
        logger.debug(f"Running: {' '.join(full_cmd)}")

        result = subprocess.run(full_cmd, capture_output=True, text=True)
        stderr = result.stderr.strip().lower()

        if result.returncode != 0:
            if "already exists" in stderr or "already_exists" in stderr:
                print(f"[~] Skipped (already exists)")
                logger.info("Resource already exists, skipping")
                return True
            elif "permission denied" in stderr or "permission" in stderr:
                print(f"[!] Permission denied: {stderr}")
                logger.error(f"Permission denied: {stderr}")
                return False
            else:
                print(f"[!] Failed: {stderr}")
                logger.error(f"Command failed: {stderr}")
                return False
        else:
            print("[+] Success")
            logger.info("Command succeeded")
            return True

    def export_to_file(self, cmd: List[str], output_path: Path) -> None:
        """
        Execute a gcloud command and write JSON output to file.

        Args:
            cmd: Command arguments (without 'gcloud' prefix)
            output_path: Path to output file

        Raises:
            SystemExit: If command fails
        """
        self.activate_service_account()

        full_cmd = [
            self.gcloud_bin
        ] + cmd + [
            "--format=json",
            f"--project={self.config.project_id}"
        ]

        logger.debug(f"Exporting to {output_path}: {' '.join(full_cmd)}")
        print(f"[+] Exporting {output_path.name}")

        with open(output_path, "w", encoding="utf-8") as f:
            result = subprocess.run(full_cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"[!] Export failed: {result.stderr.strip()}")
            sys.exit(1)

    # Convenience methods for common operations

    def list_composite_indexes(self) -> List[Dict[str, Any]]:
        """List all composite indexes."""
        return self.run_command(["firestore", "indexes", "composite", "list"], capture_json=True)

    def list_field_indexes(self) -> List[Dict[str, Any]]:
        """List all single-field indexes."""
        return self.run_command(["firestore", "indexes", "fields", "list"], capture_json=True)

    def list_ttl_policies(self) -> List[Dict[str, Any]]:
        """List all TTL policies."""
        return self.run_command(["firestore", "fields", "ttls", "list"], capture_json=True)
