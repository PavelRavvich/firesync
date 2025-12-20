#!/usr/bin/env python3
"""Tests for firestore_init command."""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import tempfile
import shutil
import subprocess
import os


class TestFirestoreInit(unittest.TestCase):
    """Tests for firestore_init.py script."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_init_success(self):
        """Test successful workspace initialization."""
        # Get path to firestore_init.py from project root
        project_root = Path.cwd()
        init_script = project_root / "firestore_init.py"

        # Prepare environment with PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        # Run firestore_init.py in temp directory
        result = subprocess.run(
            [sys.executable, str(init_script)],
            cwd=self.temp_dir,
            env=env,
            capture_output=True,
            text=True
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
        # Get path to firestore_init.py from project root
        project_root = Path.cwd()
        init_script = project_root / "firestore_init.py"

        # Prepare environment with PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        # Create workspace first
        workspace_dir = Path(self.temp_dir) / "firestore-migration"
        workspace_dir.mkdir()

        # Try to init again
        result = subprocess.run(
            [sys.executable, str(init_script)],
            cwd=self.temp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        # Check exit code
        self.assertEqual(result.returncode, 1)

        # Check error message
        self.assertIn("already exists", result.stdout)


if __name__ == "__main__":
    unittest.main()
