"""Normalization functions for Firestore schema comparison."""

from typing import Dict, List, Optional


def normalize_collection_name(item: Dict) -> Optional[str]:
    """
    Extract collection group name from various formats.

    Handles both direct fields (collectionGroup, collectionGroupId) and
    resource name paths.

    Args:
        item: Dictionary containing collection information

    Returns:
        Collection name or None if not found

    Examples:
        >>> normalize_collection_name({"collectionGroup": "users"})
        'users'
        >>> normalize_collection_name({"name": "projects/x/collectionGroups/orders/indexes/1"})
        'orders'
    """
    # Try direct fields first
    coll = item.get("collectionGroup") or item.get("collectionGroupId")
    if coll:
        return coll

    # Parse from resource name path
    name = item.get("name", "")
    if "/collectionGroups/" in name:
        parts = name.split("/collectionGroups/")
        if len(parts) > 1:
            return parts[1].split("/")[0]

    return None


def normalize_field_path(item: Dict) -> Optional[str]:
    """
    Extract field path from various formats.

    Args:
        item: Dictionary containing field information

    Returns:
        Field path or None if not found

    Examples:
        >>> normalize_field_path({"fieldPath": "createdAt"})
        'createdAt'
        >>> normalize_field_path({"name": "projects/x/collectionGroups/y/fields/timestamp"})
        'timestamp'
    """
    # Try direct field first
    field = item.get("fieldPath") or item.get("field")
    if field:
        return field

    # Parse from resource name path
    name = item.get("name", "")
    if "/fields/" in name:
        return name.split("/fields/")[-1]

    return None


def normalize_field_config(field: Dict) -> str:
    """
    Normalize a single field configuration for comparison.

    Args:
        field: Field configuration dictionary

    Returns:
        Normalized string representation: "fieldPath:order" or "fieldPath:arrayConfig"

    Examples:
        >>> normalize_field_config({"fieldPath": "name", "order": "ASCENDING"})
        'name:ascending'
        >>> normalize_field_config({"fieldPath": "tags", "arrayConfig": "CONTAINS"})
        'tags:contains'
    """
    path = field.get("fieldPath", "")
    value = field.get("order") or field.get("arrayConfig", "")
    return f"{path}:{value.lower()}"


def normalize_fields(fields: List[Dict]) -> List[str]:
    """
    Normalize a list of field configurations and sort them.

    Args:
        fields: List of field configuration dictionaries

    Returns:
        Sorted list of normalized field strings

    Examples:
        >>> normalize_fields([
        ...     {"fieldPath": "name", "order": "ASCENDING"},
        ...     {"fieldPath": "age", "order": "DESCENDING"}
        ... ])
        ['age:descending', 'name:ascending']
    """
    return sorted(normalize_field_config(f) for f in fields)


def normalize_index_value(config: Dict) -> Optional[str]:
    """
    Extract and normalize index value (order or arrayConfig).

    Args:
        config: Index configuration dictionary

    Returns:
        Normalized value (lowercase) or None if not found

    Examples:
        >>> normalize_index_value({"order": "ASCENDING"})
        'ascending'
        >>> normalize_index_value({"arrayConfig": "CONTAINS"})
        'contains'
    """
    value = config.get("order") or config.get("arrayConfig")
    return value.lower() if value else None


def normalize_query_scope(scope: Optional[str]) -> str:
    """
    Normalize query scope to uppercase with default value.

    Args:
        scope: Query scope string or None

    Returns:
        Normalized scope (default: "COLLECTION")

    Examples:
        >>> normalize_query_scope("collection")
        'COLLECTION'
        >>> normalize_query_scope(None)
        'COLLECTION'
    """
    if not scope:
        return "COLLECTION"
    return scope.upper()


def normalize_ttl_period(item: Dict) -> str:
    """
    Extract TTL period from various formats.

    Args:
        item: Dictionary containing TTL information

    Returns:
        TTL period string (may be empty)

    Examples:
        >>> normalize_ttl_period({"ttlPeriod": "86400s"})
        '86400s'
        >>> normalize_ttl_period({"ttlConfig": {"ttlPeriod": "3600s"}})
        '3600s'
    """
    # Direct field
    if "ttlPeriod" in item:
        return item["ttlPeriod"]

    # Nested in ttlConfig
    ttl_config = item.get("ttlConfig", {})
    return ttl_config.get("ttlPeriod", "")


def normalize_ttl_state(item: Dict) -> Optional[str]:
    """
    Extract TTL state from various formats.

    Args:
        item: Dictionary containing TTL information

    Returns:
        TTL state (uppercase) or None if not found

    Examples:
        >>> normalize_ttl_state({"state": "active"})
        'ACTIVE'
        >>> normalize_ttl_state({"ttlConfig": {"state": "creating"}})
        'CREATING'
    """
    # Direct field
    state = item.get("state")
    if state:
        return state.upper()

    # Nested in ttlConfig
    ttl_config = item.get("ttlConfig", {})
    state = ttl_config.get("state")
    return state.upper() if state else None
