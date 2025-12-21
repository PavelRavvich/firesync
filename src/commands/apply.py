#!/usr/bin/env python3
"""Apply local Firestore schema to remote GCP project."""

import sys
from typing import Callable, List, Dict, Any
from pathlib import Path

from cli import parse_apply_args, setup_client
from gcloud import GCloudClient
from operations import (
    CompositeIndexOperations,
    FieldIndexOperations,
    TTLPolicyOperations,
)
from schema import SchemaFile, load_schema_file
from workspace import load_config
from ui import confirm_apply, calculate_changes
from logger import setup_logging

# Configure logging based on environment variables
logger = setup_logging()


def apply_resources(
    client: GCloudClient,
    resources: List[Dict[str, Any]],
    build_command: Callable[[Dict[str, Any]], List[str]],
    resource_type: str
) -> int:
    """
    Apply resources to Firestore with error handling.

    Args:
        client: GCloud client
        resources: List of resource definitions
        build_command: Function to build gcloud command from resource
        resource_type: Resource type name for logging

    Returns:
        Number of successfully applied resources
    """
    success_count = 0
    for resource in resources:
        try:
            cmd = build_command(resource)
            if client.run_command_tolerant(cmd):
                success_count += 1
        except (ValueError, Exception) as e:
            print(f"[!] Skipping invalid {resource_type}: {e}")
            logger.warning(f"Invalid {resource_type}: {e}")
    return success_count


def collect_all_diffs(client: GCloudClient, schema_dir: Path) -> Dict[str, int]:
    """
    Collect all differences between local and remote schemas.

    Args:
        client: GCloud client configured for target environment
        schema_dir: Path to schema directory

    Returns:
        Dictionary with counts of create/delete/update operations
    """
    total_changes = {"create": 0, "delete": 0, "update": 0}

    # Composite Indexes
    try:
        local_composite = load_schema_file(schema_dir / SchemaFile.COMPOSITE_INDEXES)
        remote_composite = client.list_composite_indexes()
        diff = CompositeIndexOperations.compare(local_composite, remote_composite)
        changes = calculate_changes(diff)
        for key in total_changes:
            total_changes[key] += changes.get(key, 0)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Error comparing composite indexes: {e}")

    # Field Indexes
    try:
        local_fields = load_schema_file(schema_dir / SchemaFile.FIELD_INDEXES)
        remote_fields = client.list_field_indexes()
        diff = FieldIndexOperations.compare(local_fields, remote_fields)
        changes = calculate_changes(diff)
        for key in total_changes:
            total_changes[key] += changes.get(key, 0)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Error comparing field indexes: {e}")

    # TTL Policies
    try:
        local_ttl = load_schema_file(schema_dir / SchemaFile.TTL_POLICIES)
        remote_ttl = client.list_ttl_policies()
        diff = TTLPolicyOperations.compare(local_ttl, remote_ttl)
        changes = calculate_changes(diff)
        for key in total_changes:
            total_changes[key] += changes.get(key, 0)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Error comparing TTL policies: {e}")

    return total_changes


def apply_schema_from_directory(client: GCloudClient, schema_dir: Path):
    """
    Apply all schemas from a directory to Firestore.

    Args:
        client: GCloud client configured for target environment
        schema_dir: Path to schema directory
    """
    # Apply Composite Indexes
    print("\n🔹 Applying Composite Indexes")
    try:
        local_composite = load_schema_file(schema_dir / SchemaFile.COMPOSITE_INDEXES)

        if not isinstance(local_composite, list):
            raise ValueError("Expected a list in composite-indexes.json")

        success_count = apply_resources(
            client,
            local_composite,
            CompositeIndexOperations.build_create_command,
            "composite index"
        )
        print(f"[~] Processed {success_count}/{len(local_composite)} composite indexes")

    except FileNotFoundError:
        print("[!] Local composite-indexes.json not found, skipping")
    except Exception as e:
        print(f"[!] Error applying composite indexes: {e}")
        logger.exception("Failed to apply composite indexes")

    # Apply Single-Field Indexes
    print("\n🔹 Applying Single-Field Indexes")
    try:
        local_fields = load_schema_file(schema_dir / SchemaFile.FIELD_INDEXES)

        if not isinstance(local_fields, list):
            raise ValueError("Expected a list in field-indexes.json")

        success_count = 0
        total_count = 0

        for entry in local_fields:
            collection = entry.get("collectionGroupId")
            field_path = entry.get("fieldPath")
            idx_configs = entry.get("indexes", [])

            if not collection or not field_path:
                print(f"[!] Skipping invalid field index entry: {entry}")
                continue

            for cfg in idx_configs:
                value = cfg.get("order") or cfg.get("arrayConfig")
                if not value:
                    continue

                total_count += 1
                try:
                    cmd = FieldIndexOperations.build_create_command(
                        collection, field_path, value.lower()
                    )
                    if client.run_command_tolerant(cmd):
                        success_count += 1
                except Exception as e:
                    print(f"[!] Failed to create field index: {e}")
                    logger.warning(f"Failed to create field index: {e}")

        print(f"[~] Processed {success_count}/{total_count} field indexes")

    except FileNotFoundError:
        print("[!] Local field-indexes.json not found, skipping")
    except Exception as e:
        print(f"[!] Error applying single-field indexes: {e}")
        logger.exception("Failed to apply field indexes")

    # Apply TTL Policies
    print("\n🔹 Applying TTL Policies")
    try:
        local_ttl = load_schema_file(schema_dir / SchemaFile.TTL_POLICIES)

        if not isinstance(local_ttl, list):
            raise ValueError("Expected a list in ttl-policies.json")

        success_count = apply_resources(
            client,
            local_ttl,
            TTLPolicyOperations.build_create_command,
            "TTL policy"
        )
        print(f"[~] Processed {success_count}/{len(local_ttl)} TTL policies")

    except FileNotFoundError:
        print("[!] Local ttl-policies.json not found, skipping")
    except Exception as e:
        print(f"[!] Error applying TTL: {e}")
        logger.exception("Failed to apply TTL policies")


def main():
    """Main entry point for firestore_apply command."""
    args = parse_apply_args("Apply local Firestore schema to remote GCP project")

    # Check if migration mode (--env-from and --env-to)
    if args.env_from and args.env_to:
        # Migration mode: apply source schema to target environment
        try:
            workspace_config = load_config()
        except FileNotFoundError as e:
            print(f"[!] {e}")
            sys.exit(1)

        # Get source schema directory
        source_schema_dir = workspace_config.get_schema_dir(args.env_from)

        print(f"\n🚀 Migration: {args.env_from} → {args.env_to}")
        print(f"   Source schema: {source_schema_dir}")

        # Set up client for target environment
        _, target_client = setup_client(env=args.env_to)

        # Collect changes for confirmation
        changes = collect_all_diffs(target_client, source_schema_dir)

        # Ask for confirmation
        auto_approve = getattr(args, 'auto_approve', False)
        if not confirm_apply(changes, target_client.config.project_id, args.env_to, auto_approve):
            print("[!] Operation cancelled")
            sys.exit(0)

        # Apply source schema to target environment
        apply_schema_from_directory(target_client, source_schema_dir)

        print(f"\n[+] Migration applied: {args.env_from} schema -> {args.env_to} Firestore")

    else:
        # Standard mode: apply local schema to remote
        config, client = setup_client(
            env=args.env,
            schema_dir=getattr(args, 'schema_dir', None)
        )

        # Collect changes for confirmation
        changes = collect_all_diffs(client, config.schema_dir)

        # Ask for confirmation
        auto_approve = getattr(args, 'auto_approve', False)
        if not confirm_apply(changes, config.project_id, args.env, auto_approve):
            print("[!] Operation cancelled")
            sys.exit(0)

        # Apply changes
        apply_schema_from_directory(client, config.schema_dir)

        print("\n✔️ Firestore schema applied.")


if __name__ == "__main__":
    main()
