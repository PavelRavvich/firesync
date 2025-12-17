"""Unit tests for firesync.config module."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import Environment, FiresyncConfig


class TestEnvironment(unittest.TestCase):
    """Tests for Environment enum."""

    def test_from_string_valid(self):
        """Test converting valid strings to Environment."""
        self.assertEqual(Environment.from_string("dev"), Environment.DEV)
        self.assertEqual(Environment.from_string("staging"), Environment.STAGING)
        self.assertEqual(Environment.from_string("production"), Environment.PRODUCTION)
        self.assertEqual(Environment.from_string("DEV"), Environment.DEV)

    def test_from_string_invalid(self):
        """Test error on invalid environment string."""
        with self.assertRaises(ValueError) as ctx:
            Environment.from_string("invalid")
        self.assertIn("Invalid environment", str(ctx.exception))


class TestFiresyncConfig(unittest.TestCase):
    """Tests for FiresyncConfig class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_key_data = {
            "project_id": "test-project-123",
            "client_email": "test@test-project-123.iam.gserviceaccount.com"
        }

    def test_from_args_missing_env(self):
        """Test error when environment is not provided."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit):
                FiresyncConfig.from_args(env=None)

    def test_from_args_invalid_env(self):
        """Test error when environment is invalid."""
        with self.assertRaises(SystemExit):
            FiresyncConfig.from_args(env="invalid")

    @patch("pathlib.Path.exists")
    def test_from_args_missing_key_file(self, mock_exists):
        """Test error when key file doesn't exist."""
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            FiresyncConfig.from_args(env="dev")

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    def test_from_args_invalid_json(self, mock_exists, mock_read_text):
        """Test error when key file has invalid JSON."""
        mock_exists.return_value = True
        mock_read_text.return_value = "invalid json"
        with self.assertRaises(SystemExit):
            FiresyncConfig.from_args(env="dev")

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    def test_from_args_missing_fields(self, mock_exists, mock_read_text):
        """Test error when key file is missing required fields."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps({"project_id": "test"})
        with self.assertRaises(SystemExit):
            FiresyncConfig.from_args(env="dev")

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    def test_from_args_success(self, mock_exists, mock_read_text):
        """Test successful config creation."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps(self.test_key_data)

        config = FiresyncConfig.from_args(env="dev")

        self.assertEqual(config.env, Environment.DEV)
        self.assertEqual(config.project_id, "test-project-123")
        self.assertEqual(config.service_account, "test@test-project-123.iam.gserviceaccount.com")
        self.assertTrue(str(config.key_path).endswith("secrets/gcp-key-dev.json"))
        self.assertTrue(str(config.schema_dir).endswith("firestore_schema"))

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    def test_from_args_custom_schema_dir(self, mock_exists, mock_read_text):
        """Test config with custom schema directory."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps(self.test_key_data)

        config = FiresyncConfig.from_args(env="staging", schema_dir="custom_schema")

        self.assertEqual(config.env, Environment.STAGING)
        self.assertTrue(str(config.schema_dir).endswith("custom_schema"))

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    @patch.dict("os.environ", {"ENV": "production"})
    def test_from_args_env_variable(self, mock_exists, mock_read_text):
        """Test config using ENV environment variable."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps(self.test_key_data)

        config = FiresyncConfig.from_args(env=None)

        self.assertEqual(config.env, Environment.PRODUCTION)

    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_display_info(self, mock_print, mock_exists, mock_read_text):
        """Test display_info prints configuration."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps(self.test_key_data)

        config = FiresyncConfig.from_args(env="dev")
        config.display_info()

        # Check that print was called with expected information
        self.assertTrue(mock_print.called)
        calls_str = " ".join(str(call) for call in mock_print.call_args_list)
        self.assertIn("dev", calls_str)
        self.assertIn("test-project-123", calls_str)


if __name__ == "__main__":
    unittest.main()
