"""Unit tests for firesync.schema module."""

import json
import tempfile
import unittest
from pathlib import Path

from firesync.schema import (
    SchemaFile,
    ensure_schema_dir,
    load_schema_file,
    save_schema_file,
    validate_composite_index,
    validate_field_index,
    validate_ttl_policy,
)


class TestSchemaFile(unittest.TestCase):
    """Tests for SchemaFile class."""

    def test_all_files(self):
        """Test that all_files returns expected file names."""
        files = SchemaFile.all_files()
        self.assertEqual(len(files), 3)
        self.assertIn("composite-indexes.json", files)
        self.assertIn("field-indexes.json", files)
        self.assertIn("ttl-policies.json", files)


class TestLoadSchemaFile(unittest.TestCase):
    """Tests for load_schema_file function."""

    def test_load_valid_file(self):
        """Test loading valid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            data = [{"field": "value"}]
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            result = load_schema_file(temp_path)
            self.assertEqual(result, data)
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test error when file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            load_schema_file(Path("/nonexistent/file.json"))

    def test_load_invalid_json(self):
        """Test error when file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError) as ctx:
                load_schema_file(temp_path)
            self.assertIn("Invalid JSON", str(ctx.exception))
        finally:
            temp_path.unlink()

    def test_load_non_list_json(self):
        """Test error when JSON is not a list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError) as ctx:
                load_schema_file(temp_path)
            self.assertIn("Expected list", str(ctx.exception))
        finally:
            temp_path.unlink()


class TestSaveSchemaFile(unittest.TestCase):
    """Tests for save_schema_file function."""

    def test_save_valid_data(self):
        """Test saving valid data to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "test.json"
            data = [{"field": "value"}]

            save_schema_file(temp_path, data)

            self.assertTrue(temp_path.exists())
            loaded = json.loads(temp_path.read_text())
            self.assertEqual(loaded, data)

    def test_save_creates_parent_dirs(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "nested" / "dir" / "test.json"
            data = []

            save_schema_file(temp_path, data)

            self.assertTrue(temp_path.exists())

    def test_save_non_list_raises_error(self):
        """Test error when data is not a list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "test.json"

            with self.assertRaises(ValueError) as ctx:
                save_schema_file(temp_path, {"key": "value"})
            self.assertIn("Expected list", str(ctx.exception))


class TestEnsureSchemaDir(unittest.TestCase):
    """Tests for ensure_schema_dir function."""

    def test_creates_directory(self):
        """Test that directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = Path(tmpdir) / "schema"

            ensure_schema_dir(schema_dir)

            self.assertTrue(schema_dir.exists())
            self.assertTrue(schema_dir.is_dir())

    def test_existing_directory(self):
        """Test that existing directory is not modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = Path(tmpdir)

            ensure_schema_dir(schema_dir)

            self.assertTrue(schema_dir.exists())


class TestValidateCompositeIndex(unittest.TestCase):
    """Tests for validate_composite_index function."""

    def test_valid_index(self):
        """Test validation of valid composite index."""
        index = {
            "collectionGroup": "users",
            "queryScope": "COLLECTION",
            "fields": [
                {"fieldPath": "name", "order": "ASCENDING"},
                {"fieldPath": "age", "order": "DESCENDING"}
            ]
        }
        self.assertTrue(validate_composite_index(index))

    def test_valid_index_with_collection_group_id(self):
        """Test validation with collectionGroupId field."""
        index = {
            "collectionGroupId": "orders",
            "fields": [{"fieldPath": "total", "order": "ASCENDING"}]
        }
        self.assertTrue(validate_composite_index(index))

    def test_valid_index_with_name(self):
        """Test validation with name field."""
        index = {
            "name": "projects/test/collectionGroups/products/indexes/1",
            "fields": [{"fieldPath": "price", "order": "DESCENDING"}]
        }
        self.assertTrue(validate_composite_index(index))

    def test_missing_collection(self):
        """Test validation fails without collection."""
        index = {
            "fields": [{"fieldPath": "name", "order": "ASCENDING"}]
        }
        self.assertFalse(validate_composite_index(index))

    def test_missing_fields(self):
        """Test validation fails without fields."""
        index = {"collectionGroup": "users"}
        self.assertFalse(validate_composite_index(index))

    def test_empty_fields(self):
        """Test validation fails with empty fields."""
        index = {"collectionGroup": "users", "fields": []}
        self.assertFalse(validate_composite_index(index))

    def test_invalid_field(self):
        """Test validation fails with invalid field."""
        index = {
            "collectionGroup": "users",
            "fields": [{"fieldPath": "name"}]  # Missing order/arrayConfig
        }
        self.assertFalse(validate_composite_index(index))


class TestValidateFieldIndex(unittest.TestCase):
    """Tests for validate_field_index function."""

    def test_valid_index(self):
        """Test validation of valid field index."""
        index = {
            "collectionGroupId": "users",
            "fieldPath": "email",
            "indexes": [{"order": "ASCENDING"}]
        }
        self.assertTrue(validate_field_index(index))

    def test_missing_collection(self):
        """Test validation fails without collection."""
        index = {
            "fieldPath": "email",
            "indexes": [{"order": "ASCENDING"}]
        }
        self.assertFalse(validate_field_index(index))

    def test_missing_field_path(self):
        """Test validation fails without fieldPath."""
        index = {
            "collectionGroupId": "users",
            "indexes": [{"order": "ASCENDING"}]
        }
        self.assertFalse(validate_field_index(index))

    def test_missing_indexes(self):
        """Test validation fails without indexes."""
        index = {
            "collectionGroupId": "users",
            "fieldPath": "email"
        }
        self.assertFalse(validate_field_index(index))

    def test_empty_indexes(self):
        """Test validation fails with empty indexes."""
        index = {
            "collectionGroupId": "users",
            "fieldPath": "email",
            "indexes": []
        }
        self.assertFalse(validate_field_index(index))

    def test_valid_raw_gcp_format(self):
        """Test validation of raw GCP format with name path and indexConfig."""
        index = {
            "name": "projects/test/databases/(default)/collectionGroups/articles/fields/description",
            "indexConfig": {
                "indexes": [
                    {"fields": [{"fieldPath": "*", "order": "ASCENDING"}], "queryScope": "COLLECTION"}
                ]
            }
        }
        self.assertTrue(validate_field_index(index))

    def test_valid_raw_gcp_format_empty_indexes(self):
        """Test validation of raw GCP format with disabled indexing (empty indexes)."""
        index = {
            "name": "projects/test/databases/(default)/collectionGroups/articles/fields/content",
            "indexConfig": {
                "indexes": [{"order": "ASCENDING"}]
            }
        }
        self.assertTrue(validate_field_index(index))

    def test_raw_gcp_format_missing_indexes(self):
        """Test validation fails for raw GCP format without indexes."""
        index = {
            "name": "projects/test/databases/(default)/collectionGroups/articles/fields/title",
            "indexConfig": {}
        }
        self.assertFalse(validate_field_index(index))


class TestValidateTTLPolicy(unittest.TestCase):
    """Tests for validate_ttl_policy function."""

    def test_valid_policy(self):
        """Test validation of valid TTL policy."""
        policy = {
            "collectionGroup": "sessions",
            "field": "expiresAt",
            "ttlConfig": {"state": "ACTIVE"}
        }
        self.assertTrue(validate_ttl_policy(policy))

    def test_valid_policy_with_name(self):
        """Test validation with name field."""
        policy = {
            "name": "projects/test/collectionGroups/logs/fields/timestamp",
            "ttlConfig": {"state": "ACTIVE"}
        }
        self.assertTrue(validate_ttl_policy(policy))

    def test_valid_policy_with_state(self):
        """Test validation with direct state field."""
        policy = {
            "collectionGroup": "temp",
            "field": "createdAt",
            "state": "ACTIVE"
        }
        self.assertTrue(validate_ttl_policy(policy))

    def test_missing_collection(self):
        """Test validation fails without collection."""
        policy = {
            "field": "expiresAt",
            "ttlConfig": {"state": "ACTIVE"}
        }
        self.assertFalse(validate_ttl_policy(policy))

    def test_missing_field(self):
        """Test validation fails without field."""
        policy = {
            "collectionGroup": "sessions",
            "ttlConfig": {"state": "ACTIVE"}
        }
        self.assertFalse(validate_ttl_policy(policy))

    def test_missing_state(self):
        """Test validation fails without state."""
        policy = {
            "collectionGroup": "sessions",
            "field": "expiresAt",
            "ttlConfig": {}
        }
        self.assertFalse(validate_ttl_policy(policy))


if __name__ == "__main__":
    unittest.main()
