"""Common CLI utilities for FireSync commands."""

import argparse
from typing import Optional, Tuple

from .config import FiresyncConfig
from .gcloud import GCloudClient
from .workspace import load_config


def _validate_migration_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """
    Validate migration mode arguments.

    Args:
        parser: Argument parser for error reporting
        args: Parsed arguments

    Raises:
        SystemExit: If validation fails
    """
    migration_mode = args.from_env and args.to_env
    standard_mode = args.env

    if migration_mode and standard_mode:
        parser.error("Cannot use --from/--to with --env")

    if not migration_mode and not standard_mode:
        parser.error("Must specify either (--from and --to) or --env")

    if (args.from_env and not args.to_env) or (args.to_env and not args.from_env):
        parser.error("Both --from and --to must be specified for migration mode")


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
        "-a",
        action="store_true",
        help="Export schemas from all environments defined in config.yaml"
    )

    # Single environment
    auth_group.add_argument(
        "--env",
        "-e",
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
        "--from",
        metavar="SOURCE",
        dest="from_env",
        help="Source environment (migration mode: compare SOURCE local schema)"
    )
    parser.add_argument(
        "--to",
        metavar="TARGET",
        dest="to_env",
        help="Target environment (migration mode: compare against TARGET local schema)"
    )

    # Standard mode - single environment
    parser.add_argument(
        "--env",
        "-e",
        metavar="NAME",
        help="Compare local schema against remote Firestore (e.g., dev, staging, prod)"
    )

    # Schema directory override
    parser.add_argument(
        "--schema-dir",
        "-d",
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
    1. Migration mode: --from and --to (apply source schema to target env)
    2. Standard mode: --env (apply local schema to remote)

    Args:
        description: Command description

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description=description)

    # Environment migration mode
    parser.add_argument(
        "--from",
        metavar="SOURCE",
        dest="from_env",
        help="Source environment (migration mode: read SOURCE local schema, apply to TARGET remote)"
    )
    parser.add_argument(
        "--to",
        metavar="TARGET",
        dest="to_env",
        help="Target environment (migration mode: apply SOURCE schema to TARGET Firestore)"
    )

    # Standard mode - single environment
    parser.add_argument(
        "--env",
        "-e",
        metavar="NAME",
        help="Apply local schema to remote Firestore (e.g., dev, staging, prod)"
    )

    # Schema directory override
    parser.add_argument(
        "--schema-dir",
        "-d",
        metavar="PATH",
        help="Custom schema directory path (overrides workspace config)"
    )

    # Auto-approve flag (skip confirmation)
    parser.add_argument(
        "--auto-approve",
        "-y",
        action="store_true",
        help="Skip confirmation prompt (useful for CI/CD)"
    )

    # Dry-run flag (show commands without executing)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show gcloud commands that would be executed without running them"
    )

    args = parser.parse_args()
    _validate_migration_args(parser, args)
    return args


def setup_client(
    env: str,
    schema_dir: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[FiresyncConfig, GCloudClient]:
    """
    Set up configuration and GCloud client from workspace environment.

    Args:
        env: Environment name from workspace config
        schema_dir: Schema directory path (optional override)
        dry_run: If True, GCloudClient will show commands without executing

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
    if env_config.key_file:
        # Resolve key_file relative to config.yaml location
        resolved_key_file = workspace_config.config_dir / env_config.key_file
        actual_key_file = str(resolved_key_file)
        actual_key_env = None
    else:
        actual_key_file = None
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
        key_file=actual_key_file,
        key_env=actual_key_env,
        schema_dir=actual_schema_dir
    )

    config.display_info()
    client = GCloudClient(config, dry_run=dry_run)
    return config, client
