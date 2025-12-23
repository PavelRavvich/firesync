#!/usr/bin/env python3
"""Tests for firesync.commands.init module."""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from firesync.workspace import CONFIG_DIR_NAME, CONFIG_FILE_NAME


class TestFirestoreInit(unittest.TestCase):
    """Tests for firesync init command."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_init_success(self):
        """Test successful workspace initialization."""
        from firesync.commands.init import main as init_main

        # Mock cwd to return temp_dir
        with patch('firesync.workspace.Path.cwd', return_value=Path(self.temp_dir)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                init_main()
                output = mock_stdout.getvalue()

        # Check output
        self.assertIn("FireSync workspace initialized", output)
        self.assertIn("firestore-migration", output)
        self.assertIn("Next steps:", output)

        # Check that files were created
        config_path = Path(self.temp_dir) / CONFIG_DIR_NAME / CONFIG_FILE_NAME
        self.assertTrue(config_path.exists())

        schemas_dir = Path(self.temp_dir) / CONFIG_DIR_NAME / "schemas"
        self.assertTrue(schemas_dir.exists())
        self.assertTrue(schemas_dir.is_dir())

    def test_init_already_exists(self):
        """Test that init fails if workspace already exists."""
        from firesync.commands.init import main as init_main

        # Create workspace first
        workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        workspace_dir.mkdir()

        # Try to init again
        with patch('firesync.workspace.Path.cwd', return_value=Path(self.temp_dir)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as ctx:
                    init_main()
                output = mock_stdout.getvalue()

        # Check exit code
        self.assertEqual(ctx.exception.code, 1)

        # Check error message
        self.assertIn("already exists", output)


if __name__ == "__main__":
    unittest.main()
