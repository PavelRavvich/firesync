#!/usr/bin/env python3
"""Compare local Firestore schema against remote state."""

import logging
from typing import Callable, List, Any, Dict
from pathlib import Path

from core.cli import parse_common_args, setup_client
from core.gcloud import GCloudClient
from core.operations import (
    CompositeIndexOperations,
    FieldIndexOperations,
    TTLPolicyOperations,
)
from core.schema import SchemaFile, load_schema_file

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
    print(f"\n🔍 Comparing {resource_name}")
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


def main():
    """Main entry point for firestore_plan command."""
    args = parse_common_args(
        "Compare local Firestore schema against remote state",
        include_schema_dir=True
    )
    config, client = setup_client(key_path=args.key_path, key_env=args.key_env, schema_dir=args.schema_dir)

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
    def format_ttl(item):
        if len(item) == 3:  # create/delete
            return f"TTL: ({item[0]}, {item[1]}) => {item[2]}"
        else:  # update
            return f"TTL: ({item[0]}, {item[1]}) {item[2]} -> {item[3]}"

    compare_and_display(
        "TTL Policies",
        config.schema_dir / SchemaFile.TTL_POLICIES,
        client.list_ttl_policies,
        TTLPolicyOperations.compare,
        format_ttl
    )

    print("\n✔️ Plan complete.")


if __name__ == "__main__":
    main()
