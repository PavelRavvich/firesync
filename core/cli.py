"""Common CLI utilities for FireSync commands."""

import argparse
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
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "production"],
        help="Target environment"
    )

    if include_schema_dir:
        parser.add_argument(
            "--schema-dir",
            default="firestore_schema",
            help="Directory with schema JSON files"
        )

    return parser.parse_args()


def setup_client(
    env: Optional[str] = None,
    schema_dir: str = "firestore_schema"
) -> Tuple[FiresyncConfig, GCloudClient]:
    """
    Set up configuration and GCloud client.

    Args:
        env: Environment name
        schema_dir: Schema directory path

    Returns:
        Tuple of (config, client)
    """
    config = FiresyncConfig.from_args(env=env, schema_dir=schema_dir)
    config.display_info()
    client = GCloudClient(config)
    return config, client
