"""Unit tests for firesync.commands.apply module."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from firesync.commands.apply import apply_resources, apply_schema_from_directory
from firesync.schema import SchemaFile


class TestApplyResources(unittest.TestCase):
    """Tests for apply_resources function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_build_command = MagicMock()

    def test_apply_resources_success(self):
        """Test successful application of resources."""
        resources = [
            {"name": "resource1"},
            {"name": "resource2"},
            {"name": "resource3"}
        ]
        self.mock_build_command.return_value = ["gcloud", "command"]
        self.mock_client.run_command_tolerant.return_value = True

        count = apply_resources(
            self.mock_client,
            resources,
            self.mock_build_command,
            "test resource"
        )

        self.assertEqual(count, 3)
        self.assertEqual(self.mock_build_command.call_count, 3)
        self.assertEqual(self.mock_client.run_command_tolerant.call_count, 3)

    def test_apply_resources_partial_success(self):
        """Test partial success when some resources fail."""
        resources = [
            {"name": "resource1"},
            {"name": "resource2"},
            {"name": "resource3"}
        ]
        self.mock_build_command.return_value = ["gcloud", "command"]
        # First succeeds, second fails, third succeeds
        self.mock_client.run_command_tolerant.side_effect = [True, False, True]

        count = apply_resources(
            self.mock_client,
            resources,
            self.mock_build_command,
            "test resource"
        )

        self.assertEqual(count, 2)
        self.assertEqual(self.mock_build_command.call_count, 3)

    def test_apply_resources_build_command_error(self):
        """Test handling of build_command errors."""
        resources = [
            {"name": "resource1"},
            {"name": "invalid"},
            {"name": "resource3"}
        ]

        def build_cmd(resource):
            if resource["name"] == "invalid":
                raise ValueError("Invalid resource")
            return ["gcloud", "command"]

        self.mock_build_command.side_effect = build_cmd
        self.mock_client.run_command_tolerant.return_value = True

        with patch('builtins.print'):  # Suppress print output
            count = apply_resources(
                self.mock_client,
                resources,
                self.mock_build_command,
                "test resource"
            )

        self.assertEqual(count, 2)
        self.assertEqual(self.mock_build_command.call_count, 3)
        self.assertEqual(self.mock_client.run_command_tolerant.call_count, 2)

    def test_apply_resources_empty_list(self):
        """Test applying empty resource list."""
        count = apply_resources(
            self.mock_client,
            [],
            self.mock_build_command,
            "test resource"
        )

        self.assertEqual(count, 0)
        self.mock_build_command.assert_not_called()
        self.mock_client.run_command_tolerant.assert_not_called()


class TestApplyFieldIndexes(unittest.TestCase):
    """Tests for field index application with various formats."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_client.run_command_tolerant.return_value = True

    def _create_schema_dir(self, tmpdir, field_indexes):
        """Helper to create schema directory with field indexes."""
        schema_dir = Path(tmpdir) / "schema"
        schema_dir.mkdir(parents=True)

        # Create minimal composite indexes and ttl policies (empty)
        (schema_dir / SchemaFile.COMPOSITE_INDEXES).write_text("[]")
        (schema_dir / SchemaFile.TTL_POLICIES).write_text("[]")

        # Create field indexes file
        (schema_dir / SchemaFile.FIELD_INDEXES).write_text(
            json.dumps(field_indexes, indent=2)
        )

        return schema_dir

    def test_apply_normalized_format(self):
        """Test applying field indexes in normalized format."""
        field_indexes = [
            {
                "collectionGroupId": "users",
                "fieldPath": "email",
                "indexes": [{"order": "ASCENDING"}]
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = self._create_schema_dir(tmpdir, field_indexes)

            with patch('builtins.print'):
                apply_schema_from_directory(self.mock_client, schema_dir)

            # Verify field index command was called
            calls = self.mock_client.run_command_tolerant.call_args_list
            field_index_calls = [
                c for c in calls
                if c[0][0] and "indexes" in c[0][0] and "fields" in c[0][0]
            ]
            self.assertEqual(len(field_index_calls), 1)

    def test_apply_raw_gcp_format(self):
        """Test applying field indexes in raw GCP format with name path."""
        field_indexes = [
            {
                "name": "projects/test/databases/(default)/collectionGroups/articles/fields/title",
                "indexConfig": {
                    "indexes": [
                        {"order": "ASCENDING"},
                        {"order": "DESCENDING"}
                    ]
                }
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = self._create_schema_dir(tmpdir, field_indexes)

            with patch('builtins.print'):
                apply_schema_from_directory(self.mock_client, schema_dir)

            # Verify field index commands were called (2 indexes)
            calls = self.mock_client.run_command_tolerant.call_args_list
            field_index_calls = [
                c for c in calls
                if c[0][0] and "indexes" in c[0][0] and "fields" in c[0][0]
            ]
            self.assertEqual(len(field_index_calls), 2)

    def test_skip_system_default_entries(self):
        """Test that __default__ collection entries are skipped."""
        field_indexes = [
            {
                "name": "projects/test/databases/(default)/collectionGroups/__default__/fields/*",
                "indexConfig": {
                    "indexes": [
                        {"fields": [{"fieldPath": "*", "order": "ASCENDING"}], "queryScope": "COLLECTION"},
                        {"fields": [{"fieldPath": "*", "order": "DESCENDING"}], "queryScope": "COLLECTION"}
                    ]
                }
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = self._create_schema_dir(tmpdir, field_indexes)

            with patch('builtins.print'):
                apply_schema_from_directory(self.mock_client, schema_dir)

            # Verify NO field index commands were called
            calls = self.mock_client.run_command_tolerant.call_args_list
            field_index_calls = [
                c for c in calls
                if c[0][0] and "indexes" in c[0][0] and "fields" in c[0][0]
            ]
            self.assertEqual(len(field_index_calls), 0)

    def test_apply_mixed_formats(self):
        """Test applying mix of normalized and raw GCP formats."""
        field_indexes = [
            # System default - should be skipped
            {
                "name": "projects/test/databases/(default)/collectionGroups/__default__/fields/*",
                "indexConfig": {
                    "indexes": [{"order": "ASCENDING"}]
                }
            },
            # Raw GCP format - should be applied
            {
                "name": "projects/test/databases/(default)/collectionGroups/orders/fields/status",
                "indexConfig": {
                    "indexes": [{"order": "ASCENDING"}]
                }
            },
            # Normalized format - should be applied
            {
                "collectionGroupId": "users",
                "fieldPath": "createdAt",
                "indexes": [{"order": "DESCENDING"}]
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = self._create_schema_dir(tmpdir, field_indexes)

            with patch('builtins.print'):
                apply_schema_from_directory(self.mock_client, schema_dir)

            # Verify 2 field index commands were called (skipping __default__)
            calls = self.mock_client.run_command_tolerant.call_args_list
            field_index_calls = [
                c for c in calls
                if c[0][0] and "indexes" in c[0][0] and "fields" in c[0][0]
            ]
            self.assertEqual(len(field_index_calls), 2)

    def test_apply_raw_gcp_nested_fields_format(self):
        """Test applying raw GCP format with nested fields structure."""
        field_indexes = [
            {
                "name": "projects/test/databases/(default)/collectionGroups/products/fields/price",
                "indexConfig": {
                    "indexes": [
                        {
                            "fields": [{"fieldPath": "*", "order": "ASCENDING"}],
                            "queryScope": "COLLECTION",
                            "state": "READY"
                        }
                    ]
                }
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_dir = self._create_schema_dir(tmpdir, field_indexes)

            with patch('builtins.print'):
                apply_schema_from_directory(self.mock_client, schema_dir)

            # Verify field index command was called
            calls = self.mock_client.run_command_tolerant.call_args_list
            field_index_calls = [
                c for c in calls
                if c[0][0] and "indexes" in c[0][0] and "fields" in c[0][0]
            ]
            self.assertEqual(len(field_index_calls), 1)


if __name__ == "__main__":
    unittest.main()
