"""Unit tests for firesync.normalizers module."""

import unittest

from firesync.normalizers import (
    normalize_collection_name,
    normalize_field_config,
    normalize_field_path,
    normalize_fields,
    normalize_index_value,
    normalize_query_scope,
    normalize_ttl_period,
    normalize_ttl_state,
)


class TestNormalizeCollectionName(unittest.TestCase):
    """Tests for normalize_collection_name function."""

    def test_from_collection_group(self):
        """Test extraction from collectionGroup field."""
        item = {"collectionGroup": "users"}
        self.assertEqual(normalize_collection_name(item), "users")

    def test_from_collection_group_id(self):
        """Test extraction from collectionGroupId field."""
        item = {"collectionGroupId": "orders"}
        self.assertEqual(normalize_collection_name(item), "orders")

    def test_from_resource_name(self):
        """Test extraction from resource name path."""
        item = {"name": "projects/test/databases/(default)/collectionGroups/products/indexes/1"}
        self.assertEqual(normalize_collection_name(item), "products")

    def test_prefers_direct_field(self):
        """Test that direct field is preferred over name parsing."""
        item = {
            "collectionGroup": "users",
            "name": "projects/test/databases/(default)/collectionGroups/orders/indexes/1"
        }
        self.assertEqual(normalize_collection_name(item), "users")

    def test_missing_collection(self):
        """Test handling of missing collection."""
        item = {"name": "projects/test/databases/(default)"}
        self.assertIsNone(normalize_collection_name(item))

    def test_empty_dict(self):
        """Test handling of empty dictionary."""
        self.assertIsNone(normalize_collection_name({}))


class TestNormalizeFieldPath(unittest.TestCase):
    """Tests for normalize_field_path function."""

    def test_from_field_path(self):
        """Test extraction from fieldPath field."""
        item = {"fieldPath": "createdAt"}
        self.assertEqual(normalize_field_path(item), "createdAt")

    def test_from_field(self):
        """Test extraction from field field."""
        item = {"field": "updatedAt"}
        self.assertEqual(normalize_field_path(item), "updatedAt")

    def test_from_resource_name(self):
        """Test extraction from resource name path."""
        item = {"name": "projects/test/databases/(default)/collectionGroups/users/fields/timestamp"}
        self.assertEqual(normalize_field_path(item), "timestamp")

    def test_prefers_direct_field(self):
        """Test that direct field is preferred over name parsing."""
        item = {
            "fieldPath": "name",
            "name": "projects/test/databases/(default)/collectionGroups/users/fields/email"
        }
        self.assertEqual(normalize_field_path(item), "name")

    def test_missing_field(self):
        """Test handling of missing field."""
        item = {"name": "projects/test"}
        self.assertIsNone(normalize_field_path(item))


class TestNormalizeFieldConfig(unittest.TestCase):
    """Tests for normalize_field_config function."""

    def test_with_order(self):
        """Test normalization with order field."""
        field = {"fieldPath": "name", "order": "ASCENDING"}
        self.assertEqual(normalize_field_config(field), "name:ascending")

    def test_with_array_config(self):
        """Test normalization with arrayConfig field."""
        field = {"fieldPath": "tags", "arrayConfig": "CONTAINS"}
        self.assertEqual(normalize_field_config(field), "tags:contains")

    def test_lowercase_conversion(self):
        """Test that values are lowercased."""
        field = {"fieldPath": "status", "order": "DESCENDING"}
        self.assertEqual(normalize_field_config(field), "status:descending")

    def test_missing_value(self):
        """Test handling of missing order/arrayConfig."""
        field = {"fieldPath": "name"}
        self.assertEqual(normalize_field_config(field), "name:")


class TestNormalizeFields(unittest.TestCase):
    """Tests for normalize_fields function."""

    def test_single_field(self):
        """Test normalization of single field."""
        fields = [{"fieldPath": "name", "order": "ASCENDING"}]
        self.assertEqual(normalize_fields(fields), ["name:ascending"])

    def test_multiple_fields(self):
        """Test normalization and sorting of multiple fields."""
        fields = [
            {"fieldPath": "name", "order": "ASCENDING"},
            {"fieldPath": "age", "order": "DESCENDING"}
        ]
        result = normalize_fields(fields)
        self.assertEqual(result, ["age:descending", "name:ascending"])

    def test_empty_list(self):
        """Test handling of empty list."""
        self.assertEqual(normalize_fields([]), [])


class TestNormalizeIndexValue(unittest.TestCase):
    """Tests for normalize_index_value function."""

    def test_with_order(self):
        """Test extraction of order value."""
        config = {"order": "ASCENDING"}
        self.assertEqual(normalize_index_value(config), "ascending")

    def test_with_array_config(self):
        """Test extraction of arrayConfig value."""
        config = {"arrayConfig": "CONTAINS"}
        self.assertEqual(normalize_index_value(config), "contains")

    def test_missing_value(self):
        """Test handling of missing value."""
        config = {}
        self.assertIsNone(normalize_index_value(config))


class TestNormalizeQueryScope(unittest.TestCase):
    """Tests for normalize_query_scope function."""

    def test_lowercase_input(self):
        """Test normalization of lowercase input."""
        self.assertEqual(normalize_query_scope("collection"), "COLLECTION")

    def test_uppercase_input(self):
        """Test normalization of uppercase input."""
        self.assertEqual(normalize_query_scope("COLLECTION_GROUP"), "COLLECTION_GROUP")

    def test_none_input(self):
        """Test default value for None input."""
        self.assertEqual(normalize_query_scope(None), "COLLECTION")

    def test_empty_string(self):
        """Test default value for empty string."""
        self.assertEqual(normalize_query_scope(""), "COLLECTION")


class TestNormalizeTTLPeriod(unittest.TestCase):
    """Tests for normalize_ttl_period function."""

    def test_direct_field(self):
        """Test extraction from ttlPeriod field."""
        item = {"ttlPeriod": "86400s"}
        self.assertEqual(normalize_ttl_period(item), "86400s")

    def test_nested_in_ttl_config(self):
        """Test extraction from nested ttlConfig."""
        item = {"ttlConfig": {"ttlPeriod": "3600s"}}
        self.assertEqual(normalize_ttl_period(item), "3600s")

    def test_missing_period(self):
        """Test handling of missing period."""
        item = {}
        self.assertEqual(normalize_ttl_period(item), "")


class TestNormalizeTTLState(unittest.TestCase):
    """Tests for normalize_ttl_state function."""

    def test_direct_field(self):
        """Test extraction from state field."""
        item = {"state": "active"}
        self.assertEqual(normalize_ttl_state(item), "ACTIVE")

    def test_nested_in_ttl_config(self):
        """Test extraction from nested ttlConfig."""
        item = {"ttlConfig": {"state": "creating"}}
        self.assertEqual(normalize_ttl_state(item), "CREATING")

    def test_uppercase_conversion(self):
        """Test that state is uppercased."""
        item = {"state": "pending"}
        self.assertEqual(normalize_ttl_state(item), "PENDING")

    def test_missing_state(self):
        """Test handling of missing state."""
        item = {}
        self.assertIsNone(normalize_ttl_state(item))


if __name__ == "__main__":
    unittest.main()
