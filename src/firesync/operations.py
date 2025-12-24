"""Resource-specific operations for Firestore schema management."""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from firesync.normalizers import (
    normalize_collection_name,
    normalize_field_path,
    normalize_fields,
    normalize_index_value,
    normalize_query_scope,
    normalize_ttl_period,
    normalize_ttl_state,
)
from firesync.schema import (
    validate_composite_index,
    validate_field_index,
    validate_ttl_policy,
)

logger = logging.getLogger(__name__)


class CompositeIndexOperations:
    """Operations for composite indexes."""

    @staticmethod
    def normalize(index: Dict[str, Any]) -> Tuple[str, str, Tuple[str, ...]]:
        """
        Normalize composite index to comparable tuple.

        Args:
            index: Composite index dictionary

        Returns:
            Tuple of (collection, query_scope, fields_tuple)
        """
        collection = normalize_collection_name(index) or ""
        query_scope = normalize_query_scope(index.get("queryScope"))
        fields = tuple(normalize_fields(index.get("fields", [])))
        return (collection, query_scope, fields)

    @staticmethod
    def compare(
        local: List[Dict[str, Any]],
        remote: List[Dict[str, Any]]
    ) -> Dict[str, Set[Tuple]]:
        """
        Compare local and remote composite indexes.

        Args:
            local: Local composite indexes
            remote: Remote composite indexes

        Returns:
            Dictionary with 'create', 'delete', 'update' sets
        """
        local_set = set()
        for idx in local:
            if validate_composite_index(idx):
                local_set.add(CompositeIndexOperations.normalize(idx))

        remote_set = set()
        for idx in remote:
            remote_set.add(CompositeIndexOperations.normalize(idx))

        return {
            "create": local_set - remote_set,
            "delete": remote_set - local_set,
            "update": set()  # Composite indexes don't support updates
        }

    @staticmethod
    def build_create_command(index: Dict[str, Any]) -> List[str]:
        """
        Build gcloud command to create composite index.

        Args:
            index: Composite index dictionary

        Returns:
            Command arguments list (without 'gcloud' prefix)
        """
        collection = normalize_collection_name(index)
        if not collection:
            raise ValueError(f"Cannot extract collection name from: {index}")

        query_scope = normalize_query_scope(index.get("queryScope"))
        fields = index.get("fields", [])

        if not fields:
            raise ValueError(f"No fields in composite index: {index}")

        cmd = [
            "firestore", "indexes", "composite", "create",
            f"--collection-group={collection}",
            f"--query-scope={query_scope}"
        ]

        for field in fields:
            if "fieldPath" in field and ("order" in field or "arrayConfig" in field):
                field_config = f"field-path={field['fieldPath']}"

                if "order" in field:
                    field_config += f",order={field['order'].lower()}"
                elif "arrayConfig" in field:
                    field_config += f",array-config={field['arrayConfig'].lower()}"

                cmd.append(f"--field-config={field_config}")

        return cmd


class FieldIndexOperations:
    """Operations for single-field indexes."""

    @staticmethod
    def compare(
        local: List[Dict[str, Any]],
        remote: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare local and remote field indexes.

        Args:
            local: Local field indexes
            remote: Remote field indexes

        Returns:
            Dictionary with 'create' and 'delete' lists of (collection, field, value) tuples
        """
        remote_map = defaultdict(set)
        for entry in remote:
            if "/fields/" not in entry.get("name", ""):
                continue

            collection = normalize_collection_name(entry)
            field_path = normalize_field_path(entry)

            if not collection or not field_path:
                continue

            for idx_config in entry.get("indexes", []):
                value = normalize_index_value(idx_config)
                if value:
                    remote_map[(collection, field_path)].add(value)

        local_map = defaultdict(set)
        for entry in local:
            if not validate_field_index(entry):
                continue

            collection = entry.get("collectionGroupId")
            field_path = entry.get("fieldPath")

            if not collection or not field_path:
                continue

            for idx_config in entry.get("indexes", []):
                value = normalize_index_value(idx_config)
                if value:
                    local_map[(collection, field_path)].add(value)

        create_list = []
        delete_list = []

        # Find indexes to create
        for key in local_map.keys() - remote_map.keys():
            for value in local_map[key]:
                create_list.append((*key, value))

        # Find indexes to delete
        for key in remote_map.keys() - local_map.keys():
            for value in remote_map[key]:
                delete_list.append((*key, value))

        # Find differences in common keys
        for key in local_map.keys() & remote_map.keys():
            for value in local_map[key] - remote_map[key]:
                create_list.append((*key, value))
            for value in remote_map[key] - local_map[key]:
                delete_list.append((*key, value))

        return {
            "create": create_list,
            "delete": delete_list
        }

    @staticmethod
    def build_create_command(
        collection: str,
        field_path: str,
        index_value: str
    ) -> List[str]:
        """
        Build gcloud command to create field index.

        Args:
            collection: Collection group name
            field_path: Field path
            index_value: Index value (e.g., 'ascending', 'contains')

        Returns:
            Command arguments list (without 'gcloud' prefix)
        """
        # Determine if it's order or array-config
        if index_value in {"ascending", "descending"}:
            index_param = f"order={index_value}"
        elif index_value in {"contains"}:
            index_param = f"array-config={index_value}"
        else:
            # Default to order
            index_param = f"order={index_value}"

        return [
            "firestore", "indexes", "fields", "update",
            field_path,
            f"--collection-group={collection}",
            f"--index={index_param}"
        ]


class TTLPolicyOperations:
    """Operations for TTL policies."""

    @staticmethod
    def compare(
        local: List[Dict[str, Any]],
        remote: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare local and remote TTL policies.

        Args:
            local: Local TTL policies
            remote: Remote TTL policies

        Returns:
            Dictionary with 'create', 'delete', 'update' lists of tuples
        """
        remote_map = {}
        for entry in remote:
            collection = normalize_collection_name(entry)
            field = normalize_field_path(entry)

            if not collection or not field:
                continue

            ttl_period = normalize_ttl_period(entry)
            remote_map[(collection, field)] = ttl_period

        local_map = {}
        for entry in local:
            if not validate_ttl_policy(entry):
                continue

            collection = normalize_collection_name(entry)
            field = normalize_field_path(entry)

            if not collection or not field:
                continue

            ttl_period = normalize_ttl_period(entry)
            local_map[(collection, field)] = ttl_period

        create_list = []
        delete_list = []
        update_list = []

        # Find policies to create
        for key in local_map.keys() - remote_map.keys():
            create_list.append((*key, local_map[key]))

        # Find policies to delete
        for key in remote_map.keys() - local_map.keys():
            delete_list.append((*key, remote_map[key]))

        # Find policies to update
        for key in local_map.keys() & remote_map.keys():
            if local_map[key] != remote_map[key]:
                update_list.append((*key, remote_map[key], local_map[key]))

        return {
            "create": create_list,
            "delete": delete_list,
            "update": update_list
        }

    @staticmethod
    def build_create_command(policy: Dict[str, Any]) -> List[str]:
        """
        Build gcloud command to create/update TTL policy.

        Args:
            policy: TTL policy dictionary

        Returns:
            Command arguments list (without 'gcloud' prefix)
        """
        collection = normalize_collection_name(policy)
        field = normalize_field_path(policy)

        if not collection or not field:
            raise ValueError(f"Cannot extract collection/field from: {policy}")

        ttl_state = normalize_ttl_state(policy)
        enable_flag = "--enable-ttl" if ttl_state == "ACTIVE" else "--disable-ttl"

        return [
            "firestore", "fields", "ttls", "update",
            field,
            f"--collection-group={collection}",
            enable_flag
        ]
