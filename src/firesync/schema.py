"""Schema file loading and validation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SchemaFile:
    """Schema file types supported by FireSync."""

    COMPOSITE_INDEXES = "composite-indexes.json"
    FIELD_INDEXES = "field-indexes.json"
    TTL_POLICIES = "ttl-policies.json"

    @classmethod
    def all_files(cls) -> List[str]:
        """Return list of all schema file names."""
        return [
            cls.COMPOSITE_INDEXES,
            cls.FIELD_INDEXES,
            cls.TTL_POLICIES
        ]


def load_schema_file(path: Path) -> List[Dict[str, Any]]:
    """
    Load and validate a schema JSON file.

    Args:
        path: Path to the JSON schema file

    Returns:
        List of schema objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid JSON or not a list
    """
    if not path.exists():
        logger.warning(f"Schema file not found: {path}")
        raise FileNotFoundError(f"Schema file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        raise ValueError(f"Invalid JSON in {path}: {e}")

    if not isinstance(data, list):
        logger.error(f"Expected list in {path}, got {type(data).__name__}")
        raise ValueError(f"Expected list in {path}, got {type(data).__name__}")

    logger.debug(f"Loaded {len(data)} items from {path}")
    return data


def save_schema_file(path: Path, data: List[Dict[str, Any]]) -> None:
    """
    Save schema data to JSON file.

    Args:
        path: Path to the output JSON file
        data: List of schema objects to save

    Raises:
        ValueError: If data is not a list
        OSError: If file cannot be written
    """
    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")
        logger.debug(f"Saved {len(data)} items to {path}")
    except OSError as e:
        logger.error(f"Failed to write {path}: {e}")
        raise


def ensure_schema_dir(schema_dir: Path) -> None:
    """
    Ensure schema directory exists.

    Args:
        schema_dir: Path to schema directory

    Raises:
        OSError: If directory cannot be created
    """
    try:
        schema_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Schema directory ready: {schema_dir}")
    except OSError as e:
        logger.error(f"Failed to create schema directory {schema_dir}: {e}")
        raise


def validate_composite_index(index: Dict[str, Any]) -> bool:
    """
    Validate composite index structure.

    Args:
        index: Composite index dictionary

    Returns:
        True if valid, False otherwise
    """
    # Must have collection identifier
    has_collection = bool(
        index.get("collectionGroup") or
        index.get("collectionGroupId") or
        "/collectionGroups/" in index.get("name", "")
    )

    # Must have fields
    fields = index.get("fields", [])
    has_fields = isinstance(fields, list) and len(fields) > 0

    # Each field must have fieldPath and order/arrayConfig
    valid_fields = all(
        isinstance(f, dict) and
        "fieldPath" in f and
        ("order" in f or "arrayConfig" in f)
        for f in fields
    )

    is_valid = has_collection and has_fields and valid_fields

    if not is_valid:
        logger.warning(f"Invalid composite index: {index}")

    return is_valid


def validate_field_index(index: Dict[str, Any]) -> bool:
    """
    Validate field index structure.

    Supports both normalized format (collectionGroupId, fieldPath, indexes)
    and raw GCP format (name path, indexConfig.indexes).

    Args:
        index: Field index dictionary

    Returns:
        True if valid, False otherwise
    """
    # Check for collection identifier (direct field or in name path)
    has_collection = bool(
        index.get("collectionGroupId") or
        "/collectionGroups/" in index.get("name", "")
    )

    # Check for field path (direct field or in name path)
    has_field_path = bool(
        index.get("fieldPath") or
        "/fields/" in index.get("name", "")
    )

    # Check for indexes (direct or nested in indexConfig)
    indexes = index.get("indexes") or index.get("indexConfig", {}).get("indexes", [])
    has_indexes = isinstance(indexes, list) and len(indexes) > 0

    is_valid = has_collection and has_field_path and has_indexes

    if not is_valid:
        logger.warning(f"Invalid field index: {index}")

    return is_valid


def validate_ttl_policy(policy: Dict[str, Any]) -> bool:
    """
    Validate TTL policy structure.

    Args:
        policy: TTL policy dictionary

    Returns:
        True if valid, False otherwise
    """
    # Must have collection identifier
    has_collection = bool(
        policy.get("collectionGroup") or
        policy.get("collectionGroupId") or
        "/collectionGroups/" in policy.get("name", "")
    )

    # Must have field identifier
    has_field = bool(
        policy.get("field") or
        "/fields/" in policy.get("name", "")
    )

    # Must have ttlConfig with state
    ttl_config = policy.get("ttlConfig", {})
    has_state = bool(ttl_config.get("state") or policy.get("state"))

    is_valid = has_collection and has_field and has_state

    if not is_valid:
        logger.warning(f"Invalid TTL policy: {policy}")

    return is_valid
