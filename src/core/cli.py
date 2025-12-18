"""Common CLI utilities for FireSync commands."""

import argparse
import sys
from typing import Optional, Tuple

from core.config import FiresyncConfig
from core.gcloud import GCloudClient


def parse_common_args(description: str, include_schema_dir: bool = False) -> argparse.Namespace:
    """
    Parse common command-line arguments.

    Args:
        description: Command description
        include_schema_dir: Whether to include --schema-dir argument

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description=description)

    # Key authentication (mutually exclusive)
    key_group = parser.add_mutually_exclusive_group(required=True)
    key_group.add_argument(
        "--key-path",
        help="Path to GCP service account key file"
    )
    key_group.add_argument(
        "--key-env",
        help="Name of environment variable containing key JSON"
    )

    if include_schema_dir:
        parser.add_argument(
            "--schema-dir",
            default="firestore_schema",
            help="Directory with schema JSON files"
        )

    return parser.parse_args()


def setup_client(
    key_path: Optional[str] = None,
    key_env: Optional[str] = None,
    schema_dir: str = "firestore_schema"
) -> Tuple[FiresyncConfig, GCloudClient]:
    """
    Set up configuration and GCloud client.

    Args:
        key_path: Path to GCP service account key file
        key_env: Name of environment variable with key JSON
        schema_dir: Schema directory path

    Returns:
        Tuple of (config, client)
    """
    config = FiresyncConfig.from_args(key_path=key_path, key_env=key_env, schema_dir=schema_dir)
    config.display_info()
    client = GCloudClient(config)
    return config, client
