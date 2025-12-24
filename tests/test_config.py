#!/usr/bin/env python3
"""Tests for firesync.config module."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from firesync.config import FiresyncConfig


class TestLoadKeyAutoDetect(unittest.TestCase):
    """Tests for _load_key auto-detection of JSON content vs file path."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_key_data = {
            "type": "service_account",
            "project_id": "test-project",
            "client_email": "test@test-project.iam.gserviceaccount.com"
        }
        self.test_key_json = json.dumps(self.test_key_data)

    def test_key_env_with_json_content(self):
        """Test that key_env with JSON content creates temp file."""
        with patch.dict(os.environ, {'GCP_KEY': self.test_key_json}):
            key_data, key_path, temp_file = FiresyncConfig._load_key(
                key_path=None,
                key_env='GCP_KEY'
            )

            self.assertEqual(key_data['project_id'], 'test-project')
            self.assertIsNotNone(temp_file)  # Temp file created for JSON content
            self.assertTrue(key_path.exists())

            # Clean up temp file
            if temp_file:
                os.unlink(temp_file)

    def test_key_env_with_file_path(self):
        """Test that key_env with file path reads from that file."""
        # Create temp key file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_key_data, f)
            temp_key_path = f.name

        try:
            with patch.dict(os.environ, {'GCP_KEY': temp_key_path}):
                key_data, key_path, temp_file = FiresyncConfig._load_key(
                    key_path=None,
                    key_env='GCP_KEY'
                )

                self.assertEqual(key_data['project_id'], 'test-project')
                self.assertIsNone(temp_file)  # No temp file for file path
                self.assertEqual(str(key_path), str(Path(temp_key_path).resolve()))
        finally:
            os.unlink(temp_key_path)

    def test_key_env_not_set(self):
        """Test that missing env var causes exit."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop('NONEXISTENT_KEY', None)

            with self.assertRaises(SystemExit):
                FiresyncConfig._load_key(
                    key_path=None,
                    key_env='NONEXISTENT_KEY'
                )

    def test_key_env_invalid_path(self):
        """Test that invalid file path in env var causes exit."""
        with patch.dict(os.environ, {'GCP_KEY': '/nonexistent/path/to/key.json'}):
            with self.assertRaises(SystemExit):
                FiresyncConfig._load_key(
                    key_path=None,
                    key_env='GCP_KEY'
                )

    def test_key_path_direct(self):
        """Test direct key_path works as before."""
        # Create temp key file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_key_data, f)
            temp_key_path = f.name

        try:
            key_data, key_path, temp_file = FiresyncConfig._load_key(
                key_path=temp_key_path,
                key_env=None
            )

            self.assertEqual(key_data['project_id'], 'test-project')
            self.assertIsNone(temp_file)
        finally:
            os.unlink(temp_key_path)

    def test_both_key_path_and_key_env_fails(self):
        """Test that specifying both key_path and key_env causes exit."""
        with self.assertRaises(SystemExit):
            FiresyncConfig._load_key(
                key_path='/some/path',
                key_env='SOME_KEY'
            )

    def test_neither_key_path_nor_key_env_fails(self):
        """Test that specifying neither key_path nor key_env causes exit."""
        with self.assertRaises(SystemExit):
            FiresyncConfig._load_key(
                key_path=None,
                key_env=None
            )


if __name__ == '__main__':
    unittest.main()
