#!/usr/bin/env python3
"""Apply local Firestore schema to remote GCP project."""

import logging
import sys
from typing import Callable, List, Dict, Any

from firesync.cli import parse_apply_args, setup_client
from firesync.gcloud import GCloudClient
from firesync.normalizers import (
    normalize_collection_name,
    normalize_field_path,
    normalize_index_value,
)
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


def apply_schema_from_directory(client: GCloudClient, schema_dir):
    """
    Apply all schemas from a directory to Firestore.

    Args:
        client: GCloud client configured for target environment
        schema_dir: Path to schema directory
    """
    # Apply Composite Indexes
    print("\n[~] Applying Composite Indexes")
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
    print("\n[~] Applying Single-Field Indexes")
    try:
        local_fields = load_schema_file(schema_dir / SchemaFile.FIELD_INDEXES)

        if not isinstance(local_fields, list):
            raise ValueError("Expected a list in field-indexes.json")

        success_count = 0
        total_count = 0

        for entry in local_fields:
            # Use normalizers to handle both direct fields and GCP resource name paths
            collection = normalize_collection_name(entry)
            field_path = normalize_field_path(entry)

            # Get indexes from either direct field or nested indexConfig
            idx_configs = entry.get("indexes") or entry.get("indexConfig", {}).get("indexes", [])

            if not collection or not field_path:
                print(f"[!] Skipping invalid field index entry: {entry}")
                continue

            # Skip system default entries (wildcard field on __default__ collection)
            if collection == "__default__" or field_path == "*":
                logger.debug(f"Skipping system default field index: {collection}/{field_path}")
                continue

            for cfg in idx_configs:
                # Handle both flat config and nested fields structure
                # Flat: {"order": "ASCENDING"} or {"arrayConfig": "CONTAINS"}
                # Nested: {"fields": [{"fieldPath": "*", "order": "ASCENDING"}]}
                if "fields" in cfg:
                    # Nested structure from raw GCP format - extract value from first field
                    fields_list = cfg.get("fields", [])
                    if fields_list:
                        value = normalize_index_value(fields_list[0])
                    else:
                        value = None
                else:
                    value = normalize_index_value(cfg)

                if not value:
                    continue

                total_count += 1
                try:
                    cmd = FieldIndexOperations.build_create_command(
                        collection, field_path, value
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
    print("\n[~] Applying TTL Policies")
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
    """Main entry point for firesync apply command."""
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

        print(f"\nMigration: {args.env_from} -> {args.env_to}")
        print(f"   Source schema: {source_schema_dir}")

        # Set up client for target environment
        _, target_client = setup_client(env=args.env_to)

        # Apply source schema to target environment
        apply_schema_from_directory(target_client, source_schema_dir)

        print(f"\n[+] Migration applied: {args.env_from} schema -> {args.env_to} Firestore")

    else:
        # Standard mode: apply local schema to remote
        config, client = setup_client(
            env=args.env,
            schema_dir=getattr(args, 'schema_dir', None)
        )

        apply_schema_from_directory(client, config.schema_dir)

        print("\n[+] Firestore schema applied.")


if __name__ == "__main__":
    main()
