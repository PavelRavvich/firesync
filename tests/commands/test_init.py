#!/usr/bin/env python3
"""Tests for commands.init command."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestFirestoreInit(unittest.TestCase):
    """Tests for firestore_init.py script."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_init_success(self):
        """Test successful workspace initialization."""
        # Get project root
        project_root = Path.cwd()

        # Prepare environment with PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        # Run firesync.commands.init module in temp directory
        result = subprocess.run(
            [sys.executable, "-m", "firesync.commands.init"],
            cwd=self.temp_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        # Check exit code
        self.assertEqual(result.returncode, 0, f"STDERR: {result.stderr}")

        # Check output
        self.assertIn("FireSync workspace initialized", result.stdout)
        self.assertIn("firestore-migration", result.stdout)
        self.assertIn("Next steps:", result.stdout)

        # Check that files were created
        config_path = Path(self.temp_dir) / "firestore-migration" / "config.yaml"
        self.assertTrue(config_path.exists())

        schemas_dir = Path(self.temp_dir) / "firestore-migration" / "schemas"
        self.assertTrue(schemas_dir.exists())
        self.assertTrue(schemas_dir.is_dir())

    def test_init_already_exists(self):
        """Test that init fails if workspace already exists."""
        # Get project root
        project_root = Path.cwd()

        # Prepare environment with PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        # Create workspace first
        workspace_dir = Path(self.temp_dir) / "firestore-migration"
        workspace_dir.mkdir()

        # Try to init again
        result = subprocess.run(
            [sys.executable, "-m", "firesync.commands.init"],
            cwd=self.temp_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        # Check exit code
        self.assertEqual(result.returncode, 1)

        # Check error message
        self.assertIn("already exists", result.stdout)


if __name__ == "__main__":
    unittest.main()
