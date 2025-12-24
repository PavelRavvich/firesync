#!/usr/bin/env python3
"""Compare local Firestore schema against remote state."""

import logging
import sys
from typing import Callable, List, Any, Dict
from pathlib import Path

from firesync.cli import parse_plan_args, setup_client
from firesync.operations import (
    CompositeIndexOperations,
    FieldIndexOperations,
    TTLPolicyOperations,
)
from firesync.schema import SchemaFile, load_schema_file
from firesync.workspace import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def compare_and_display(
    resource_name: str,
    schema_file: Path,
    fetch_remote: Callable[[], List[Dict[str, Any]]],
    compare_func: Callable[[List, List], Dict],
    format_func: Callable[[Any], str]
) -> None:
    """
    Compare local and remote resources and display differences.

    Args:
        resource_name: Display name for the resource type
        schema_file: Path to local schema file
        fetch_remote: Function to fetch remote resources
        compare_func: Function to compare local vs remote
        format_func: Function to format diff items for display
    """
    print(f"\n[~] Comparing {resource_name}")
    try:
        remote = fetch_remote()
        local = load_schema_file(schema_file)
        diff = compare_func(local, remote)

        for item in diff.get("create", []):
            print(f"[+] WILL CREATE: {format_func(item)}")
        for item in diff.get("delete", []):
            print(f"[-] WILL DELETE: {format_func(item)}")
        for item in diff.get("update", []):
            print(f"[~] WILL UPDATE: {format_func(item)}")

        if not any(diff.get(key, []) for key in ["create", "delete", "update"]):
            print("[~] No changes")

    except FileNotFoundError:
        print(f"[!] Local {schema_file.name} not found")
    except Exception as e:
        print(f"[!] {resource_name} compare failed: {e}")
        logger.exception(f"{resource_name} comparison failed")


def compare_local_schemas(
    resource_name: str,
    source_schema_file: Path,
    target_schema_file: Path,
    compare_func: Callable[[List, List], Dict],
    format_func: Callable[[Any], str]
) -> None:
    """
    Compare two local schema files (migration mode).

    Args:
        resource_name: Display name for the resource type
        source_schema_file: Path to source environment schema
        target_schema_file: Path to target environment schema
        compare_func: Function to compare schemas
        format_func: Function to format diff items for display
    """
    print(f"\n[~] Comparing {resource_name}")
    try:
        source = load_schema_file(source_schema_file)
        target = load_schema_file(target_schema_file)
        diff = compare_func(source, target)

        for item in diff.get("create", []):
            print(f"[+] WILL CREATE: {format_func(item)}")
        for item in diff.get("delete", []):
            print(f"[-] WILL DELETE: {format_func(item)}")
        for item in diff.get("update", []):
            print(f"[~] WILL UPDATE: {format_func(item)}")

        if not any(diff.get(key, []) for key in ["create", "delete", "update"]):
            print("[~] No changes")

    except FileNotFoundError as e:
        print(f"[!] Schema file not found: {e}")
    except Exception as e:
        print(f"[!] {resource_name} compare failed: {e}")
        logger.exception(f"{resource_name} comparison failed")


def main():
    """Main entry point for firesync plan command."""
    args = parse_plan_args("Compare local Firestore schema against remote state")

    # Check if migration mode (--env-from and --env-to)
    if args.env_from and args.env_to:
        # Migration mode: compare two local schemas
        try:
            workspace_config = load_config()
        except FileNotFoundError as e:
            print(f"[!] {e}")
            sys.exit(1)

        # Get schema directories for both environments
        source_schema_dir = workspace_config.get_schema_dir(args.env_from)
        target_schema_dir = workspace_config.get_schema_dir(args.env_to)

        print(f"\nMigration Plan: {args.env_from} -> {args.env_to}")
        print(f"   Source: {source_schema_dir}")
        print(f"   Target: {target_schema_dir}")

        # Format functions
        def format_ttl(item):
            if len(item) == 3:  # create/delete
                return f"TTL: ({item[0]}, {item[1]}) => {item[2]}"
            else:  # update
                return f"TTL: ({item[0]}, {item[1]}) {item[2]} -> {item[3]}"

        # Compare Composite Indexes
        compare_local_schemas(
            "Composite Indexes",
            source_schema_dir / SchemaFile.COMPOSITE_INDEXES,
            target_schema_dir / SchemaFile.COMPOSITE_INDEXES,
            CompositeIndexOperations.compare,
            lambda item: f"{item[0]} {item[1]} {' | '.join(item[2])}"
        )

        # Compare Single-Field Indexes
        compare_local_schemas(
            "Single-Field Indexes",
            source_schema_dir / SchemaFile.FIELD_INDEXES,
            target_schema_dir / SchemaFile.FIELD_INDEXES,
            FieldIndexOperations.compare,
            lambda item: f"FIELD INDEX: ({item[0]}, {item[1]}) => {item[2]}"
        )

        # Compare TTL Policies
        compare_local_schemas(
            "TTL Policies",
            source_schema_dir / SchemaFile.TTL_POLICIES,
            target_schema_dir / SchemaFile.TTL_POLICIES,
            TTLPolicyOperations.compare,
            format_ttl
        )

        print("\n[+] Migration plan complete.")

    else:
        # Standard mode: compare local vs remote
        config, client = setup_client(
            env=args.env,
            schema_dir=getattr(args, 'schema_dir', None)
        )

        # Format functions
        def format_ttl(item):
            if len(item) == 3:  # create/delete
                return f"TTL: ({item[0]}, {item[1]}) => {item[2]}"
            else:  # update
                return f"TTL: ({item[0]}, {item[1]}) {item[2]} -> {item[3]}"

        # Compare Composite Indexes
        compare_and_display(
            "Composite Indexes",
            config.schema_dir / SchemaFile.COMPOSITE_INDEXES,
            client.list_composite_indexes,
            CompositeIndexOperations.compare,
            lambda item: f"{item[0]} {item[1]} {' | '.join(item[2])}"
        )

        # Compare Single-Field Indexes
        compare_and_display(
            "Single-Field Indexes",
            config.schema_dir / SchemaFile.FIELD_INDEXES,
            client.list_field_indexes,
            FieldIndexOperations.compare,
            lambda item: f"FIELD INDEX: ({item[0]}, {item[1]}) => {item[2]}"
        )

        # Compare TTL Policies
        compare_and_display(
            "TTL Policies",
            config.schema_dir / SchemaFile.TTL_POLICIES,
            client.list_ttl_policies,
            TTLPolicyOperations.compare,
            format_ttl
        )

        print("\n[+] Plan complete.")


if __name__ == "__main__":
    main()
