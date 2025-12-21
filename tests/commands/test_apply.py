"""Unit tests for commands.apply module."""

import unittest
from unittest.mock import MagicMock, patch

from firesync.commands import apply as firestore_apply


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

        count = firestore_apply.apply_resources(
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

        count = firestore_apply.apply_resources(
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
            count = firestore_apply.apply_resources(
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
        count = firestore_apply.apply_resources(
            self.mock_client,
            [],
            self.mock_build_command,
            "test resource"
        )

        self.assertEqual(count, 0)
        self.mock_build_command.assert_not_called()
        self.mock_client.run_command_tolerant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
