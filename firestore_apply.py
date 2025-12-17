#!/usr/bin/env python3
"""Apply local Firestore schema to remote GCP project."""

import logging
from typing import Callable, List, Dict, Any

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


def main():
    """Main entry point for firestore_apply command."""
    args = parse_common_args(
        "Apply local Firestore schema to remote GCP project",
        include_schema_dir=True
    )
    config, client = setup_client(env=args.env, schema_dir=args.schema_dir)

    # Apply Composite Indexes
    print("\n🔹 Applying Composite Indexes")
    try:
        local_composite = load_schema_file(config.schema_dir / SchemaFile.COMPOSITE_INDEXES)

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
        local_fields = load_schema_file(config.schema_dir / SchemaFile.FIELD_INDEXES)

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
        local_ttl = load_schema_file(config.schema_dir / SchemaFile.TTL_POLICIES)

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

    print("\n✔️ Firestore schema applied.")


if __name__ == "__main__":
    main()
