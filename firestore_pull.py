#!/usr/bin/env python3
"""Export Firestore schema from GCP to local JSON files."""

import logging

from core.cli import parse_common_args, setup_client
from core.schema import SchemaFile, ensure_schema_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for firestore_pull command."""
    args = parse_common_args("Export Firestore schema from GCP to local JSON files")
    config, client = setup_client(key_path=args.key_path)

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

    print(f"\n✔️ Firestore schema exported to: {config.schema_dir}")


if __name__ == "__main__":
    main()
