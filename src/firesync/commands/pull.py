#!/usr/bin/env python3
"""Export Firestore schema from GCP to local JSON files."""

import logging
import sys

from firesync.cli import parse_pull_args, setup_client
from firesync.schema import SchemaFile, ensure_schema_dir
from firesync.workspace import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def pull_single_environment(env_name):
    """Pull schema for a single environment."""
    config, client = setup_client(env=env_name)

    # Ensure schema directory exists
    ensure_schema_dir(config.schema_dir)

    # Export all schema files
    print()
    client.export_to_file(
        ["firestore", "indexes", "composite", "list"],
        config.schema_dir / SchemaFile.COMPOSITE_INDEXES
    )
    client.export_to_file(
        ["firestore", "indexes", "fields", "list"],
        config.schema_dir / SchemaFile.FIELD_INDEXES
    )
    client.export_to_file(
        ["firestore", "fields", "ttls", "list"],
        config.schema_dir / SchemaFile.TTL_POLICIES
    )

    print(f"[+] Firestore schema exported to: {config.schema_dir}")
    return True


def main():
    """Main entry point for firesync pull command."""
    args = parse_pull_args("Export Firestore schema from GCP to local JSON files")

    # Handle --all mode
    if getattr(args, 'all', False):
        try:
            workspace_config = load_config()
        except FileNotFoundError as e:
            print(f"[!] {e}")
            sys.exit(1)

        if not workspace_config.environments:
            print("[!] No environments configured in workspace")
            print("    Run 'firesync env add <name> --key-path=<path>' to add an environment")
            sys.exit(1)

        env_count = len(workspace_config.environments)
        print(f"\nPulling schemas from {env_count} environment(s)...\n")

        success_count = 0
        failed_envs = []

        for idx, env_name in enumerate(workspace_config.environments.keys(), 1):
            print(f"[{idx}/{env_count}] Pulling environment: {env_name}")
            print("-" * 60)
            try:
                pull_single_environment(env_name)
                success_count += 1
            except Exception as e:
                print(f"[!] Failed to pull {env_name}: {e}")
                logger.exception(f"Failed to pull environment {env_name}")
                failed_envs.append(env_name)
            print()

        # Summary
        print("=" * 60)
        print(f"\n[+] Successfully pulled {success_count}/{env_count} environment(s)")
        if failed_envs:
            print(f"[!] Failed environments: {', '.join(failed_envs)}")
            sys.exit(1)

    else:
        # Single environment pull
        pull_single_environment(args.env)


if __name__ == "__main__":
    main()
