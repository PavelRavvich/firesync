"""Common CLI utilities for FireSync commands."""

import argparse
from typing import Optional, Tuple

from core.config import FiresyncConfig
from core.gcloud import GCloudClient
from core.workspace import load_config


def _validate_migration_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """
    Validate migration mode arguments.

    Args:
        parser: Argument parser for error reporting
        args: Parsed arguments

    Raises:
        SystemExit: If validation fails
    """
    migration_mode = args.env_from and args.env_to
    standard_mode = args.env

    if migration_mode and standard_mode:
        parser.error("Cannot use --env-from/--env-to with --env")

    if not migration_mode and not standard_mode:
        parser.error("Must specify either (--env-from and --env-to) or --env")

    if (args.env_from and not args.env_to) or (args.env_to and not args.env_from):
        parser.error("Both --env-from and --env-to must be specified for migration mode")


def parse_pull_args(description: str) -> argparse.Namespace:
    """
    Parse command-line arguments for pull command.

    Supports two modes:
    1. Pull all: --all (pulls all environments from config)
    2. Single environment: --env=<environment-name>

    Args:
        description: Command description

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description=description)

    # Authentication options (mutually exclusive groups)
    auth_group = parser.add_mutually_exclusive_group(required=True)

    # Pull all environments
    auth_group.add_argument(
        "--all",
        action="store_true",
        help="Export schemas from all environments defined in config.yaml"
    )

    # Single environment
    auth_group.add_argument(
        "--env",
        metavar="NAME",
        help="Export schema from specific environment (e.g., dev, staging, prod)"
    )

    return parser.parse_args()


def parse_plan_args(description: str) -> argparse.Namespace:
    """
    Parse command-line arguments for plan command.

    Supports two modes:
    1. Migration mode: --env-from and --env-to (compare two local schemas)
    2. Standard mode: --env (compare local vs remote)

    Args:
        description: Command description

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description=description)

    # Environment migration mode
    parser.add_argument(
        "--env-from",
        metavar="SOURCE",
        help="Source environment (migration mode: compare SOURCE local schema)"
    )
    parser.add_argument(
        "--env-to",
        metavar="TARGET",
        help="Target environment (migration mode: compare against TARGET local schema)"
    )

    # Standard mode - single environment
    parser.add_argument(
        "--env",
        metavar="NAME",
        help="Compare local schema against remote Firestore (e.g., dev, staging, prod)"
    )

    # Schema directory override
    parser.add_argument(
        "--schema-dir",
        metavar="PATH",
        help="Custom schema directory path (overrides workspace config)"
    )

    args = parser.parse_args()
    _validate_migration_args(parser, args)
    return args


def parse_apply_args(description: str) -> argparse.Namespace:
    """
    Parse command-line arguments for apply command.

    Supports two modes:
    1. Migration mode: --env-from and --env-to (apply source schema to target env)
    2. Standard mode: --env (apply local schema to remote)

    Args:
        description: Command description

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description=description)

    # Environment migration mode
    parser.add_argument(
        "--env-from",
        metavar="SOURCE",
        help="Source environment (migration mode: read SOURCE local schema, apply to TARGET remote)"
    )
    parser.add_argument(
        "--env-to",
        metavar="TARGET",
        help="Target environment (migration mode: apply SOURCE schema to TARGET Firestore)"
    )

    # Standard mode - single environment
    parser.add_argument(
        "--env",
        metavar="NAME",
        help="Apply local schema to remote Firestore (e.g., dev, staging, prod)"
    )

    # Schema directory override
    parser.add_argument(
        "--schema-dir",
        metavar="PATH",
        help="Custom schema directory path (overrides workspace config)"
    )

    args = parser.parse_args()
    _validate_migration_args(parser, args)
    return args


def setup_client(
    env: str,
    schema_dir: Optional[str] = None
) -> Tuple[FiresyncConfig, GCloudClient]:
    """
    Set up configuration and GCloud client from workspace environment.

    Args:
        env: Environment name from workspace config
        schema_dir: Schema directory path (optional override)

    Returns:
        Tuple of (config, client)

    Raises:
        FileNotFoundError: If workspace config not found
        ValueError: If environment not found in workspace config
    """
    # Load from config.yaml
    workspace_config = load_config()
    env_config = workspace_config.get_env(env)

    # Determine key parameters from environment config
    if env_config.key_path:
        # Resolve key_path relative to config.yaml location
        resolved_key_path = workspace_config.config_dir / env_config.key_path
        actual_key_path = str(resolved_key_path)
        actual_key_env = None
    else:
        actual_key_path = None
        actual_key_env = env_config.key_env

    # Determine schema_dir
    if schema_dir is None:
        # Use workspace schema directory for this environment
        actual_schema_dir = str(workspace_config.get_schema_dir(env))
    else:
        # User provided override
        actual_schema_dir = schema_dir

    # Create config
    config = FiresyncConfig.from_args(
        key_path=actual_key_path,
        key_env=actual_key_env,
        schema_dir=actual_schema_dir
    )

    config.display_info()
    client = GCloudClient(config)
    return config, client
