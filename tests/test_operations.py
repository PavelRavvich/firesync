"""Unit tests for firesync.operations module."""

import unittest

from firesync.operations import (
    CompositeIndexOperations,
    FieldIndexOperations,
    TTLPolicyOperations,
)


class TestCompositeIndexOperations(unittest.TestCase):
    """Tests for CompositeIndexOperations class."""

    def test_normalize(self):
        """Test normalization of composite index."""
        index = {
            "collectionGroup": "users",
            "queryScope": "COLLECTION",
            "fields": [
                {"fieldPath": "name", "order": "ASCENDING"},
                {"fieldPath": "age", "order": "DESCENDING"}
            ]
        }
        result = CompositeIndexOperations.normalize(index)
        self.assertEqual(result[0], "users")
        self.assertEqual(result[1], "COLLECTION")
        self.assertIn("age:descending", result[2])
        self.assertIn("name:ascending", result[2])

    def test_compare_create(self):
        """Test comparison detects indexes to create."""
        local = [{
            "collectionGroup": "orders",
            "queryScope": "COLLECTION",
            "fields": [{"fieldPath": "total", "order": "ASCENDING"}]
        }]
        remote = []

        diff = CompositeIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)
        self.assertEqual(len(diff["delete"]), 0)

    def test_compare_delete(self):
        """Test comparison detects indexes to delete."""
        local = []
        remote = [{
            "collectionGroup": "products",
            "queryScope": "COLLECTION",
            "fields": [{"fieldPath": "price", "order": "DESCENDING"}]
        }]

        diff = CompositeIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 0)
        self.assertEqual(len(diff["delete"]), 1)

    def test_compare_no_changes(self):
        """Test comparison detects no changes."""
        index = {
            "collectionGroup": "users",
            "queryScope": "COLLECTION",
            "fields": [{"fieldPath": "name", "order": "ASCENDING"}]
        }

        diff = CompositeIndexOperations.compare([index], [index])

        self.assertEqual(len(diff["create"]), 0)
        self.assertEqual(len(diff["delete"]), 0)

    def test_compare_skips_invalid(self):
        """Test comparison skips invalid indexes."""
        local = [
            {"collectionGroup": "valid", "fields": [{"fieldPath": "x", "order": "ASCENDING"}]},
            {"collectionGroup": "invalid"}  # Missing fields
        ]
        remote = []

        diff = CompositeIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)

    def test_build_create_command(self):
        """Test building gcloud command."""
        index = {
            "collectionGroup": "orders",
            "queryScope": "COLLECTION_GROUP",
            "fields": [
                {"fieldPath": "status", "order": "ASCENDING"},
                {"fieldPath": "createdAt", "order": "DESCENDING"}
            ]
        }

        cmd = CompositeIndexOperations.build_create_command(index)

        self.assertIn("firestore", cmd)
        self.assertIn("indexes", cmd)
        self.assertIn("composite", cmd)
        self.assertIn("create", cmd)
        self.assertIn("--collection-group=orders", cmd)
        self.assertIn("--query-scope=COLLECTION_GROUP", cmd)

        # Check field configs
        field_configs = [arg for arg in cmd if arg.startswith("--field-config=")]
        self.assertEqual(len(field_configs), 2)

    def test_build_create_command_missing_collection(self):
        """Test error when collection is missing."""
        index = {
            "fields": [{"fieldPath": "name", "order": "ASCENDING"}]
        }

        with self.assertRaises(ValueError):
            CompositeIndexOperations.build_create_command(index)

    def test_build_create_command_missing_fields(self):
        """Test error when fields are missing."""
        index = {"collectionGroup": "users"}

        with self.assertRaises(ValueError):
            CompositeIndexOperations.build_create_command(index)


class TestFieldIndexOperations(unittest.TestCase):
    """Tests for FieldIndexOperations class."""

    def test_compare_create(self):
        """Test comparison detects field indexes to create."""
        local = [{
            "collectionGroupId": "users",
            "fieldPath": "email",
            "indexes": [{"order": "ASCENDING"}]
        }]
        remote = []

        diff = FieldIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)
        self.assertEqual(diff["create"][0], ("users", "email", "ascending"))
        self.assertEqual(len(diff["delete"]), 0)

    def test_compare_delete(self):
        """Test comparison detects field indexes to delete."""
        local = []
        remote = [{
            "collectionGroup": "products",
            "fieldPath": "name",
            "name": "projects/x/collectionGroups/products/fields/name",
            "indexes": [{"order": "DESCENDING"}]
        }]

        diff = FieldIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 0)
        self.assertEqual(len(diff["delete"]), 1)

    def test_compare_update(self):
        """Test comparison detects field index updates."""
        local = [{
            "collectionGroupId": "orders",
            "fieldPath": "total",
            "indexes": [{"order": "ASCENDING"}, {"order": "DESCENDING"}]
        }]
        remote = [{
            "collectionGroup": "orders",
            "fieldPath": "total",
            "name": "projects/x/collectionGroups/orders/fields/total",
            "indexes": [{"order": "ASCENDING"}]
        }]

        diff = FieldIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)
        self.assertEqual(diff["create"][0], ("orders", "total", "descending"))
        self.assertEqual(len(diff["delete"]), 0)

    def test_compare_skips_invalid(self):
        """Test comparison skips invalid indexes."""
        local = [
            {"collectionGroupId": "valid", "fieldPath": "x", "indexes": [{"order": "ASCENDING"}]},
            {"fieldPath": "invalid"}  # Missing collection
        ]
        remote = []

        diff = FieldIndexOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)

    def test_build_create_command_order(self):
        """Test building command with order index."""
        cmd = FieldIndexOperations.build_create_command("users", "email", "ascending")

        self.assertIn("firestore", cmd)
        self.assertIn("indexes", cmd)
        self.assertIn("fields", cmd)
        self.assertIn("update", cmd)
        self.assertIn("email", cmd)
        self.assertIn("--collection-group=users", cmd)
        self.assertIn("--index=order=ascending", cmd)

    def test_build_create_command_array_config(self):
        """Test building command with array-config index."""
        cmd = FieldIndexOperations.build_create_command("posts", "tags", "contains")

        self.assertIn("--index=array-config=contains", cmd)


class TestTTLPolicyOperations(unittest.TestCase):
    """Tests for TTLPolicyOperations class."""

    def test_compare_create(self):
        """Test comparison detects TTL policies to create."""
        local = [{
            "collectionGroup": "sessions",
            "field": "expiresAt",
            "ttlConfig": {"ttlPeriod": "86400s", "state": "ACTIVE"}
        }]
        remote = []

        diff = TTLPolicyOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)
        self.assertEqual(diff["create"][0], ("sessions", "expiresAt", "86400s"))
        self.assertEqual(len(diff["delete"]), 0)

    def test_compare_delete(self):
        """Test comparison detects TTL policies to delete."""
        local = []
        remote = [{
            "collectionGroup": "temp",
            "field": "createdAt",
            "ttlPeriod": "3600s"
        }]

        diff = TTLPolicyOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 0)
        self.assertEqual(len(diff["delete"]), 1)

    def test_compare_update(self):
        """Test comparison detects TTL policy updates."""
        local = [{
            "collectionGroup": "logs",
            "field": "timestamp",
            "ttlConfig": {"ttlPeriod": "604800s", "state": "ACTIVE"}
        }]
        remote = [{
            "collectionGroup": "logs",
            "field": "timestamp",
            "ttlPeriod": "86400s"
        }]

        diff = TTLPolicyOperations.compare(local, remote)

        self.assertEqual(len(diff["update"]), 1)
        self.assertEqual(diff["update"][0], ("logs", "timestamp", "86400s", "604800s"))

    def test_compare_skips_invalid(self):
        """Test comparison skips invalid policies."""
        local = [
            {"collectionGroup": "valid", "field": "x", "ttlConfig": {"state": "ACTIVE"}},
            {"collectionGroup": "invalid"}  # Missing field
        ]
        remote = []

        diff = TTLPolicyOperations.compare(local, remote)

        self.assertEqual(len(diff["create"]), 1)

    def test_build_create_command_active(self):
        """Test building command with active TTL."""
        policy = {
            "collectionGroup": "sessions",
            "field": "expiresAt",
            "ttlConfig": {"state": "ACTIVE"}
        }

        cmd = TTLPolicyOperations.build_create_command(policy)

        self.assertIn("firestore", cmd)
        self.assertIn("fields", cmd)
        self.assertIn("ttls", cmd)
        self.assertIn("update", cmd)
        self.assertIn("expiresAt", cmd)
        self.assertIn("--collection-group=sessions", cmd)
        self.assertIn("--enable-ttl", cmd)

    def test_build_create_command_inactive(self):
        """Test building command with inactive TTL."""
        policy = {
            "collectionGroup": "temp",
            "field": "createdAt",
            "ttlConfig": {"state": "DISABLED"}
        }

        cmd = TTLPolicyOperations.build_create_command(policy)

        self.assertIn("--disable-ttl", cmd)

    def test_build_create_command_missing_collection(self):
        """Test error when collection is missing."""
        policy = {
            "field": "expiresAt",
            "ttlConfig": {"state": "ACTIVE"}
        }

        with self.assertRaises(ValueError):
            TTLPolicyOperations.build_create_command(policy)


if __name__ == "__main__":
    unittest.main()
